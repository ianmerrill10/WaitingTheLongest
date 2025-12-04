# Shelter Collection Guide

## Overview

This guide explains how to use the custom GitHub Copilot agent to systematically collect contact information and descriptions for animal shelters, rescues, humane societies, SPCAs, and other non-profit animal adoption organizations across all 50 US states.

## Purpose

The Waiting The Longest™ platform needs a comprehensive database of non-profit animal adoption organizations to:

1. **Connect Adopters with Shelters**: Help potential adopters find shelters near them
2. **Enrich Animal Records**: Provide accurate shelter contact information for animal listings
3. **Support the Mission**: Help animals who have been waiting the longest find their forever homes

## Quick Start

### 1. Check Collection Progress

```bash
cd backend
python tools/shelter_collector.py --show-progress
```

This shows:
- Total states
- Completed count and percentage
- Pending states
- Total shelters collected

### 2. Find Next State to Collect

```bash
python tools/shelter_collector.py --next-state
```

### 3. Collect Shelters for a State

Use GitHub Copilot Chat with prompts like:
- "Collect shelters for Texas"
- "Collect TX shelters"
- "Get animal shelters in California"

The agent will output JSON in the required format.

### 4. Save and Process Data

Save the agent's JSON output to a file, then process it:

```bash
# Save output to file
# (Copy JSON from Copilot response to TX_shelters.json)

# Process the file
python tools/shelter_collector.py --file TX_shelters.json
```

### 5. Insert to Database

```bash
python tools/shelter_collector.py --state TX --insert
```

## Data Collection Workflow

### Step 1: Preparation

Before collecting for a state:

1. Check if the state has already been collected:
   ```bash
   python tools/shelter_collector.py --show-progress
   ```

2. Review existing data if available:
   ```bash
   ls backend/data/collected_shelters/
   ```

### Step 2: Collection

Use the Copilot agent to collect shelter data. Recommended prompts:

| Prompt | Description |
|--------|-------------|
| `Collect shelters for [State]` | Collect all shelters for a specific state |
| `What's the next state to collect?` | Get the next pending state |
| `Show collection progress` | Display current progress |
| `List major shelters in [City]` | Focus on a specific city |

### Step 3: Validation

The shelter collector tool validates:

- **Name**: Required, max 200 characters
- **State**: Required, valid US state abbreviation
- **Email**: Optional, max 200 characters
- **Phone**: Optional, max 50 characters
- **Address**: Optional, max 300 characters
- **City**: Optional, max 100 characters
- **ZIP Code**: Optional, max 20 characters
- **Coordinates**: Optional, valid latitude/longitude

### Step 4: Storage

Data is stored in two locations:

1. **JSON Files**: `backend/data/collected_shelters/{STATE}_shelters.json`
2. **Database**: The `shelters` table in PostgreSQL

### Step 5: Tracking

Progress is automatically tracked in:
- `backend/data/state_collection_tracker.json`

## Output Format

### Required JSON Structure

```json
{
  "state": "TX",
  "state_full": "Texas",
  "collection_date": "2025-12-04",
  "shelters": [
    {
      "name": "Austin Pets Alive!",
      "type": "rescue",
      "email": "info@austinpetsalive.org",
      "phone": "(512) 961-6519",
      "website": "https://www.austinpetsalive.org",
      "address": "1156 West Cesar Chavez Street",
      "city": "Austin",
      "state": "TX",
      "zip_code": "78703",
      "description": "Mission statement or brief description"
    }
  ],
  "total_count": 1,
  "notes": "Optional notes about the collection"
}
```

### Valid Organization Types

- `shelter` - Municipal or government animal shelters
- `rescue` - Animal rescue organizations
- `humane_society` - Humane societies
- `spca` - Society for Prevention of Cruelty to Animals
- `aspca` - ASPCA affiliates
- `sanctuary` - Animal sanctuaries
- `foster_network` - Foster-based rescue networks
- `nonprofit` - Other non-profit animal welfare organizations

## CLI Reference

### Show Progress

```bash
python tools/shelter_collector.py --show-progress
```

Output:
```
============================================================
Waiting The Longest™ - Shelter Collection Progress
============================================================

Total States: 50
Completed: 5 (10.0%)
Pending: 45
In Progress: 0
Total Shelters Collected: 127

Completed States: CA, FL, NY, PA, TX
```

### Get Next State

```bash
python tools/shelter_collector.py --next-state
```

Output:
```
Next state to collect: AL (Alabama)
```

### Process File

```bash
python tools/shelter_collector.py --file TX_shelters.json
```

Options:
- `--no-db`: Skip database operations (file only)

### Insert from Saved File

```bash
python tools/shelter_collector.py --state TX --insert
```

This reads from `backend/data/collected_shelters/TX_shelters.json` and inserts to database.

## Quality Guidelines

### Organizations to Include

✅ Municipal animal shelters
✅ County animal control facilities
✅ Registered 501(c)(3) rescues
✅ Humane societies
✅ SPCAs and ASPCA affiliates
✅ Animal sanctuaries
✅ Foster-based rescue networks

### Organizations to Exclude

❌ Retail pet stores
❌ For-profit breeders
❌ Puppy mills
❌ Backyard breeders
❌ Commercial pet sellers

### Data Quality Checklist

- [ ] Organization is a legitimate non-profit or municipal facility
- [ ] Contact information is current and publicly available
- [ ] Address matches the correct state
- [ ] No duplicate entries
- [ ] Description is accurate and appropriate

## Troubleshooting

### Common Issues

**Issue**: Validation error for shelter name
- **Solution**: Ensure name is provided and under 200 characters

**Issue**: Invalid state abbreviation
- **Solution**: Use two-letter US state abbreviations (TX, CA, NY, etc.)

**Issue**: Database connection failed
- **Solution**: Check database configuration in `.env` file
- **Alternative**: Use `--no-db` flag to save to file only

**Issue**: File not found when inserting
- **Solution**: Ensure the JSON file exists in `backend/data/collected_shelters/`

### Validation Errors

The tool will report validation errors for individual shelters:
- Shelters with errors are skipped
- Valid shelters are still processed
- Errors are logged for review

## Integration with Existing Data

### Source Field

All shelters collected by this agent use:
```python
source = "copilot_agent_collection"
```

This distinguishes agent-collected data from:
- `rescuegroups` - RescueGroups.org API
- `adoptapet` - Adopt-a-Pet API
- `manual` - Manually entered data

### Upsert Logic

The collector uses **name + state** as the unique identifier:
- If a shelter with the same name and state exists, it's updated
- Otherwise, a new record is created

## State Collection Checklist

Use this checklist to track progress:

### High-Priority States (Highest Population)

- [ ] CA - California
- [ ] TX - Texas
- [ ] FL - Florida
- [ ] NY - New York
- [ ] PA - Pennsylvania
- [ ] IL - Illinois
- [ ] OH - Ohio
- [ ] GA - Georgia
- [ ] NC - North Carolina
- [ ] MI - Michigan

### Medium-Priority States

- [ ] NJ - New Jersey
- [ ] VA - Virginia
- [ ] WA - Washington
- [ ] AZ - Arizona
- [ ] MA - Massachusetts
- [ ] TN - Tennessee
- [ ] IN - Indiana
- [ ] MD - Maryland
- [ ] MO - Missouri
- [ ] WI - Wisconsin

### Remaining States

See `backend/data/state_collection_tracker.json` for full list.

## Support

For questions or issues:
1. Check the Copilot instructions in `.github/copilot-instructions.md`
2. Review the tracker file: `backend/data/state_collection_tracker.json`
3. Check tool logs for detailed error messages

---

*Waiting The Longest™ - Every shelter animal deserves a chance at a forever home.*
