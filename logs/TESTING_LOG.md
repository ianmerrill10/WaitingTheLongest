# Testing Log

This log tracks what has been tested, what passed, what failed, and what was fixed.

## How this log is updated
- Manual: append an entry under **Entries**.
- Automated: `backend/tools/scheduled_tests.py` appends entries when scheduled tests are enabled.

## Entries

### 2025-12-13
- Scope: Backend core test suite
- Environment: Windows + Python 3.12 venv (`backend/.venv`)
- Command: `python -m pytest -q`
- Result: PASS (152 passed)
- Smoke test: Local API boot + key endpoints
- Endpoints: `GET /`, `GET /health`, `GET /api/animals`, `GET /api/longest-waiting`
- Result: PASS (200 responses; empty dataset is expected on fresh SQLite DB)
- Fixes applied:
  - `backend/requirements.txt`: added `email-validator==2.2.0` (required by Pydantic `EmailStr`)

### 2025-12-12
- Scope: Backend specialized-agent tests
- Command: `python -m pytest -q tests/test_specialized_agents.py`
- Result: PASS (50 passed)
- Fixes applied:
  - `backend/agents/specialized/data_quality_agent.py`: cleanup now matches schema (uses `Observation.shelter_id`, `Animal.first_seen_at`) and always returns expected keys.
  - `backend/agents/__init__.py` + `backend/agents/specialized/__init__.py`: added lazy-import hooks so `unittest.mock.patch('agents.specialized.*')` works reliably.
- Remaining known issues: None in this test suite

### 2025-12-12T13:52:57Z — Random file checks

- Count: 10
- Pass: 10
- Fail: 0
- See logs/FILES_TESTED.md for per-file status.

### 2025-12-12T13:54:35Z — Random file checks

- Count: 10
- Pass: 10
- Fail: 0
- See logs/FILES_TESTED.md for per-file status.

### 2025-12-13T04:05:45Z — Scheduled pytest run

- Scope: -q
- Command: `C:\Users\ianme\OneDrive\Desktop\waitingthelongestdevelopment\WAITINGTHELONGEST DEC 12 TRANSFER\waitingthelongest\WaitingTheLongest\backend\.venv\Scripts\python.exe -m pytest -q`
- Result: PASS (exit=0)
- Stdout/Stderr captured in worker logs (not embedded here by default).
