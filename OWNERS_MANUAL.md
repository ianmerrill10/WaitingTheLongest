# Waiting The Longest™ - Owner's Manual

> **"Because Every Day Matters"**

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Key Components](#key-components)
4. [Worker Documentation](#worker-documentation)
5. [Running the Application](#running-the-application)
6. [Environment Variables](#environment-variables)
7. [Data Sources](#data-sources)
8. [Changelog](#changelog)

---

## Project Overview

### Platform Name
**Waiting The Longest™**

### Tagline
**"Because Every Day Matters"**

### Mission
Helping shelter dogs who have waited the longest find forever homes. Our platform highlights animals sorted by how long they've been waiting in shelters, giving the longest-waiting pets the visibility they deserve.

### Key Features
- **Days Waiting Priority**: Animals sorted by days waiting (longest first) by default
- **Multi-Source Aggregation**: Data from RescueGroups.org and other shelter APIs
- **Deduplication**: Perceptual hashing prevents duplicate animal listings
- **Social Media Content**: Automated TikTok/Instagram vertical video generation
- **Ethical Monetization**: Amazon Associates affiliate links for pet supplies

---

## Architecture Overview

### Directory Structure

```
WaitingTheLongest/
├── backend/                  # Python FastAPI backend
│   ├── app/                  # FastAPI application core
│   │   ├── config.py         # Pydantic settings for environment configuration
│   │   ├── database.py       # SQLAlchemy engine and session management
│   │   ├── models.py         # ORM model definitions (Animal, Observation, etc.)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── crud.py           # Database operations and business logic
│   │   ├── main.py           # FastAPI application entry point
│   │   └── email_marketing.py# Email marketing service
│   ├── ingestors/            # Data ingestion from shelter APIs
│   │   └── rescuegroups.py   # RescueGroups.org API ingestor (PRIMARY)
│   ├── workers/              # Background task workers
│   │   └── scheduler.py      # Scheduled workers for ingestion, cleanup, etc.
│   ├── tools/                # Utility tools
│   │   └── video_generator.py# TikTok/Instagram Reels video generator
│   └── monetization/         # Revenue generation
│       └── amazon_associates.py # Amazon Associates integration
├── frontend/                 # Vanilla JavaScript SPA
│   ├── index.html            # Main HTML page
│   └── css/js/               # Styles and scripts
├── aws/                      # AWS deployment configs
├── nginx/                    # Nginx reverse proxy configuration
├── systemd/                  # systemd service units
└── scripts/                  # Deployment and utility scripts
```

### Technology Stack
| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 |
| Cache | Redis |
| Frontend | Vanilla JavaScript SPA |
| Server OS | Ubuntu 24.04 LTS |
| Web Server | Nginx with Let's Encrypt SSL |
| Process Manager | systemd |

---

## Key Components

### RescueGroups Ingestor
**File**: `backend/ingestors/rescuegroups.py`

The primary data source for animal data. Connects to the RescueGroups.org API to fetch shelter animal listings.

> **NOTE**: Petfinder does NOT have a public API! We discovered this during development and pivoted to RescueGroups.org as our primary data source.

**Key Classes**:
- `RescueGroupsIngestor`: Main ingestor class with API communication
- `IngestedAnimal`: Dataclass for standardized animal data
- `run_full_ingestion()`: Orchestrates complete ingestion from all sources

### Scheduler
**File**: `backend/workers/scheduler.py`

Background workers for scheduled operations including data ingestion, status updates, social content generation, and cleanup.

**Available Workers**:
- IngestionWorker
- StatusUpdateWorker
- SocialContentWorker
- EmailWorker
- CleanupWorker

### Video Generator
**File**: `backend/tools/video_generator.py`

Creates TikTok/Instagram Reels style 9:16 vertical videos featuring animals who have waited the longest.

**Video Structure**:
1. **Intro Clip**: Prominent days waiting count ("365 DAYS WAITING")
2. **Photo Slideshow**: Up to 5 photos with breed/name overlays
3. **Outro Clip**: "ADOPT TODAY" call-to-action and branding

**Dependencies**: moviepy, pillow, numpy

### Config
**File**: `backend/app/config.py`

Pydantic settings for environment configuration. Loads settings from environment variables and `.env` file.

---

## Worker Documentation

### IngestionWorker
**Purpose**: Fetches animals from shelter APIs

**Interval**: Every 6 hours (configurable via `INGEST_INTERVAL_HOURS`)

**Process**:
1. Connect to RescueGroups.org API
2. Fetch animal listings (dogs and cats)
3. Check for duplicates using perceptual hashing
4. Create or update animal records in database

### StatusUpdateWorker
**Purpose**: Updates stale animal statuses

**Threshold**: 14 days without sighting

**Behavior**: Animals not seen in 14 days are marked as "unknown" (potentially adopted, transferred, etc.)

### SocialContentWorker
**Purpose**: Generates promotional videos for longest-waiting animals

**Cooldown**: 7 days between promotions for the same animal

**Maximum**: 5 videos per run

### EmailWorker
**Purpose**: Processes email queue and newsletters

**Batch Size**: 100 emails per run

**Features**:
- Sends pending emails
- Schedules weekly newsletters (Sunday)
- Handles retries with exponential backoff

### CleanupWorker
**Purpose**: Removes old video files

**Retention**: 30 days

**Directory**: Configured via `VIDEO_OUTPUT_DIR`

---

## Running the Application

### Manual Worker Execution

```bash
# Run all workers
python -m backend.workers.scheduler

# From the backend directory
cd backend
python -m workers.scheduler
```

### Cron Configuration Example

```cron
# Run workers every 6 hours
0 */6 * * * cd /opt/waitingthelongest && /opt/waitingthelongest/venv/bin/python -m backend.workers.scheduler >> /var/log/waitingthelongest/workers.log 2>&1
```

### Running the API Server

```bash
# Development
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Environment Variables

Reference `.env.example` for a complete list of environment variables.

### Key Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | Application secret key |
| `RESCUEGROUPS_API_KEY` | No | RescueGroups.org API key |
| `AMAZON_ASSOCIATE_ID` | No | Amazon Associates ID (default: waitingthelon-20) |
| `REDIS_URL` | No | Redis connection URL |
| `REDIS_PASSWORD` | No | Redis password |
| `INGEST_ENABLED` | No | Enable/disable data ingestion (default: true) |
| `INGEST_INTERVAL_HOURS` | No | Hours between ingestion runs (default: 6) |
| `VIDEO_OUTPUT_DIR` | No | Path for generated videos |

### Social Media Tokens
| Variable | Description |
|----------|-------------|
| `TIKTOK_ACCESS_TOKEN` | TikTok API token |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram API token |
| `FACEBOOK_PAGE_TOKEN` | Facebook Page token |
| `AYRSHARE_API_KEY` | Ayrshare unified posting API key |

---

## Data Sources

### RescueGroups.org API (Primary)
**URL**: https://api.rescuegroups.org/http/v2.json

**Features**:
- Free API access
- Nationwide shelter data
- Both dogs and cats
- Regular updates

**API Documentation**: https://rescuegroups.org/services/adoptable-pet-data-api/

### Adopt-a-Pet API (Secondary)
**Status**: Implemented (requires `ADOPTAPET_API_KEY`)

Secondary source to expand coverage beyond RescueGroups. Configure `ADOPTAPET_API_KEY` to enable ingestion; when missing, the ingestor is automatically skipped to keep runs healthy.

---

## Changelog

### December 2025
- Created comprehensive OWNERS_MANUAL.md documentation
- Added `backend/__init__.py` to fix import errors
- Documented project architecture and structure
- Added worker documentation
- Documented environment variables

### Initial Release
- Core animal listing with days_waiting sorting
- RescueGroups.org data ingestion
- Amazon Associates integration
- Social media video generation
- Email marketing system

---

**IMPORTANT**: Any changes to backend Python files MUST be documented in this OWNERS_MANUAL.md

**"Because Every Day Matters"**

*© 2025 Waiting The Longest™*
