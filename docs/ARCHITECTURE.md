# Waiting The Longest™ - Architecture

This document describes the architecture of the Waiting The Longest™ platform.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USERS                                    │
│            Web Browser / Mobile / API Consumers                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        VERCEL EDGE                               │
│     CDN / Static Assets / Serverless Functions / Headers        │
└─────────────────────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   STATIC    │    │    API      │    │   ASSETS    │
    │   FRONTEND  │    │  (FastAPI)  │    │   (CDN)     │
    │   index.html│    │  /api/*     │    │  images/    │
    └─────────────┘    └─────────────┘    └─────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      DATABASE       │
                    │    (PostgreSQL)     │
                    │   SQLite (demo)     │
                    └─────────────────────┘
```

## Components

### Frontend (SPA)

- **Technology**: Vanilla HTML/CSS/JavaScript
- **Features**:
  - Client-side routing (no page reloads)
  - PWA with service worker for offline support
  - Real-time wait counters
  - Dark mode support
  - Responsive design
  - Favorites (localStorage)
  - Social sharing

### Backend API

- **Technology**: FastAPI (Python 3.12)
- **Features**:
  - RESTful API design
  - OpenAPI/Swagger documentation
  - Rate limiting (slowapi)
  - Request ID tracking
  - CORS support
  - Pydantic validation

### Database

- **ORM**: SQLAlchemy 2.0
- **Development**: SQLite
- **Production**: PostgreSQL 16
- **Migrations**: Alembic

### Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    DATA INGESTION PIPELINE                    │
└──────────────────────────────────────────────────────────────┘
                               │
      ┌────────────────────────┼────────────────────────┐
      ▼                        ▼                        ▼
┌───────────┐          ┌───────────────┐        ┌───────────┐
│ RescueGroups │        │ Best Friends   │        │  Manual   │
│    API     │          │   Scraper     │        │   Entry   │
└───────────┘          └───────────────┘        └───────────┘
      │                        │                        │
      └────────────────────────┼────────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   DEDUPLICATION     │
                    │  (Perceptual Hash)  │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     DATABASE        │
                    │                     │
                    │  Animals ───────────┤
                    │  Observations ──────┤
                    │  Shelters ──────────┤
                    │  SuccessStories ────┤
                    └─────────────────────┘
```

## Database Schema

### Core Tables

```
animals (id, species, canonical_name, breed_primary, breed_secondary,
         color_primary, age_group, size, gender, status, photo_phash,
         first_seen_at, last_seen_at, transfer_count)

observations (id, animal_id, shelter_id, source, external_id, name,
              breed_primary, description, photo_url, photo_gallery_json,
              city, state, zip_code, listing_url, first_seen_at, last_seen_at)

shelters (id, name, source, external_id, email, phone, website,
          address, city, state, zip_code, latitude, longitude)

success_stories (id, animal_id, pet_name, adopter_name, story_text,
                 days_waited, photo_urls, adoption_date, is_featured)
```

### Monetization Tables

```
affiliate_clicks (id, product_id, program, ip_hash, source_page,
                  animal_id, clicked_at, converted)

email_subscribers (id, email, name, preferred_species, location_state,
                   is_verified, is_active, subscribed_at)
```

## Security

### Headers (via Vercel)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

### API Security
- Rate limiting per IP
- Input validation via Pydantic
- SQL injection prevention via SQLAlchemy ORM
- CORS whitelist configuration

## Deployment

### Vercel (Current)
- Serverless Python functions
- Static file CDN
- Automatic HTTPS
- Preview deployments on PRs

### Docker (Alternative)
```yaml
services:
  backend:    # FastAPI application
  db:         # PostgreSQL 16
  redis:      # Cache (optional)
  frontend:   # Nginx serving static files
```

## Monitoring

### Logging
- Structured logging with structlog
- Request ID tracking
- Error aggregation

### Metrics (Planned)
- Prometheus endpoint at `/api/metrics`
- Grafana dashboards
- Uptime monitoring

## Performance Optimizations

1. **Database**: Indexed queries on frequently filtered columns
2. **Caching**: Service worker for static assets
3. **Images**: Lazy loading, preloading, fallback placeholders
4. **API**: Response caching headers, gzip compression
5. **Frontend**: Skeleton loaders, optimistic UI

## Technology Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, CSS3, Vanilla JS |
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16 / SQLite |
| ORM | SQLAlchemy 2.0 |
| Deployment | Vercel / Docker |
| CI/CD | GitHub Actions |
| Monitoring | structlog, Sentry (planned) |
