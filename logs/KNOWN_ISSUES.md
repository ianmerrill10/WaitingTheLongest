# Known Issues

This file tracks current known issues and blockers.

---

## Critical

*No critical issues currently identified*

---

## High Priority

### OAuth Credentials Not Configured
- **Status**: Pending
- **Description**: Google/Facebook OAuth needs real API keys
- **Files**: `backend/app/config.py`, `.env`
- **Notes**: Placeholders created, needs real credentials from user

### Production Database Migration
- **Status**: Pending
- **Description**: Need to migrate from SQLite demo to PostgreSQL production
- **Notes**: PostgreSQL 16 configured in production settings

---

## Medium Priority

### Test Coverage Gaps
- **Status**: Ongoing
- **Description**: Some agents lack comprehensive unit tests
- **Notes**: Basic test suite exists, needs expansion

### Redis Cache Not Running
- **Status**: Pending for production
- **Description**: Redis needs to be started on production server
- **Notes**: Configuration ready in `.env.production`

---

## Low Priority

### Documentation Gaps
- **Status**: Ongoing
- **Description**: Some agents need better inline comments
- **Notes**: Most critical agents documented

### Logging Consistency
- **Status**: Ongoing
- **Description**: Log formats vary across agents
- **Notes**: Consider adding structured logging

---

## Recently Resolved

| Date | Issue | Resolution |
|------|-------|------------|
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
