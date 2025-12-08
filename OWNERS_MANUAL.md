# Owners Manual

> **🤖 AI Agents:** For task tracking and development context, see **[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)**

---

## 2025-12-04

- Added a curated rescue directory data module (`backend/app/data/rescue_directory.py`) and exposed it through a new FastAPI route `/api/resources/rescues`. The endpoint supports optional filters (`state`, `network_region`, `breed`) and returns summary counts for frontend widgets. Any future changes to the dataset structure should stay backward compatible with the existing response shape used by `frontend/shelters.html`.
- Refreshed `frontend/shelters.html`, `frontend/app.js`, and `frontend/styles.css` to surface live rescue directory metrics (counts, metadata, and error states) so visitors immediately see dataset coverage before browsing cards. Keep the summary IDs (`rescue-directory-summary`, `rescue-summary-panel`) stable because other pages may reuse the helper soon.
- Expanded `frontend/sitemap.html` and `README.md` to catalogue every public page (services, knowledge, blog, shelter directory, auth flows) and added a roadmap section that tracks the remaining enhancements. Update both files whenever new top-level pages or programs ship.
- Strengthened `/api/resources/rescues` regression coverage in `backend/tests/test_api.py` by asserting count accuracy against the source dataset and verifying that the `include_counts=false` flag suppresses aggregation. Run `pytest tests/test_api.py -v` after modifying directory data or filters.
- Hardened `/api/resources/rescues` with deterministic `ETag`/`Cache-Control` headers so the frontend and CDN can reuse cached copies for fifteen minutes. Tests now verify conditional requests return 304 responses when the payload is unchanged.
- Added `/healthz` (liveness) and `/readyz` (readiness) FastAPI routes. `/readyz` reports dependency checks, uptime, and the rescue directory version so systemd, nginx, and GitHub Actions can verify the stack before shifting traffic.
- Created `backend/tools/rescue_directory_validator.py` plus `backend/tests/test_rescue_directory_validator.py` to guarantee every entry shipped to shelters includes required metadata. CI now runs the validator via the new `data-quality` job in `.github/workflows/ci-cd.yml` and fails builds on structural regressions.
