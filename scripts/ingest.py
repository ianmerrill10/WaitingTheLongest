#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Automated Data Ingestion Scheduler
===============================================================================
Purpose: Schedule and run data ingestion from all configured sources.
         Can run as a standalone daemon or be triggered by cron/systemd.

Usage:
    python scripts/ingest.py              # Run ingestion once
    python scripts/ingest.py --daemon     # Run as daemon (every 6 hours)
    python scripts/ingest.py --dry-run    # Test without saving

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure backend directory is on path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def run_ingestion(dry_run: bool = False) -> dict:
    """
    Run data ingestion from all configured sources.
    
    Returns:
        dict with ingestion statistics
    """
    logger.info("=" * 60)
    logger.info("Starting data ingestion run")
    logger.info("=" * 60)
    
    results = {
        "started_at": datetime.utcnow().isoformat(),
        "sources": {},
        "total_animals": 0,
        "new_animals": 0,
        "updated_animals": 0,
        "errors": []
    }
    
    # Try RescueGroups ingestion
    try:
        logger.info("Checking RescueGroups ingestor...")
        from ingestors.rescuegroups import RescueGroupsIngestor
        from app.config import settings
        
        api_key = getattr(settings, 'RESCUEGROUPS_API_KEY', None)
        if not api_key:
            logger.warning("RESCUEGROUPS_API_KEY not configured, skipping")
            results["sources"]["rescuegroups"] = {"status": "skipped", "reason": "no API key"}
        else:
            logger.info("Running RescueGroups ingestion...")
            if dry_run:
                logger.info("[DRY RUN] Would fetch from RescueGroups API")
                results["sources"]["rescuegroups"] = {"status": "dry_run"}
            else:
                # Run actual ingestion
                ingestor = RescueGroupsIngestor()
                count = ingestor.run()
                results["sources"]["rescuegroups"] = {
                    "status": "success",
                    "animals_processed": count
                }
                results["total_animals"] += count
                logger.info(f"RescueGroups: processed {count} animals")
                
    except ImportError as e:
        logger.warning(f"RescueGroups ingestor not available: {e}")
        results["sources"]["rescuegroups"] = {"status": "error", "error": str(e)}
        results["errors"].append(f"rescuegroups: {e}")
    except Exception as e:
        logger.error(f"RescueGroups ingestion failed: {e}")
        results["sources"]["rescuegroups"] = {"status": "error", "error": str(e)}
        results["errors"].append(f"rescuegroups: {e}")
    
    # Try Best Friends ingestion (if available)
    try:
        from ingestors.bestfriends import BestFriendsIngestor
        logger.info("Running Best Friends ingestion...")
        if dry_run:
            logger.info("[DRY RUN] Would scrape Best Friends")
            results["sources"]["bestfriends"] = {"status": "dry_run"}
        else:
            ingestor = BestFriendsIngestor()
            count = ingestor.run()
            results["sources"]["bestfriends"] = {
                "status": "success",
                "animals_processed": count
            }
            results["total_animals"] += count
            
    except ImportError:
        logger.debug("Best Friends ingestor not available")
    except Exception as e:
        logger.warning(f"Best Friends ingestion failed: {e}")
        results["errors"].append(f"bestfriends: {e}")
    
    results["completed_at"] = datetime.utcnow().isoformat()
    
    # Summary
    logger.info("=" * 60)
    logger.info("Ingestion Complete")
    logger.info(f"  Total animals processed: {results['total_animals']}")
    logger.info(f"  Errors: {len(results['errors'])}")
    logger.info("=" * 60)
    
    return results


def run_daemon(interval_hours: int = 6):
    """
    Run ingestion as a daemon, repeating at specified interval.
    """
    interval_seconds = interval_hours * 3600
    
    logger.info(f"Starting ingestion daemon (interval: {interval_hours} hours)")
    
    while True:
        try:
            run_ingestion()
        except Exception as e:
            logger.error(f"Ingestion run failed: {e}")
        
        next_run = datetime.utcnow().timestamp() + interval_seconds
        next_run_str = datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Next ingestion run at: {next_run_str}")
        
        time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(
        description="Run data ingestion for Waiting The Longest"
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Run as daemon (repeats every 6 hours)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=6,
        help="Interval in hours for daemon mode (default: 6)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without saving data"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.daemon:
        run_daemon(interval_hours=args.interval)
    else:
        results = run_ingestion(dry_run=args.dry_run)
        
        if results["errors"]:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
