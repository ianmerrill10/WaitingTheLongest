# Rescue Entity Scraper Agent

A Python-based agent framework for scraping animal rescue entities across all 50 US states.

## Overview

This agent systematically iterates through all US states and their counties to collect information about animal rescue organizations, shelters, and humane societies. It excludes for-profit breeders and pet stores.

## Features

- **State & County Iteration**: Processes all 50 states with county-level granularity
- **Resumable Execution**: Can be stopped and resumed without losing progress
- **CSV Output**: Results saved to CSV with comprehensive entity information
- **Progress Tracking**: Real-time progress display during collection
- **Entity Filtering**: Automatically excludes breeders and pet stores

## File Structure

```
backend/agents/
├── agent.py           # Main entry point and execution loop
├── data_manager.py    # State/county data and CSV I/O
├── scraper_utils.py   # Scraping logic (placeholder)
├── requirements.txt   # Python dependencies
├── README.md          # This file
├── us_counties.json   # County data (to be added)
└── output/
    └── rescue_entities.csv  # Collection output
```

## Installation

1. Navigate to the agents directory:
```bash
cd backend/agents
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run Full Collection
```bash
python agent.py
```

### Collect Only One State
```bash
python agent.py --state TX
```

### Resume from Last Position
```bash
python agent.py --resume
```

### Start Fresh (Overwrite Existing Data)
```bash
python agent.py --no-resume
```

### Check Current Status
```bash
python agent.py --status
```

### Custom Output File
```bash
python agent.py --output /path/to/output.csv
```

### Adjust Request Delay
```bash
python agent.py --delay 2.0
```

### Enable Verbose Logging
```bash
python agent.py -v
```

## Output Format

The CSV file contains the following columns:

| Column | Description |
|--------|-------------|
| name | Organization name |
| address | Street address |
| city | City |
| state | State abbreviation (e.g., TX) |
| zip_code | ZIP code |
| phone | Contact phone number |
| email | Contact email |
| website | Website URL |
| social_facebook | Facebook page URL |
| social_instagram | Instagram profile URL |
| social_twitter | Twitter profile URL |
| description | Organization description |
| animal_types | Types of animals (comma-separated) |
| entity_type | government, private, or individual |
| county | County name |
| collected_at | Collection timestamp |

## Entity Types

- **government**: Municipal shelters, animal control
- **private**: Private non-profit rescues, humane societies
- **individual**: Individual foster networks

## Excluded Entities

The following are automatically excluded:
- Breeders and breeding operations
- For-profit pet stores
- Puppy mills
- Commercial animal sellers

## Graceful Shutdown

Press `Ctrl+C` to request a graceful shutdown. The agent will finish processing the current county before exiting.

## Resumability

The agent tracks completed counties via the output CSV. On restart with `--resume` (default), it will:
1. Read existing entities from CSV
2. Extract unique (state, county) pairs
3. Skip any county that has already been processed

## Adding County Data

The agent reads county data from `us_counties.json`. This file should contain a JSON object mapping state abbreviations to lists of county names:

```json
{
  "TX": ["Travis County", "Harris County", "Dallas County", ...],
  "CA": ["Los Angeles County", "San Francisco County", ...],
  ...
}
```

If this file is not present, placeholder counties will be used.

## Future Enhancements

The `search_entities_in_county()` function in `scraper_utils.py` is a placeholder. Future PRs will implement actual scraping logic for:
- Web searches
- Government databases
- Rescue organization directories
- Social media discovery

## Integration

This agent is part of the **Waiting The Longest™** platform, which helps shelter animals who have waited the longest find forever homes.

## License

Proprietary - All rights reserved.

---

*© 2025 Waiting The Longest™*
