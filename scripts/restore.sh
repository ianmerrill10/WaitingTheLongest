#!/bin/bash
# ===============================================================================
# Waiting The Longest™ - Database Restore Script
# ===============================================================================
# Purpose: Restore PostgreSQL database from backup
# Usage: ./restore.sh backup_file.sql.gz [--confirm]
# ===============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"

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
BACKUP_FILE=""
CONFIRMED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --confirm)
            CONFIRMED=true
            shift
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            fi
            shift
            ;;
    esac
done

# Validate backup file
if [[ -z "$BACKUP_FILE" ]]; then
    echo "Usage: $0 <backup_file> [--confirm]"
    echo ""
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/*.gz 2>/dev/null || echo "  No backups found in $BACKUP_DIR"
    exit 1
fi

# Check if it's a path or just a filename
if [[ ! -f "$BACKUP_FILE" ]]; then
    if [[ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]]; then
        BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
    else
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
fi

# Load environment variables
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    source "${PROJECT_ROOT}/.env"
fi

# Database connection
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-waitingthelongest}"
DB_USER="${DATABASE_USER:-postgres}"

log_info "Restore target: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
log_info "Backup file: ${BACKUP_FILE}"

# Confirmation
if [[ "$CONFIRMED" != true ]]; then
    echo ""
    log_warn "⚠️  WARNING: This will DESTROY all current data in the database!"
    log_warn "Database: ${DB_NAME}"
    echo ""
    read -p "Type 'yes' to confirm restore: " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
fi

# Detect backup type
if [[ "$BACKUP_FILE" == *.db.gz || "$BACKUP_FILE" == *.db ]]; then
    # SQLite restore
    log_info "Restoring SQLite database..."
    
    # Create backup of current database
    if [[ -f "${PROJECT_ROOT}/backend/waitingthelongest.db" ]]; then
        cp "${PROJECT_ROOT}/backend/waitingthelongest.db" "${PROJECT_ROOT}/backend/waitingthelongest.db.bak"
        log_info "Created backup of current database"
    fi
    
    # Decompress if needed
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        gunzip -c "$BACKUP_FILE" > "${PROJECT_ROOT}/backend/waitingthelongest.db"
    else
        cp "$BACKUP_FILE" "${PROJECT_ROOT}/backend/waitingthelongest.db"
    fi
else
    # PostgreSQL restore
    log_info "Restoring PostgreSQL database..."
    
    # Create pre-restore backup
    log_info "Creating pre-restore backup..."
    PGPASSWORD="${DATABASE_PASSWORD:-}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-privileges \
        --format=plain | gzip > "${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    # Drop and recreate database
    log_info "Dropping existing tables..."
    PGPASSWORD="${DATABASE_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    
    # Restore from backup
    log_info "Restoring data..."
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        gunzip -c "$BACKUP_FILE" | PGPASSWORD="${DATABASE_PASSWORD:-}" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --quiet
    else
        PGPASSWORD="${DATABASE_PASSWORD:-}" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --quiet < "$BACKUP_FILE"
    fi
fi

log_info "Restore complete!"

# Verify restore
log_info "Verifying restore..."
if [[ "$BACKUP_FILE" == *.db.gz || "$BACKUP_FILE" == *.db ]]; then
    ANIMAL_COUNT=$(sqlite3 "${PROJECT_ROOT}/backend/waitingthelongest.db" "SELECT COUNT(*) FROM animals" 2>/dev/null || echo "0")
else
    ANIMAL_COUNT=$(PGPASSWORD="${DATABASE_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t -c "SELECT COUNT(*) FROM animals" 2>/dev/null || echo "0")
fi

echo ""
echo "==============================================="
echo "Restore Summary"
echo "==============================================="
echo "Backup:   ${BACKUP_FILE}"
echo "Database: ${DB_NAME}"
echo "Animals:  ${ANIMAL_COUNT}"
echo "==============================================="
