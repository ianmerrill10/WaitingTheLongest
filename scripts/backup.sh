#!/bin/bash
# ===============================================================================
# Waiting The Longest™ - Database Backup Script
# ===============================================================================
# Purpose: Backup PostgreSQL database to local storage and optionally S3
# Usage: ./backup.sh [--s3] [--name backup_name]
# ===============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="wtl_backup_${TIMESTAMP}"
RETENTION_DAYS=30

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
UPLOAD_S3=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --s3)
            UPLOAD_S3=true
            shift
            ;;
        --name)
            BACKUP_NAME="$2"
            shift 2
            ;;
        *)
            log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    source "${PROJECT_ROOT}/.env"
fi

# Database connection
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-waitingthelongest}"
DB_USER="${DATABASE_USER:-postgres}"

log_info "Starting backup: ${BACKUP_NAME}"
log_info "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"

# Check if using SQLite or PostgreSQL
if [[ -f "${PROJECT_ROOT}/backend/waitingthelongest.db" ]]; then
    # SQLite backup
    log_info "Backing up SQLite database..."
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.db"
    cp "${PROJECT_ROOT}/backend/waitingthelongest.db" "$BACKUP_FILE"
    
    # Compress
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
else
    # PostgreSQL backup
    log_info "Backing up PostgreSQL database..."
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"
    
    PGPASSWORD="${DATABASE_PASSWORD:-}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-privileges \
        --format=plain | gzip > "$BACKUP_FILE"
fi

# Calculate size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_info "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Create backup manifest
MANIFEST_FILE="${BACKUP_DIR}/${BACKUP_NAME}.manifest.json"
cat > "$MANIFEST_FILE" << EOF
{
    "name": "${BACKUP_NAME}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "database": "${DB_NAME}",
    "file": "$(basename "$BACKUP_FILE")",
    "size_bytes": $(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE"),
    "checksum": "$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)"
}
EOF

log_info "Manifest created: ${MANIFEST_FILE}"

# Upload to S3 if requested
if [[ "$UPLOAD_S3" == true ]]; then
    S3_BUCKET="${BACKUP_S3_BUCKET:-}"
    if [[ -z "$S3_BUCKET" ]]; then
        log_warn "S3 upload requested but BACKUP_S3_BUCKET not set"
    else
        log_info "Uploading to S3: s3://${S3_BUCKET}/backups/"
        aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/backups/$(basename "$BACKUP_FILE")"
        aws s3 cp "$MANIFEST_FILE" "s3://${S3_BUCKET}/backups/$(basename "$MANIFEST_FILE")"
        log_info "S3 upload complete"
    fi
fi

# Clean up old backups
log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "wtl_backup_*.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "wtl_backup_*.manifest.json" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# Count remaining backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "wtl_backup_*.gz" | wc -l)
log_info "Total backups retained: ${BACKUP_COUNT}"

log_info "Backup complete!"

# Print summary
echo ""
echo "==============================================="
echo "Backup Summary"
echo "==============================================="
echo "Name:     ${BACKUP_NAME}"
echo "File:     ${BACKUP_FILE}"
echo "Size:     ${BACKUP_SIZE}"
echo "S3:       ${UPLOAD_S3}"
echo "==============================================="
