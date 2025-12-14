# Waiting The Longest™

> **"Because Every Day Matters"** - A mission-driven pet adoption platform prioritizing shelter animals who have waited the longest for homes.

## ⚠️ Data Integrity Policy

> **ALL DATA IN THIS PROJECT MUST BE 100% TRUTHFUL AND VERIFIED ACCURATE.**
> 
> See [TRUTH_POLICY.md](TRUTH_POLICY.md) for complete policy. No exceptions.

## Overview

**Waiting The Longest™** is a nationwide shelter animal adoption platform that:
- Aggregates pet data from multiple sources (RescueGroups.org, shelter APIs)
- Highlights animals who have waited the longest using "days waiting" as primary sort
- Deduplicates animals across shelters using perceptual hashing (pHash)
- Generates social media content for TikTok/Instagram to drive adoptions
- Monetizes through ethical affiliate marketing (Amazon Associates)

## Key Information

| Item | Value |
|------|-------|
| **Primary Domain** | WaitingTheLongest.com |
| **Secondary Domain** | WaitedTheLongest.com (redirects to primary) |
| **Amazon Associate ID** | waitingthelon-20 |
| **Server** | IONOS VPS (67.217.244.241) |

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16
- **Cache**: Redis
- **ASGI Server**: Gunicorn + Uvicorn workers

### Frontend
- Vanilla JavaScript SPA
- Mobile-responsive design
- SEO-optimized

### Infrastructure
- **Server**: Ubuntu 24.04 LTS
- **Reverse Proxy**: Nginx
- **SSL**: Let's Encrypt (Certbot)
- **Process Manager**: systemd

## Project Structure

```
WaitingTheLongest/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── config.py        # Settings/configuration
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── models.py        # Database models
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── crud.py          # Business logic
│   ├── ingestors/
│   │   └── rescuegroups.py  # Data ingestion
│   ├── monetization/
│   │   └── amazon_associates.py
│   ├── tools/
│   │   └── video_generator.py
│   ├── workers/
│   │   └── scheduler.py
│   └── requirements.txt
├── frontend/
│   └── index.html
├── scripts/
│   └── deploy.sh
├── nginx/
│   └── waitingthelongest.conf
├── systemd/
│   └── waitingthelongest.service
├── docs/
├── .env.example
├── .gitignore
└── README.md
```

## Quick Start

### Development

```bash
# Clone repository
git clone https://github.com/ianmerrill10/WaitedTheLongest.git
cd WaitedTheLongest

# Option 1: Automated setup (recommended)
python scripts/dev_setup.py

# Option 2: Manual setup
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cp ../.env.example .env       # Then edit .env

# Seed demo data
python scripts/db_seed.py demo

# Run development server
cd backend
uvicorn app.main:app --reload

# Run tests
pytest
```

### Automation Scripts

| Script | Purpose |
|--------|---------|
| `scripts/dev_setup.py` | One-command dev environment setup |
| `scripts/run.py` | Start development server with hot reload |
| `scripts/db_seed.py` | Database seeding (demo/clear/reset/status) |
| `scripts/ci.py` | Run all CI checks locally |
| `scripts/ingest.py` | Run data ingestion (once or daemon) |
| `scripts/full_project_check.py` | Run all validation checks |
| `scripts/health_check.py` | Zero-dependency health checker |
| `backend/tools/api_smoke_test.py` | Quick API endpoint tests |
| `backend/tools/validate_ingestion.py` | Validate ingestion setup |

### Quick Start Files

| File | Platform | Purpose |
|------|----------|---------|
| `start.bat` | Windows | Double-click to start dev server |
| `start.ps1` | Windows PowerShell | PowerShell quick start |
| `start.sh` | Mac/Linux | Bash quick start |
| `Makefile` | Unix/WSL | Standard make commands |

### Production Deployment

```bash
# Connect to server
ssh root@67.217.244.241

# Run deployment script
curl -fsSL https://raw.githubusercontent.com/ianmerrill10/WaitedTheLongest/main/scripts/deploy.sh -o deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/api/animals` | GET | List animals (paginated, filterable) |
| `/api/animals/{id}` | GET | Animal details |
| `/api/longest-waiting` | GET | Top longest-waiting animals |
| `/api/success-stories` | GET/POST | Success stories |
| `/api/stats` | GET | Platform statistics |

### Key Query Parameters

```
GET /api/animals?
  species=dog           # Filter by species
  status=available      # Filter by status
  sort_by=days_waiting  # Sort field (default!)
  sort_order=desc       # Longest waiting first
  page=1               # Pagination
  page_size=20         # Items per page
```

## Data Sources

### Primary: RescueGroups.org
- Free API access
- Nationwide coverage
- Register: https://rescuegroups.org/services/adoptable-pet-data-api/

### Note on Petfinder
Petfinder does NOT have a public API. We discovered this during development and pivoted to RescueGroups.org.

## Monetization

### Amazon Associates (ID: waitingthelon-20)
- Pet supplies affiliate links
- Commission: 2-8% on pet products
- **CRITICAL**: Need 3 qualified sales within 180 days!

## Security Checklist

- [x] Non-root service user (waitingapp)
- [x] UFW firewall (22, 80, 443 only)
- [x] Fail2ban configured
- [x] SSL/TLS (Certbot)
- [x] Rate limiting in Nginx
- [x] Security headers
- [x] Automatic security updates

## Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_PASSWORD` - Redis authentication
- `RESCUEGROUPS_API_KEY` - Primary data source
- `AMAZON_ASSOCIATE_ID` - Affiliate tracking

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. **Update OWNERS_MANUAL.md with any functional changes**
5. Submit a pull request

### Documentation Requirements

All contributions must follow our documentation policy:
- Update `OWNERS_MANUAL.md` when changing functionality
- Include docstrings for all new functions
- Add header comments to new Python files
- See `backend/DOCUMENTATION_REQUIREMENTS.md` for full guidelines

## Documentation

- **OWNERS_MANUAL.md** - Comprehensive system guide (see note below)
- **backend/OWNERS_MANUAL_CONTENT.md** - Full manual content (copy to OWNERS_MANUAL.md)
- **backend/DOCUMENTATION_REQUIREMENTS.md** - Documentation policy
- **.github/PULL_REQUEST_TEMPLATE.md** - PR checklist
- **API Docs** - https://waitingthelongest.com/api/docs

> **Note**: If OWNERS_MANUAL.md is empty, copy content from `backend/OWNERS_MANUAL_CONTENT.md`:
> ```bash
> cp backend/OWNERS_MANUAL_CONTENT.md OWNERS_MANUAL.md
> ```

## License

Proprietary - All rights reserved.

---

**Mission**: Help shelter animals who have waited the longest find forever homes.

*© 2025 Waiting The Longest™*
