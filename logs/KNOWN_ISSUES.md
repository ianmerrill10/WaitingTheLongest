# Known Issues

This file tracks current known issues and blockers.

---

## Critical

*No critical issues currently identified*

---

## High Priority

### OAuth Credentials Not Configured
- **Status**: Ready for Configuration
- **Description**: Google/Facebook OAuth needs real API keys
- **Files**: `backend/app/config.py`, `.env.example`, `.env`
- **Notes**: Full documentation added to `.env.example` with setup instructions
- **Setup Guide**: See `.env.example` for step-by-step OAuth configuration

### Production Database Migration
- **Status**: Ready for Migration
- **Description**: Need to migrate from SQLite demo to PostgreSQL production
- **Notes**: PostgreSQL 16 configured, connection pooling set up, Alembic ready
- **Commands**: `alembic upgrade head` after PostgreSQL is running

---

## Medium Priority

### Test Coverage Gaps
- **Status**: ✅ RESOLVED 2025-12-11
- **Description**: Some agents lacked comprehensive unit tests
- **Resolution**: Added comprehensive tests in `test_specialized_agents.py`

### Redis Cache Not Running
- **Status**: Ready for Production
- **Description**: Redis needs to be started on production server
- **Notes**: Configuration ready in `.env.example` with optional Redis password
- **Commands**: `sudo systemctl start redis` on production server

---

## Low Priority

### Documentation Gaps
- **Status**: ✅ RESOLVED 2025-12-11
- **Description**: All critical agents now have documentation
- **Notes**: Agent README and inline comments updated

### Logging Consistency
- **Status**: ✅ RESOLVED 2025-12-11
- **Description**: Added structlog for structured logging
- **Notes**: structlog added to requirements.txt

---

## Recently Resolved

| Date | Issue | Resolution |
|------|-------|------------|
| 2025-12-11 | Missing Sentry integration | Added sentry-sdk to requirements, integrated with FastAPI |
| 2025-12-11 | Test coverage gaps | Created comprehensive agent tests |
| 2025-12-11 | Documentation gaps | Updated .env.example with full configuration guide |
| 2025-12-11 | Frontend API URL hardcoded | Made API URL dynamic based on environment |
| 2025-12-11 | Multiple project versions | Consolidated to single main branch |
| 2025-12-07 | CSS inline styles | Added utility classes |
| 2025-12-07 | Browser text-size-adjust | Added CSS property |
| 2025-12-06 | State filter not working | Fixed in frontend |

---

## For AI Agents

When you discover a new issue:
1. Add it to the appropriate priority section above
2. Include: Status, Description, Files affected, Notes
3. When resolved, move to "Recently Resolved" table with date

When resolving an issue:
1. Document the solution in `PROBLEMS_SOLVED.md`
2. Move the issue to "Recently Resolved" in this file
3. Update `PROJECT_CONTEXT.md` if it was listed there
