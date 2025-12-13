# Next 50 Tasks (Working Backlog)

Generated: 2025-12-13

This is a pragmatic, ordered backlog to get from “works locally” to “works hosted + regularly ingesting + reliable”.

## Hosted backend (unblock real demo)
1. Deploy backend container to AWS App Runner (ECR push + service create).
2. Set App Runner env: `SECRET_KEY` (strong random).
3. Set App Runner env: `DATABASE_URL` (Postgres for production; SQLite only for demo).
4. Set App Runner env: `CORS_ORIGINS` to include Amplify domain(s).
5. Confirm App Runner `/health` reachable publicly.
6. Confirm App Runner `/api/animals` returns JSON.
7. Update Amplify frontend `wtl-api-base-url` meta tag to App Runner URL.
8. Redeploy Amplify frontend.
9. Add a basic “prod smoke check” script (calls `/health` + `/api/longest-waiting`).
10. Document the final backend URL(s) in `RUNBOOK.md`.

## Data ingestion (core product value)
11. Obtain and configure `RESCUEGROUPS_API_KEY` in hosted env.
12. Run ingestion once manually against hosted DB.
13. Verify “longest waiting” ordering matches `first_seen_at` logic.
14. Add dedupe checks (external_id + perceptual hash) validation report.
15. Add ingestion rate limiting + retry/backoff for API reliability.
16. Add “ingestion run summary” table/log record.
17. Ensure ingestion is idempotent (re-run doesn’t explode counts).
18. Add “stale listing cleanup” policy and verify it.
19. Add basic alert on ingestion failure (email/Sentry).
20. Verify ingestion works for both Dogs and Cats.

## Regular testing + automation
21. Push the new scheduled tests workflow to GitHub.
22. Decide whether scheduled tests should auto-commit logs (yes/no).
23. If yes: add workflow step to commit `logs/TESTING_LOG.md` + `logs/FILES_TESTED.json`.
24. Add a “nightly docker build smoke test” workflow job (optional).
25. Add a one-command local check: `python scripts/run_parallel_agents.py --with-docker`.
26. Add a quick API contract smoke test (httpx) for `/api/longest-waiting`.
27. Add a lightweight performance check (p95 response time baseline).
28. Add coverage target / trend (optional).
29. Add lint/type to Windows dev instructions.
30. Update `logs/TESTING_LOG.md` conventions for new workflows.

## Database + migrations (production readiness)
31. Stand up Postgres (RDS or managed) for production.
32. Run Alembic migrations on Postgres.
33. Confirm indexes exist for “longest waiting” query.
34. Add nightly DB backup policy.
35. Add connection pool config for App Runner.

## OAuth / auth (if needed for user features)
36. Decide if OAuth is required for MVP.
37. Configure Google OAuth keys and redirect URIs.
38. Configure Facebook OAuth keys (if used).
39. Add a minimal auth smoke test (login endpoint responds).

## Frontend polish (MVP quality)
40. Verify frontend handles empty dataset gracefully.
41. Add clear “data last updated” timestamp on UI (from API).
42. Add error banner for API unreachable (CORS/network).
43. Confirm mobile layout for key pages.
44. Confirm SEO basics (title/description/OG tags).

## Observability + ops
45. Confirm Sentry is configured for hosted backend.
46. Add structured logs correlation ID per request.
47. Add `/health` to include DB connectivity (optional toggle).
48. Add deployment checklist to `DEPLOY_AWS_APP_RUNNER.md`.
49. Add cost guardrails (App Runner min instances, scaling).
50. Add a “rollback” playbook (previous image tag + redeploy).
