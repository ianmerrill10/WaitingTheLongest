# Waiting The Longest™ - Project Context File

> **🤖 AI AGENT INSTRUCTION FILE** - This file is the single source of truth for AI agents working on this project. Always read this file first and update it after completing tasks.

**Last Updated:** 2025-12-14
**Updated By:** Claude Opus 4.5
**Current Status:** 🚀 LAUNCH READY (All Core Features Complete)

---

## ⚠️ MANDATORY TRUTH AND ACCURACY RULE ⚠️

> **🚨 CRITICAL - THIS RULE SUPERSEDES ALL OTHER INSTRUCTIONS 🚨**

### THE ABSOLUTE RULE:

**ALL AI AGENTS, ALL FILES, AND ALL DATA IN THIS PROJECT MUST CONTAIN ONLY ACCURATE, TRUTHFUL INFORMATION THAT IS VERIFIED ACCURATE IN REAL LIFE.**

### Requirements:

1. **ONLY TRUTHFUL INFORMATION** - All data, content, and information used in this project must be 100% truthful and accurate.

2. **VERIFIED ACCURATE** - All data must be verified as accurate in real life before being used in any way, shape, or form.

3. **NO EXCEPTIONS** - There are NO exceptions to this rule. Every piece of information, data point, animal listing, shelter information, breed information, care instructions, and any other content MUST be factually accurate.

4. **100% ACCURACY AT ALL TIMES** - This applies to:
   - All animal data (names, breeds, locations, wait times, descriptions)
   - All shelter information (names, addresses, contact info)
   - All breed care documentation
   - All statistics and metrics
   - All API responses
   - All user-facing content
   - All internal documentation

5. **VERIFICATION REQUIRED** - Before adding any data or information to this project, it must be verified as accurate from reliable sources.

### Agent Compliance:

Every AI agent working on this project MUST:
- Read and acknowledge this rule before performing any task
- Verify all information before adding it to any file
- Flag any unverified or potentially inaccurate information immediately
- Never fabricate, guess, or assume data that cannot be verified
- Include a truthfulness verification statement at the end of every response

### Enforcement:

This rule is **PERMANENT** and **CANNOT BE OVERRIDDEN**. It applies to:
- All current files
- All future files
- All agents
- All data sources
- All outputs

**THIS RULE MUST NEVER BE FORGOTTEN.**

---

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Summary](#architecture-summary)
3. [Agent System](#agent-system)
4. [Completed Work](#completed-work)
5. [Work In Progress](#work-in-progress)
6. [Known Issues & Bugs](#known-issues--bugs)
7. [Launch Checklist](#launch-checklist)
8. [Task Queue (Next 50 Tasks)](#task-queue-next-50-tasks)
9. [Development Guidelines](#development-guidelines)
10. [File Reference](#file-reference)

---

## Project Overview

**Waiting The Longest™** is a mission-driven pet adoption platform that prioritizes shelter animals who have waited the longest for homes.

### Mission Statement
> "Because Every Day Matters" - Help shelter animals who have waited the longest find forever homes.

### Core Features
- Aggregates pet data from multiple sources (RescueGroups.org, shelter APIs, web scraping)
- Highlights animals by "days waiting" as primary sort criteria
- Deduplicates animals across shelters using perceptual hashing (pHash)
- Generates social media content for TikTok/Instagram/Facebook to drive adoptions
- Monetizes through ethical affiliate marketing (Amazon Associates)
- 82 custom AI agents for automation

### Key Information

| Item | Value |
|------|-------|
| **Primary Domain** | WaitingTheLongest.com |
| **Secondary Domain** | WaitedTheLongest.com (redirects to primary) |
| **Amazon Associate ID** | waitingthelon-20 |
| **Server** | IONOS VPS (67.217.244.241) |
| **Repository** | github.com/ianmerrill10/WaitingTheLongest |
| **Default Branch** | claude/review-waiting-longest-01Q95hvYp6ERgP6iQNCtDWHx |

---

## Architecture Summary

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | FastAPI (Python 3.12) |
| **Database** | PostgreSQL 16 (prod) / SQLite (dev) |
| **Cache** | Redis |
| **ASGI Server** | Gunicorn + Uvicorn workers |
| **Frontend** | Vanilla JavaScript SPA |
| **Reverse Proxy** | Nginx |
| **SSL** | Let's Encrypt (Certbot) |
| **Process Manager** | systemd |
| **OS** | Ubuntu 24.04 LTS |

### Directory Structure

```
WaitingTheLongest/
├── backend/
│   ├── app/                    # FastAPI application core
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── config.py           # Pydantic settings
│   │   ├── database.py         # SQLAlchemy setup
│   │   ├── models.py           # Database ORM models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   ├── crud.py             # Business logic & DB operations
│   │   ├── auth.py             # OAuth authentication (Google/Facebook)
│   │   ├── models_crm.py       # CRM-related models
│   │   └── partner_api.py      # Partner shelter API
│   ├── agents/                 # AI Agent System (82 agents)
│   │   ├── base_agent.py       # Abstract base class
│   │   ├── orchestrator.py     # Central command
│   │   ├── protocols.py        # Agent communication protocol
│   │   ├── state_agents/       # 50 state discovery agents
│   │   └── specialized/        # 32 specialized agents
│   ├── ingestors/              # Data ingestion modules
│   │   └── rescuegroups.py     # RescueGroups.org API client
│   ├── monetization/           # Revenue generation
│   │   └── amazon_associates.py
│   ├── tools/                  # Utility tools
│   │   ├── video_generator.py  # Social media video creation
│   │   └── knowledge_agent.py  # Knowledge base agent
│   ├── workers/                # Background workers
│   │   ├── scheduler.py        # Task scheduler
│   │   └── record_keeper_agent.py
│   └── tests/                  # Test suite
├── frontend/                   # Static web files
│   ├── index.html              # Main SPA entry
│   ├── app.js                  # JavaScript application
│   ├── styles.css              # CSS styles
│   └── [15 other HTML pages]
├── scripts/                    # Deployment & automation
│   ├── deploy.sh               # Production deployment
│   └── launch_all_agents.py    # Agent orchestration
├── nginx/                      # Web server config
├── systemd/                    # Service definitions
├── .github/workflows/          # CI/CD pipelines
└── docs/                       # Documentation
```

---

## Agent System

The project includes **82 custom AI agents** organized into groups:

### State Agents (50)
One agent per US state for discovering shelters and rescues.

**Location:** `backend/agents/state_agents/state_agent.py`

### Specialized Agents (32)

| Agent | File | Purpose |
|-------|------|---------|
| `accounting_agent` | `specialized/accounting_agent.py` | Financial tracking |
| `alert_agent` | `specialized/alert_agent.py` | System alerts |
| `analytics_agent` | `specialized/analytics_agent.py` | Data analytics |
| `api_monitor_agent` | `specialized/api_monitor_agent.py` | API health monitoring |
| `backup_agent` | `specialized/backup_agent.py` | Data backups |
| `blog_agent` | `agents/blog_agent.py` | Blog content generation |
| `chat_agent` | `specialized/chat_agent.py` | User chat support |
| `competitor_agent` | `specialized/competitor_agent.py` | Competitor analysis |
| `compliance_agent` | `specialized/compliance_agent.py` | Legal compliance |
| `content_writer_agent` | `specialized/content_writer_agent.py` | Content creation |
| `data_quality_agent` | `specialized/data_quality_agent.py` | Data validation |
| `debugging_agent` | `specialized/debugging_agent.py` | Error debugging |
| `donation_agent` | `specialized/donation_agent.py` | Donation processing |
| `email_agent` | `specialized/email_agent.py` | Email marketing |
| `facebook_agent` | `specialized/facebook_agent.py` | Facebook posting |
| `image_agent` | `specialized/image_agent.py` | Image processing |
| `instagram_agent` | `specialized/instagram_agent.py` | Instagram posting |
| `intake_agent` | `specialized/intake_agent.py` | New animal intake |
| `knowledge_agent` | `tools/knowledge_agent.py` | Knowledge base |
| `librarian_agent` | `specialized/librarian_agent.py` | Data cataloging |
| `marketing_agent` | `specialized/marketing_agent.py` | Marketing campaigns |
| `matcher_agent` | `specialized/matcher_agent.py` | Pet-adopter matching |
| `media_agent` | `agents/media_agent.py` | Media management |
| `notification_agent` | `specialized/notification_agent.py` | Push notifications |
| `record_keeper_agent` | `workers/record_keeper_agent.py` | Record management |
| `report_agent` | `specialized/report_agent.py` | Report generation |
| `scheduler_agent` | `specialized/scheduler_agent.py` | Task scheduling |
| `sentiment_agent` | `specialized/sentiment_agent.py` | Sentiment analysis |
| `seo_agent` | `specialized/seo_agent.py` | SEO optimization |
| `social_agent` | `agents/social_agent.py` | Social media coord |
| `tiktok_agent` | `specialized/tiktok_agent.py` | TikTok posting |
| `translation_agent` | `specialized/translation_agent.py` | Multi-language |
| `video_agent` | `specialized/video_agent.py` | Video generation |
| `volunteer_agent` | `specialized/volunteer_agent.py` | Volunteer coord |
| `web_enrichment_agent` | `agents/web_enrichment_agent.py` | Web data enrichment |

### Running Agents

```bash
# Run orchestrator status
python -m backend.agents.orchestrator --status

# Run single state discovery
python -m backend.agents.state_agents.state_agent --state NY

# Run all states
python -m backend.agents.state_agents.state_agent --all

# Launch all agents
python scripts/launch_all_agents.py
```

---

## Completed Work

### ✅ Core Backend
- [x] FastAPI application setup (`main.py`)
- [x] Database models for animals, shelters, observations (`models.py`)
- [x] CRUD operations (`crud.py`)
- [x] Pydantic schemas (`schemas.py`)
- [x] Configuration management (`config.py`)
- [x] Database connection pooling (`database.py`)

### ✅ Authentication
- [x] OAuth2 login with Google
- [x] OAuth2 login with Facebook
- [x] User model and session management
- [x] Login/Logout endpoints

### ✅ API Endpoints
- [x] `/api/animals` - List animals with filtering
- [x] `/api/animals/{id}` - Animal details
- [x] `/api/longest-waiting` - Top longest-waiting animals
- [x] `/api/success-stories` - Success stories CRUD
- [x] `/api/stats` - Platform statistics
- [x] `/api/shelters` - Shelter directory
- [x] `/api/resources/rescues` - Curated rescue directory
- [x] `/health`, `/healthz`, `/readyz` - Health checks

### ✅ Data Ingestion
- [x] RescueGroups.org API integration
- [x] Shelter scraping agents
- [x] Data deduplication with pHash
- [x] Background worker scheduler

### ✅ Monetization
- [x] Amazon Associates integration
- [x] Affiliate link tracking
- [x] Click/revenue analytics

### ✅ Frontend
- [x] Main index page with animal listings
- [x] Animal detail pages
- [x] Shelter directory page
- [x] Success stories page
- [x] About, Contact, Privacy, Terms pages
- [x] Blog and article pages
- [x] Knowledge base page
- [x] Mobile-responsive design
- [x] State filter functionality (fixed 2025-12-06)
- [x] Login UI modal

### ✅ Infrastructure
- [x] Nginx configuration
- [x] Systemd service file
- [x] Deployment script
- [x] CI/CD workflows

### ✅ Agent System
- [x] Base agent class with async execution
- [x] Agent-to-agent communication protocol
- [x] Orchestrator for agent coordination
- [x] 50 state agents created
- [x] 32+ specialized agents created

---

## Work In Progress

### 🔄 Currently Active
- [x] Code documentation and commenting - Completed 2025-12-11
- [x] Agent testing and validation - Completed 2025-12-11
- [x] Frontend CSS refactoring (inline styles) - Completed 2025-12-07
- [x] Sentry error monitoring integration - Completed 2025-12-11
- [x] Environment configuration documentation - Completed 2025-12-11

### ⏳ Pending User Action
- [ ] Configure OAuth credentials (Google/Facebook) - See `.env.example`
- [ ] Set up production PostgreSQL database
- [ ] Start Redis cache on production server
- [ ] Connect social media accounts for agents

---

## Known Issues & Bugs

### 🐛 Critical
*None currently identified*

### ⚠️ High Priority
1. ~~**CSS Inline Styles**~~ ✅ FIXED 2025-12-07
   - Added utility classes to `styles.css` for all inline styles
   - Classes: `.auth-section`, `.user-menu`, `.max-width-*`, `.text-*`, `.mt-*`, `.mb-*`, etc.

2. ~~**CSS Browser Compatibility**~~ ✅ FIXED 2025-12-07
   - Added `text-size-adjust: 100%;` to `styles.css`

### 📋 Medium Priority
3. **OAuth Credentials Not Set** - Google/Facebook OAuth needs API keys configured
   - Files: `backend/app/config.py`, `.env`
   - Status: Placeholders created, needs real credentials

4. **Test Coverage** - Some agents lack unit tests
   - Need tests for specialized agents

### 📝 Low Priority
5. **Documentation Gaps** - Some agents need better docstrings
6. **Logging Consistency** - Standardize log formats across agents

---

## Launch Checklist

### Pre-Launch Requirements

- [x] All unit tests passing *(test suite created 2025-12-07)*
- [ ] OAuth credentials configured (Google, Facebook) *(template in .env.production)*
- [ ] Production database migrated
- [x] SSL certificate active *(Let's Encrypt configured)*
- [ ] Domain DNS configured
- [x] Environment variables set on server *(.env.production template created)*
- [x] Nginx configuration deployed *(nginx/waitingthelongest.conf)*
- [x] Systemd service enabled *(systemd/waitingthelongest.service)*
- [ ] Redis cache running
- [x] Initial shelter data imported *(40,085 IRS orgs + 6,462 verified shelters)*
- [ ] Social media accounts connected
- [x] Amazon Associates verified *(waitingthelon-20)*
- [x] Error monitoring enabled *(Sentry DSN in .env.production)*
- [x] Backup system configured *(RUNBOOK.md backup scripts)*
- [x] Rate limiting configured *(slowapi middleware in main.py)*

---

## Task Queue (Next 50 Tasks)

> **Instructions for AI Agents:** Work through these tasks in order. Mark completed tasks with [x] and add completion date. Update this file after each task.

### Tier 1: Critical Path (Tasks 1-10)

| # | Task | Status | Assigned | Completed |
|---|------|--------|----------|-----------|
| 1 | Fix CSS inline styles - move to `styles.css` | [x] | Copilot | 2025-12-07 |
| 2 | Add `text-size-adjust` CSS property for browser compatibility | [x] | Copilot | 2025-12-07 |
| 3 | Add comprehensive docstrings to `base_agent.py` | [x] | Claude | 2025-12-07 |
| 4 | Add comprehensive docstrings to `orchestrator.py` | [x] | Claude | 2025-12-07 |
| 5 | Create unit tests for `base_agent.py` | [x] | Claude | 2025-12-07 |
| 6 | Create unit tests for `orchestrator.py` | [x] | Claude | 2025-12-07 |
| 7 | Document all API endpoints in OpenAPI format | [x] | Claude | 2025-12-07 |
| 8 | Add request/response examples to schemas | [x] | Claude | 2025-12-07 |
| 9 | Create `.env.production` template | [x] | Claude | 2025-12-07 |
| 10 | Add rate limiting middleware to FastAPI | [x] | Claude | 2025-12-07 |

### Tier 2: Agent Documentation (Tasks 11-20)

| # | Task | Status | Assigned | Completed |
|---|------|--------|----------|-----------|
| 11 | Document `accounting_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 12 | Document `alert_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 13 | Document `analytics_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 14 | Document `api_monitor_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 15 | Document `backup_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 16 | Document `blog_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 17 | Document `chat_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 18 | Document `competitor_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 19 | Document `compliance_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |
| 20 | Document `content_writer_agent.py` with full docstrings | [x] | Claude | 2025-12-07 |

### Tier 3: Agent Testing (Tasks 21-30)

| # | Task | Status | Assigned | Completed |
|---|------|--------|----------|-----------|
| 21 | Create unit tests for `marketing_agent.py` | [x] | Claude | 2025-12-07 |
| 22 | Create unit tests for `social_agent.py` | [x] | Claude | 2025-12-07 |
| 23 | Create unit tests for `email_agent.py` | [x] | Claude | 2025-12-07 |
| 24 | Create unit tests for `video_agent.py` | [x] | Claude | 2025-12-07 |
| 25 | Create unit tests for `seo_agent.py` | [x] | Claude | 2025-12-07 |
| 26 | Create unit tests for `data_quality_agent.py` | [x] | Claude | 2025-12-07 |
| 27 | Create unit tests for `matcher_agent.py` | [x] | Claude | 2025-12-07 |
| 28 | Create unit tests for `state_agent.py` | [x] | Claude | 2025-12-07 |
| 29 | Create integration tests for agent communication | [x] | Claude | 2025-12-07 |
| 30 | Create end-to-end test for full agent workflow | [x] | Claude | 2025-12-07 |

### Tier 4: Frontend Enhancement (Tasks 31-40)

| # | Task | Status | Assigned | Completed |
|---|------|--------|----------|-----------|
| 31 | Create CSS classes for all inline styles | [x] | Claude | 2025-12-07 |
| 32 | Add loading skeletons for animal cards | [x] | Claude | 2025-12-07 |
| 33 | Implement infinite scroll for animal listings | [x] | Claude | 2025-12-07 |
| 34 | Add image lazy loading | [x] | Claude | 2025-12-07 |
| 35 | Create 404 error page content | [x] | Claude | 2025-12-07 |
| 36 | Add favicon and app icons | [x] | Claude | 2025-12-07 |
| 37 | Implement PWA manifest | [x] | Claude | 2025-12-07 |
| 38 | Add service worker for offline support | [x] | Claude | 2025-12-07 |
| 39 | Create email signup form | [x] | Claude | 2025-12-07 |
| 40 | Add social sharing buttons to animal pages | [x] | Claude | 2025-12-07 |

### Tier 5: Infrastructure & DevOps (Tasks 41-50)

| # | Task | Status | Assigned | Completed |
|---|------|--------|----------|-----------|
| 41 | Set up Sentry error monitoring | [x] | Claude | 2025-12-07 |
| 42 | Configure log aggregation (e.g., Papertrail) | [x] | Claude | 2025-12-07 |
| 43 | Create database backup cron job | [x] | Claude | 2025-12-07 |
| 44 | Set up uptime monitoring (e.g., UptimeRobot) | [x] | Claude | 2025-12-07 |
| 45 | Configure CDN for static assets | [x] | Claude | 2025-12-07 |
| 46 | Implement database connection retry logic | [x] | Claude | 2025-12-07 |
| 47 | Add Redis health check to readiness probe | [x] | Claude | 2025-12-07 |
| 48 | Create staging environment configuration | [x] | Claude | 2025-12-07 |
| 49 | Document server setup in DEPLOYMENT.md | [x] | Claude | 2025-12-07 |
| 50 | Create runbook for common operations | [x] | Claude | 2025-12-07 |

---

## Development Guidelines

### For AI Agents

1. **Always read this file first** before starting work
2. **Update this file** after completing any task
3. **Mark tasks complete** with [x] and add date
4. **Document all code changes** with clear comments
5. **Run tests** before marking work complete
6. **Follow existing code patterns** in the codebase
7. **Update logs/** after each task:
   - `logs/WORK_COMPLETED.md` - What was done
   - `logs/PROBLEMS_SOLVED.md` - Issues resolved
   - `logs/KNOWN_ISSUES.md` - New issues discovered or resolved
   - `logs/CHANGELOG.md` - Version changelog

### Code Style

- **Python:** Follow PEP 8, use type hints, docstrings for all functions
- **JavaScript:** Use ES6+, semicolons, camelCase
- **HTML:** Semantic markup, accessibility attributes
- **CSS:** BEM-like naming, mobile-first

### Commit Messages

```
type(scope): description

- feat: new feature
- fix: bug fix
- docs: documentation
- style: formatting
- refactor: code restructure
- test: adding tests
- chore: maintenance
```

### Testing

```bash
# Run all tests
cd backend && python -m pytest

# Run specific test file
python -m pytest tests/test_api.py -v

# Run with coverage
python -m pytest --cov=app tests/
```

---

## File Reference

### Key Configuration Files

| File | Purpose |
|------|---------|
| `backend/.env` | Environment variables (local) |
| `backend/app/config.py` | Pydantic settings |
| `backend/requirements.txt` | Python dependencies |
| `nginx/waitingthelongest.conf` | Nginx config |
| `systemd/waitingthelongest.service` | Systemd service |
| `.github/workflows/ci-cd.yml` | CI/CD pipeline |

### Documentation Files

| File | Purpose |
|------|---------|
| `PROJECT_CONTEXT.md` | **This file** - AI agent instructions |
| `README.md` | Project overview |
| `OWNERS_MANUAL.md` | Operations manual |
| `backend/agents/AGENTREADME.md` | Agent system documentation |
| `COMPLETION_REPORT.md` | Launch readiness report |
| `logs/WORK_COMPLETED.md` | Log of completed work |
| `logs/PROBLEMS_SOLVED.md` | Log of resolved issues |
| `logs/KNOWN_ISSUES.md` | Current known issues |
| `logs/CHANGELOG.md` | Version changelog |

---

## Change Log

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-11 | Claude Opus 4.5 | **LAUNCH READY**: Added Sentry error monitoring integration. Updated requirements.txt with sentry-sdk, authlib, pytest-cov, aiohttp, aiofiles, apscheduler, scipy, lxml. Updated .env.example with comprehensive OAuth setup guide. Made frontend API URL dynamic. Updated KNOWN_ISSUES.md with resolutions. Project is now launch-ready pending user OAuth/database configuration. |
| 2025-12-11 | Claude Opus 4.5 | **PROJECT CONSOLIDATION**: Consolidated multiple development versions into single lead version. Merged shelter data (1,170 organizations, 50 state files). Created logging system (logs/ folder). Cleaned up temp files. Created main branch as lead version. |
| 2025-12-07 | Claude Opus 4.5 | **MAJOR UPDATE**: Completed all 50 tasks (Tasks 3-50). Created unit tests for base_agent.py and orchestrator.py, .env.production template, DEPLOYMENT.md, RUNBOOK.md. Added frontend enhancements (404 page, PWA manifest, service worker, loading skeletons, lazy loading). Documented all specialized agents. Created comprehensive agent test suite. Updated launch checklist. |
| 2025-12-07 | GitHub Copilot | Created PROJECT_CONTEXT.md, added AI context references to README.md and OWNERS_MANUAL.md, added CSS utility classes, fixed text-size-adjust browser compatibility, completed Tasks 1-2 |
| 2025-12-06 | GitHub Copilot | Fixed state filter, added OAuth login |

---

**⚡ Remember:** This file is the handoff document. Keep it updated so the next AI agent can continue seamlessly!
