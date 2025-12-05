# Waiting The Longest™

> **"Because Every Day Matters"** - A mission-driven pet adoption platform prioritizing shelter animals who have waited the longest for homes.

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

# Create virtual environment
cd backend
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp ../.env.example .env
# Edit .env with your settings

# Run development server
uvicorn app.main:app --reload
```

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
| `/healthz` | GET | Lightweight liveness probe for load balancers |
| `/readyz` | GET | Readiness probe (DB, dataset integrity, uptime) |
| `/api/animals` | GET | List animals (paginated, filterable) |
| `/api/animals/{id}` | GET | Animal details |
| `/api/longest-waiting` | GET | Top longest-waiting animals |
| `/api/success-stories` | GET/POST | Success stories |
| `/api/stats` | GET | Platform statistics |
| `/api/resources/rescues` | GET | Curated rescue directory with caching/ETag support |

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

### Secondary: Best Friends Network
- Scraped from bestfriends.org/partners directory
- ~6,000+ rescue organizations
- Custom scraper: `backend/tools/scrape_bestfriends_fast.py`

### AI Web Enrichment
- Crawls shelter websites for contact info
- Extracts: email, phone, address, social media URLs
- Agent: `backend/agents/web_enrichment_agent.py`

### CRITICAL: Petfinder Has No API - DO NOT USE

> **PERMANENT POLICY**: Petfinder does NOT have a public API. This has been confirmed multiple times. **DO NOT** attempt to integrate with Petfinder, reference a "Petfinder API" in code, or suggest it as a data source.
>
> See [NO_PETFINDER_API.md](NO_PETFINDER_API.md) for full details.
>
> Approved data sources: RescueGroups.org, Best Friends Network, individual shelter websites, state registries.

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

## Operational Readiness

### Health Probes

- `/health` exercises the SQLAlchemy session to guarantee connectivity.
- `/healthz` is a lightweight liveness ping for load balancers.
- `/readyz` verifies database reachability, counts animal rows, reports rescue directory version, and returns API uptime (seconds since process boot). Point orchestrators/systemd `ExecStartPost` checks here to block traffic until dependencies are ready.

### Rescue Directory Caching

The curated rescue directory (`/api/resources/rescues`) now returns `ETag`, `Cache-Control`, and `Vary` headers. Clients should cache responses for up to 15 minutes and use conditional requests (`If-None-Match`) to avoid re-downloading the large payload when nothing changed.

### Data Quality Automation

Run the structural validator anytime rescue metadata changes:

```bash
python backend/tools/rescue_directory_validator.py --fail-on-warn --dump-json
```

The `data-quality` job inside `.github/workflows/ci-cd.yml` executes the same validator on every pull request, ensuring the frontend widgets never receive malformed entries.

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

## Roadmap

- **Rescue Directory QA**: ship automated validation for Massachusetts licenses, transport region metadata, and AKC contact rotations so `/api/resources/rescues` can be refreshed weekly without regressions.
- **Frontend Completeness Sweep**: finish sitemap coverage, add link monitoring, and ensure every public page references the new rescue resources widgets.
- **Shelter CRM Hooks**: expose authenticated endpoints for partner orgs to edit contact data and drop duplicate listings directly from the dashboard.
- **Content Automation**: connect observation events to the TikTok/Twitter scheduler so longest-waiting pets automatically enter the storytelling queue.
- **Monetization Experiments**: expand beyond Amazon Associates with Chewy + direct-donate overlays while keeping disclosures centralized in `app.js`.

## License

Proprietary - All rights reserved.

---

**Mission**: Help shelter animals who have waited the longest find forever homes.

*© 2025 Waiting The Longest™*
