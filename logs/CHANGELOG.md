# Changelog

All notable changes to Waiting The Longest are documented here.

Format: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

### Added
- Project logging system (`logs/` folder)
- Master shelter database (1,170 organizations across 50 states)
- Per-state shelter JSON files
- State collection tracker

### Changed
- Consolidated multiple development versions into single `main` branch
- Merged shelter data from GitHub default branch

### Fixed
- N/A

### Removed
- Temporary nul files
- Duplicate development folders (cleaned up parent directory)

---

## [0.9.0] - 2025-12-07

### Added
- Complete unit test suite for agents
- PWA manifest and service worker
- 404 error page
- Loading skeletons for animal cards
- Infinite scroll for listings
- Image lazy loading
- Email signup form
- Social sharing buttons
- Sentry error monitoring configuration
- DEPLOYMENT.md documentation
- RUNBOOK.md operations manual
- .env.production template

### Changed
- Refactored CSS to use utility classes (removed inline styles)
- Added comprehensive docstrings to all agents

### Fixed
- Browser text-size-adjust compatibility
- State filter functionality

---

## [0.8.0] - 2025-12-06

### Added
- OAuth login (Google/Facebook)
- Rate limiting middleware

### Fixed
- State filter in frontend

---

## [0.7.0] - 2025-12-05

### Added
- AI Agent system (82 agents total)
  - 50 state discovery agents
  - 32 specialized agents
- Amazon Associates monetization
- Best Friends Network scraper
- RescueGroups.org integration

---

## [0.6.0] - Initial Release

### Added
- FastAPI backend
- SQLite/PostgreSQL database support
- Animal and shelter models
- Basic CRUD operations
- Frontend SPA (Vanilla JavaScript)
- Mobile-responsive design
- Nginx configuration
- Systemd service

---

## For AI Agents

When making changes:
1. Add entries under `[Unreleased]` section
2. Use categories: Added, Changed, Fixed, Removed, Security
3. When a version is released, create new version header with date
4. Keep descriptions concise but clear
