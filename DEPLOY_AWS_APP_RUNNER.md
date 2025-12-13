# Deploy Backend on AWS App Runner (Docker)

This is the fastest path to a hosted backend that your Amplify static frontend can call.

## Prereqs
- AWS account access
- AWS CLI configured locally
- Docker installed locally

## 1) Build and run locally (sanity)
From repo root:

- Build:
  - `docker build -t waitingthelongest-backend:local -f backend/Dockerfile backend`
- Run:
  - `docker run --rm -p 8000:8000 -e PORT=8000 -e DATABASE_URL=sqlite:///./waitingthelongest.db waitingthelongest-backend:local`
- Verify:
  - `http://127.0.0.1:8000/health`

## 2) Push image to ECR
1. Create a repo (one-time):
   - `aws ecr create-repository --repository-name waitingthelongest-backend`
2. Login Docker to ECR:
   - `aws ecr get-login-password | docker login --username AWS --password-stdin <account_id>.dkr.ecr.<region>.amazonaws.com`
3. Tag and push:
   - `docker tag waitingthelongest-backend:local <account_id>.dkr.ecr.<region>.amazonaws.com/waitingthelongest-backend:latest`
   - `docker push <account_id>.dkr.ecr.<region>.amazonaws.com/waitingthelongest-backend:latest`

## 3) Create App Runner service
- In AWS Console → App Runner → Create service
- Source: ECR (the repo/image you pushed)
- Port: `8000`
- Env vars (minimum recommended):
  - `DATABASE_URL` (use Postgres in production; SQLite is fine for a demo)
  - `SECRET_KEY` (set to a secure random value)
  - `CORS_ORIGINS` (JSON array string, include your Amplify URL)

Example `CORS_ORIGINS` value:

```json
["https://<your-amplify-app>.amplifyapp.com","https://<your-custom-domain>"]
```

## 4) Point Amplify frontend at the hosted backend
Because Amplify is static hosting, the frontend defaults to same-origin API calls.
To use a different backend origin, set the meta tag in `frontend/index.html`:

```html
<meta name="wtl-api-base-url" content="https://<your-app-runner-service-url>" />
```

Then redeploy the frontend.

## Notes
- App Runner sets `PORT` for you in many setups; the Docker image honors it.
- If you later enable Redis or Postgres, switch `DATABASE_URL`/`REDIS_URL` and redeploy.

---

## Deployment Checklist

Before going live, verify each item:

### Pre-deploy
- [ ] Docker builds locally: `docker build -t waitingthelongest-backend:local -f backend/Dockerfile backend`
- [ ] Container runs locally: `docker run --rm -p 8000:8000 -e PORT=8000 -e DATABASE_URL=sqlite:///./test.db -e SECRET_KEY=dev waitingthelongest-backend:local`
- [ ] Health check passes: `curl http://127.0.0.1:8000/health`
- [ ] API smoke test passes: `python backend/tools/api_smoke_test.py`

### ECR Push
- [ ] ECR repo exists: `aws ecr describe-repositories --repository-names waitingthelongest-backend`
- [ ] Docker logged in to ECR
- [ ] Image tagged and pushed

### App Runner Service
- [ ] Service created with correct ECR image
- [ ] Port set to `8000`
- [ ] `SECRET_KEY` env var set (strong random value)
- [ ] `DATABASE_URL` env var set (SQLite for demo, Postgres for prod)
- [ ] `CORS_ORIGINS` env var set (includes Amplify domain)
- [ ] Service health check passes (App Runner console or `scripts/health_check.py <url>`)

### Frontend Integration
- [ ] `frontend/index.html` has `<meta name="wtl-api-base-url" content="https://<app-runner-url>">`
- [ ] Frontend redeployed to Amplify
- [ ] Cross-origin requests work (no CORS errors in browser console)
- [ ] Animals display correctly (or empty state if no data yet)

### Post-deploy Validation
- [ ] Run `python scripts/health_check.py https://<app-runner-url>`
- [ ] Run `python backend/tools/api_smoke_test.py --base-url https://<app-runner-url>`
- [ ] Manual browser test: load site, check filters, check animal detail

---

## Rollback

If something breaks:

1. **Quick rollback (previous image):**
   - In App Runner console → your service → Configuration → Source
   - Update to previous image tag (e.g., `:previous` if you tagged it)
   - Deploy

2. **Emergency stop:**
   - Pause service in App Runner console (stops billing, keeps config)

3. **Frontend rollback:**
   - Redeploy previous Amplify version from Amplify console → Deployments

