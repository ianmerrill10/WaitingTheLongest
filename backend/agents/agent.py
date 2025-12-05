#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Rescue Entity Scraper Agent
===============================================================================
Purpose: Main execution loop for scraping animal rescue entities across the US.

Author: Waiting The Longest™ Development Team
Dependencies: See requirements.txt
Related Files: data_manager.py, scraper_utils.py

This module provides:
- Main State -> County iteration loop
- Progress tracking and display
- Interruptible/resumable execution
- Console output with statistics

Usage:
    python agent.py                    # Run full collection
    python agent.py --state TX         # Run only for Texas
    python agent.py --resume           # Resume from last position
    python agent.py --status           # Show current progress

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md
===============================================================================
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from data_manager import (
    DEFAULT_OUTPUT_FILE,
    US_STATES,
    get_all_states,
    get_completed_counties,
    get_counties_for_state,
    get_progress_stats,
    get_state_name,
    initialize_csv,
    is_county_completed,
    write_entities_to_csv,
)
from scraper_utils import filter_entities, search_entities_in_county

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("\nShutdown requested. Finishing current county...")


class ProgressTracker:
    """Track and display collection progress."""

    def __init__(self):
        self.start_time = datetime.now()
        self.total_entities = 0
        self.states_completed = 0
        self.counties_completed = 0
        self.current_state = ""
        self.current_county = ""

    def update(
        self,
        entities_found: int = 0,
        county_done: bool = False,
        state_done: bool = False,
    ):
        """Update progress counters."""
        self.total_entities += entities_found
        if county_done:
            self.counties_completed += 1
        if state_done:
            self.states_completed += 1

    def set_current(self, state: str, county: str):
        """Set the current state/county being processed."""
        self.current_state = state
        self.current_county = county

    def display(self):
        """Display current progress to console."""
        elapsed = datetime.now() - self.start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        print("\n" + "=" * 60)
        print("Rescue Entity Scraper - Progress Report")
        print("=" * 60)
        print(f"Elapsed Time: {hours:02d}:{minutes:02d}:{seconds:02d}")
        print(f"Current: {self.current_state} - {self.current_county}")
        print("-" * 60)
        print(f"Total Entities Found: {self.total_entities:,}")
        print(f"States Completed: {self.states_completed} / {len(US_STATES)}")
        print(f"Counties Completed: {self.counties_completed:,}")
        print("=" * 60 + "\n")


def run_collection(
    target_state: Optional[str] = None,
    resume: bool = True,
    output_file: Path = DEFAULT_OUTPUT_FILE,
    delay_between_counties: float = 1.0,
) -> int:
    """
    Run the main collection loop.

    Args:
        target_state: If provided, only collect for this state
        resume: If True, skip already completed counties
        output_file: Path to output CSV file
        delay_between_counties: Seconds to wait between county requests

    Returns:
        Total number of entities collected
    """
    global _shutdown_requested

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize CSV file
    initialize_csv(output_file)

    # Initialize progress tracker
    progress = ProgressTracker()

    # Get initial completed counties for resumability
    completed = get_completed_counties(output_file) if resume else set()

    # Determine which states to process
    if target_state:
        states = [target_state.upper()]
        if states[0] not in US_STATES:
            logger.error(f"Invalid state: {target_state}")
            return 0
    else:
        states = get_all_states()

    logger.info(f"Starting collection for {len(states)} state(s)")
    logger.info(f"Resume mode: {resume}, Already completed: {len(completed)} counties")

    total_collected = 0

    for state_abbr in states:
        if _shutdown_requested:
            logger.info("Shutdown requested, stopping...")
            break

        state_name = get_state_name(state_abbr)
        logger.info(f"\n{'='*40}")
        logger.info(f"Processing state: {state_name} ({state_abbr})")
        logger.info(f"{'='*40}")

        # Get counties for this state
        counties = get_counties_for_state(state_abbr)
        if not counties:
            logger.warning(f"No county data available for {state_abbr}")
            continue

        counties_in_state = len(counties)
        counties_done_in_state = 0

        for county in counties:
            if _shutdown_requested:
                break

            # Check if already completed (resumability)
            if resume and (state_abbr, county) in completed:
                logger.debug(f"Skipping completed county: {county}")
                counties_done_in_state += 1
                continue

            progress.set_current(state_abbr, county)
            logger.info(f"Searching: {county}, {state_abbr}")

            try:
                # Search for entities in this county
                raw_entities = search_entities_in_county(state_abbr, county)

                # Filter out breeders/pet stores and validate
                entities = filter_entities(raw_entities)

                if entities:
                    # Write to CSV
                    written = write_entities_to_csv(entities, output_file)
                    total_collected += written
                    progress.update(entities_found=written, county_done=True)
                    logger.info(f"  Found {written} entities in {county}")
                else:
                    # Mark county as done even if no entities found
                    progress.update(county_done=True)
                    logger.info(f"  No entities found in {county}")

                counties_done_in_state += 1

            except Exception as e:
                logger.error(f"Error processing {county}, {state_abbr}: {e}")
                # Continue with next county

            # Rate limiting
            if delay_between_counties > 0:
                time.sleep(delay_between_counties)

        # State completed
        if counties_done_in_state == counties_in_state:
            progress.update(state_done=True)
            logger.info(f"Completed state: {state_name}")

        # Display progress after each state
        progress.display()

    logger.info(f"\nCollection complete. Total entities: {total_collected}")
    return total_collected


def show_status(output_file: Path = DEFAULT_OUTPUT_FILE):
    """Display current collection status."""
    stats = get_progress_stats(output_file)

    print("\n" + "=" * 60)
    print("Rescue Entity Scraper - Status Report")
    print("=" * 60)
    print(f"Output file: {output_file}")
    print(f"Total entities collected: {stats['total_entities']:,}")
    print(f"Counties completed: {stats['completed_counties']:,}")
    print(
        f"States with progress: {stats['states_with_progress']} / {stats['total_states']}"
    )
    print("=" * 60 + "\n")


def main():
    """Main entry point for the agent."""
    parser = argparse.ArgumentParser(
        description="Rescue Entity Scraper - Collect animal rescue organizations across the US",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python agent.py                    # Run full collection
    python agent.py --state TX         # Collect only Texas
    python agent.py --resume           # Resume from last position
    python agent.py --status           # Show current progress
    python agent.py --no-resume        # Start fresh (overwrite existing)
        """,
    )

    parser.add_argument(
        "--state",
        type=str,
        help="Process only this state (e.g., TX, CA)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from last position (default: True)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh, don't skip completed counties",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current collection status and exit",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_FILE),
        help=f"Output CSV file path (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between county requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_file = Path(args.output)

    # Show status and exit if requested
    if args.status:
        show_status(output_file)
        return 0

    # Determine resume mode
    resume = not args.no_resume

    # Run collection
    try:
        total = run_collection(
            target_state=args.state,
            resume=resume,
            output_file=output_file,
            delay_between_counties=args.delay,
        )
        logger.info(f"Collection finished. Total entities: {total}")
        return 0
    except KeyboardInterrupt:
        logger.info("\nCollection interrupted by user.")
        return 1
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
