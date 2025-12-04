# Waiting The Longest™ - Owner's Manual

> **"Because Every Day Matters"**

---

## Table of Contents

1. [Project Overview & Mission](#project-overview--mission)
2. [Architecture Overview](#architecture-overview)
3. [Complete File-by-File Breakdown](#complete-file-by-file-breakdown)
4. [Database Schema Documentation](#database-schema-documentation)
5. [API Endpoint Reference](#api-endpoint-reference)
6. [Data Flow Explanations](#data-flow-explanations)
7. [Deployment Guide](#deployment-guide)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Monetization Strategy](#monetization-strategy)
10. [Social Media Integration](#social-media-integration)
11. [Maintenance Procedures](#maintenance-procedures)
12. [Security Considerations](#security-considerations)
13. [Environment Variables Reference](#environment-variables-reference)
14. [Changelog / Version History](#changelog--version-history)

---

## Project Overview & Mission

### Mission Statement
**Waiting The Longest™** is a mission-driven platform dedicated to helping shelter animals who have waited the longest find their forever homes. Our core belief is that every day an animal waits in a shelter matters, and those who have waited longest deserve extra visibility.

### Key Features
- **Days Waiting Priority**: Animals are sorted by days waiting (longest first) by default
- **Multi-Source Aggregation**: Data from RescueGroups.org and other shelter APIs
- **Deduplication**: Perceptual hashing prevents duplicate animal listings
- **Social Media Content**: Automated TikTok/Instagram video generation
- **Ethical Monetization**: Amazon Associates affiliate links for pet supplies

### Domain Information
| Property | Value |
|----------|-------|
| **Primary Domain** | WaitingTheLongest.com |
| **Secondary Domain** | WaitedTheLongest.com (301 redirect to primary) |
| **Server IP** | 67.217.244.241 (IONOS VPS) |
| **Amazon Associate ID** | waitingthelon-20 |

### Technology Stack
- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16
- **Cache**: Redis
- **Frontend**: Vanilla JavaScript SPA
- **Server OS**: Ubuntu 24.04 LTS
- **Web Server**: Nginx with Let's Encrypt SSL
- **Process Manager**: systemd

---

## Architecture Overview

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                 │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         NGINX (Reverse Proxy)                         │
│  - SSL Termination (Let's Encrypt)                                    │
│  - Rate Limiting (per IP)                                             │
│  - Static File Serving (frontend/)                                    │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                     ▼                             ▼
        ┌────────────────────┐       ┌────────────────────────────┐
        │   FastAPI Backend  │       │    Static Frontend         │
        │   (port 8000)      │       │    (index.html, app.js)    │
        │                    │       └────────────────────────────┘
        │  API Endpoints     │
        │  Rate Limiter      │
        └────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐        ┌───────────────┐
│  PostgreSQL   │        │    Redis      │
│  (Database)   │        │   (Cache)     │
└───────────────┘        └───────────────┘

        ┌─────────────────────────────────────────────┐
        │           BACKGROUND WORKERS                 │
        │  (Scheduled via cron/systemd timer)          │
        │                                              │
        │  - IngestionWorker (6hr cycle)               │
        │  - StatusUpdateWorker                        │
        │  - SocialContentWorker                       │
        │  - CleanupWorker                             │
        └─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                              │
│  - RescueGroups API (Data Source)                                     │
│  - Amazon Associates (Monetization)                                   │
│  - Social Media APIs (TikTok, Instagram, FB)                          │
└──────────────────────────────────────────────────────────────────────┘
```

### Request Flow
```
User Request → Nginx → FastAPI → Database → Response
```

### Data Ingestion Flow
```
RescueGroups API → Ingestor → Deduplication Check → Database
```

---

## Complete File-by-File Breakdown

### Backend Core (`backend/app/`)

#### `backend/app/main.py`
**Purpose**: FastAPI application entry point. Defines all HTTP endpoints, middleware configuration, and application lifecycle management.

**Key Components**:
- `lifespan()`: Async context manager handling app startup/shutdown
- `app`: FastAPI instance with CORS, rate limiting, exception handlers
- Rate Limiter: Uses `slowapi` to limit requests per IP (60/min, 1000/hour default)

**Endpoints Defined**:
- `GET /` - Returns API info and version
- `GET /health` - Health check with database connectivity test
- `GET /api/animals` - Paginated animal listing with filters
- `GET /api/animals/{id}` - Single animal details
- `GET /api/longest-waiting` - Top N longest-waiting animals
- `POST /api/success-stories` - Submit adoption success story
- `GET /api/success-stories` - Retrieve success stories
- `GET /api/stats` - Platform statistics
- `POST /api/affiliate/click` - Track affiliate link clicks
- `GET /api/products/recommendations` - Get product recommendations

**Dependencies**: fastapi, slowapi, sqlalchemy, pydantic

---

#### `backend/app/config.py`
**Purpose**: Centralized configuration management using Pydantic Settings.

**Configuration Categories**:
- Application: APP_NAME, DEBUG, SECRET_KEY
- Database: DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW
- Redis: REDIS_URL, REDIS_PASSWORD
- API Keys: RESCUEGROUPS_API_KEY, ADOPTAPET_API_KEY
- Amazon: AMAZON_ASSOCIATE_ID, AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY
- Social: TIKTOK_ACCESS_TOKEN, INSTAGRAM_ACCESS_TOKEN, etc.
- CORS: CORS_ORIGINS list
- Paths: VIDEO_OUTPUT_DIR, IMAGE_CACHE_DIR, UPLOAD_DIR
- Ingestion: INGEST_ENABLED, INGEST_PAGE_LIMIT, INGEST_INTERVAL_HOURS
- Rate Limiting: RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR

---

#### `backend/app/database.py`
**Purpose**: SQLAlchemy database engine and session management.

**Key Components**:
- `engine`: SQLAlchemy engine with connection pooling
- `SessionLocal`: Session factory for creating database sessions
- `Base`: Declarative base class for all ORM models
- `get_db()`: Dependency injection function for FastAPI routes
- `init_db()`: Creates all database tables

---

#### `backend/app/models.py`
**Purpose**: SQLAlchemy ORM model definitions.

**Models**:
| Model | Purpose |
|-------|---------|
| `Animal` | Core entity - canonical, deduplicated animal records |
| `Observation` | Raw sighting from a data source |
| `Shelter` | Shelter/rescue organization information |
| `SuccessStory` | User-submitted adoption success stories |
| `SocialPromotion` | Tracks social media posts for animals |
| `AffiliateClick` | Tracks affiliate link clicks for revenue |

**Key Property**:
```python
@property
def days_waiting(self) -> int:
    """Calculate days this animal has been waiting"""
    if self.first_seen_at:
        return (datetime.now(timezone.utc).replace(tzinfo=None) - self.first_seen_at).days
    return 0
```

---

#### `backend/app/schemas.py`
**Purpose**: Pydantic schemas for request/response validation and serialization.

**Key Schemas**: HealthResponse, AnimalListItem, AnimalDetailResponse, AnimalListResponse, SuccessStoryCreate, SuccessStoryResponse, ProductRecommendation

---

#### `backend/app/crud.py`
**Purpose**: Core business logic and database operations. **Implements the "days waiting" sorting which is central to our mission!**

**Key Functions**:
- `paginate_animals()`: **THE CORE FEATURE!** Lists animals sorted by days_waiting
- `get_animal_detail()`: Get complete animal info with all observations
- `create_success_story()`: Create new success story (requires moderation)
- `get_trending_stories()`: Get featured/approved success stories
- `find_duplicate_animal()`: Deduplication using perceptual hash, name+breed
- `merge_animal_observation()`: Add new observation to existing animal
- `get_platform_stats()`: Calculate platform-wide statistics

---

### Data Ingestion (`backend/ingestors/rescuegroups.py`)
**Purpose**: Data ingestion from RescueGroups.org API. This is the PRIMARY data source (Petfinder does NOT have a public API).

**Key Components**:
- `IngestedAnimal`: Dataclass for standardized animal data
- `RescueGroupsIngestor`: Main ingestor class with API communication
- `run_full_ingestion()`: Orchestrates complete ingestion from all sources

---

### Workers (`backend/workers/scheduler.py`)
**Purpose**: Background task workers for scheduled operations.

**Workers**:
- `IngestionWorker`: Fetches new animals from APIs (every 6 hours)
- `StatusUpdateWorker`: Marks animals not seen in 14 days as "unknown"
- `SocialContentWorker`: Generates promotional videos for longest-waiting animals
- `CleanupWorker`: Deletes old video files (30-day retention)

**Usage**:
```bash
python -m backend.workers.scheduler
```

---

### Tools (`backend/tools/video_generator.py`)
**Purpose**: Generates TikTok/Instagram Reels style vertical videos (9:16 aspect ratio).

**Video Structure**:
1. Intro: Days waiting count + animal name
2. Photos: Up to 5 photos with breed overlay
3. Outro: "ADOPT TODAY" + shelter info + website

**Dependencies**: moviepy, pillow, numpy

---

### Monetization (`backend/monetization/amazon_associates.py`)
**Purpose**: Amazon Associates affiliate link generation and product recommendations.

**Associate ID**: waitingthelon-20

**CRITICAL**: You need 3 qualified sales within 180 days!

**Commission Rates**:
- Pet Products: 2-8%
- Pet Food: 4%
- Toys: 3%
- Luxury Beauty (grooming): 10%

---

### Infrastructure Files

#### `scripts/deploy.sh`
**Purpose**: Master deployment script for Ubuntu 24.04 server setup.

**Steps**: System dependencies, user creation, PostgreSQL setup, Redis configuration, Python environment, UFW firewall, Fail2ban, systemd service, log rotation.

#### `nginx/waitingthelongest.conf`
**Purpose**: Nginx reverse proxy with SSL, rate limiting, security headers.

#### `systemd/waitingthelongest.service`
**Purpose**: systemd service unit for FastAPI application.

---

### Frontend (`frontend/index.html`)
**Purpose**: Single-page application (SPA) for the user-facing website.

**Features**: Mobile-responsive, hero section with stats, pet grid, auto-loads from API.

---

## Database Schema Documentation

### Core Tables

| Table | Purpose |
|-------|---------|
| `animals` | Canonical deduplicated animal records |
| `observations` | Raw sightings from data sources |
| `shelters` | Shelter/rescue organization info |
| `success_stories` | User-submitted adoption stories |
| `social_promotions` | Social media post tracking |
| `affiliate_clicks` | Revenue tracking |

### Key Field
`animals.first_seen_at` - Used to calculate `days_waiting`, our core metric!

---

## API Endpoint Reference

### Base URL
- **Production**: `https://waitingthelongest.com/api`
- **Development**: `http://localhost:8000/api`

### Rate Limits
- Per Minute: 60 requests
- Per Hour: 1000 requests

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/api/animals` | GET | List animals (paginated) |
| `/api/animals/{id}` | GET | Animal details |
| `/api/longest-waiting` | GET | Top longest-waiting |
| `/api/success-stories` | GET/POST | Success stories |
| `/api/stats` | GET | Platform statistics |
| `/api/affiliate/click` | POST | Track clicks |
| `/api/products/recommendations` | GET | Product recommendations |

### Key Parameters (GET /api/animals)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| species | string | null | "dog" or "cat" |
| sort_by | string | "days_waiting" | Sort field |
| sort_order | string | "desc" | Longest first |
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page |

---

## Data Flow Explanations

### Ingestion Flow
```
1. Scheduled Worker Triggers (every 6 hours)
2. RescueGroupsIngestor.fetch_animals()
3. Deduplication Check (pHash, name+breed)
4. Create or Update Record
5. Commit to database
```

---

## Deployment Guide

```bash
# Connect to server
ssh root@67.217.244.241

# Run deployment script
sudo ./scripts/deploy.sh

# Configure API keys
nano /opt/waitingthelongest/backend/.env

# Setup SSL
certbot --nginx -d waitingthelongest.com

# Start service
systemctl start waitingthelongest
```

---

## Troubleshooting Guide

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | `systemctl restart waitingthelongest` |
| Database errors | `systemctl status postgresql` |
| Rate limiting (429) | Wait or increase limits |
| No animals | Check RESCUEGROUPS_API_KEY |

### Log Locations
- API: `/var/log/waitingthelongest/`
- System: `journalctl -u waitingthelongest`

---

## Monetization Strategy

**Amazon Associate ID**: `waitingthelon-20`

**CRITICAL**: Need 3 qualified sales within 180 days!

| Category | Commission |
|----------|------------|
| Pet Products | 2-8% |
| Pet Food | 4% |
| Toys | 3% |

---

## Social Media Integration

### Platforms
- TikTok (Primary)
- Instagram Reels (Primary)
- Facebook (Secondary)

### Video Structure
1. Hook: "365 DAYS WAITING"
2. Photos with overlays
3. CTA: "ADOPT TODAY"

---

## Maintenance Procedures

### Daily
- Check `/health` endpoint

### Weekly
- Database backup
- Review disk space

### Monthly
- Apply security updates
- Review fail2ban

---

## Security Considerations

| Measure | Status |
|---------|--------|
| UFW Firewall | ✅ Ports 22, 80, 443 only |
| Fail2ban | ✅ Enabled |
| SSL/TLS | ✅ Let's Encrypt |
| Non-root User | ✅ `waitingapp` |
| Rate Limiting | ✅ Enabled |

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | PostgreSQL connection |
| SECRET_KEY | Yes | Application secret |
| RESCUEGROUPS_API_KEY | No | Data source API |
| AMAZON_ASSOCIATE_ID | No | waitingthelon-20 |
| REDIS_PASSWORD | No | Redis auth |

See `.env.example` for complete list.

---

## Changelog / Version History

### Version 1.0.0 (2025-01-15)
- Initial Release
- Core animal listing with days_waiting sorting
- RescueGroups.org data ingestion
- Amazon Associates integration
- Social media video generation

---

**"Because Every Day Matters"**

*© 2025 Waiting The Longest™*
