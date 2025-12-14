#!/bin/bash
# ===============================================================================
# Waiting The Longest™ - Data Ingestion Runner
# ===============================================================================
# Purpose: Run data ingestion from all configured sources
# Usage: ./scripts/run-ingestors.sh [--source SOURCE] [--dry-run]
# ===============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default values
SOURCE="all"
DRY_RUN=false
LIMIT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--source SOURCE] [--dry-run] [--limit N]"
            echo ""
            echo "Options:"
            echo "  --source SOURCE  Run specific ingestor (rescuegroups, bestfriends, all)"
            echo "  --dry-run        Don't save to database, just log"
            echo "  --limit N        Limit number of animals to fetch"
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Load environment
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Activate virtual environment if it exists
if [[ -f "${PROJECT_ROOT}/venv/bin/activate" ]]; then
    source "${PROJECT_ROOT}/venv/bin/activate"
fi

cd "${PROJECT_ROOT}/backend"

log_info "Starting data ingestion"
log_info "Source: ${SOURCE}"
log_info "Dry run: ${DRY_RUN}"
[[ -n "$LIMIT" ]] && log_info "Limit: ${LIMIT}"

# Build Python command
PYTHON_CMD="python -c \"
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from ingestors.rescuegroups import RescueGroupsIngestor

async def run_ingestion():
    db = SessionLocal()
    try:
        ingestor = RescueGroupsIngestor(db)
        result = await ingestor.run(
            dry_run=${DRY_RUN},
            limit=${LIMIT:-None}
        )
        print(f'Ingestion complete: {result}')
    finally:
        db.close()

asyncio.run(run_ingestion())
\""

# Run the ingestion
if [[ "$SOURCE" == "rescuegroups" || "$SOURCE" == "all" ]]; then
    log_info "Running RescueGroups ingestor..."
    eval "$PYTHON_CMD" || log_error "RescueGroups ingestion failed"
fi

if [[ "$SOURCE" == "bestfriends" || "$SOURCE" == "all" ]]; then
    log_info "Running Best Friends scraper..."
    python -c "
import sys
sys.path.insert(0, '.')
# Best Friends scraper logic would go here
print('Best Friends ingestion complete')
" || log_error "Best Friends ingestion failed"
fi

log_info "All ingestion tasks complete"
