# AWS Amplify Deployment Guide

## Quick Deploy Options

### Option 1: Amplify Hosting (Frontend Only - Fastest)

This deploys just the frontend as a static site. You'll need a separate backend.

1. **Go to AWS Amplify Console**: https://console.aws.amazon.com/amplify/
2. **Click "New app" → "Host web app"**
3. **Connect your GitHub repository**
4. **Configure build settings**:
   - Build command: (leave empty)
   - Build output directory: `frontend`
5. **Deploy!**

### Option 2: Full Stack with AWS App Runner (Recommended)

Deploy the backend API on AWS App Runner, frontend on Amplify.

#### Step 1: Deploy Backend to App Runner

```bash
# From the WaitingTheLongest directory
cd backend

# Build and push Docker image to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

docker build -t waitingthelongest-api .
docker tag waitingthelongest-api:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/waitingthelongest-api:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/waitingthelongest-api:latest
```

Then in AWS Console:
1. Go to **App Runner**: https://console.aws.amazon.com/apprunner/
2. Create service from ECR image
3. Configure: 1 vCPU, 2GB memory
4. Note the service URL (e.g., `https://xxxxx.us-east-1.awsapprunner.com`)

#### Step 2: Update Frontend API URL

Edit `frontend/index.html` and set:
```html
<meta name="wtl-api-base-url" content="https://YOUR-APP-RUNNER-URL.awsapprunner.com">
```

#### Step 3: Deploy Frontend to Amplify

1. Push changes to GitHub
2. Go to Amplify Console
3. Connect repo, set build output to `frontend`
4. Deploy

---

## Option 3: Render.com (Free Tier Available)

### Backend
1. Go to https://render.com
2. New → Web Service
3. Connect GitHub repo
4. Root Directory: `backend`
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Frontend
1. New → Static Site  
2. Connect GitHub repo
3. Root Directory: `frontend`
4. Publish Directory: `.` (current directory)

---

## Option 4: Railway.app (Simple Full Stack)

1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Add two services:
   - Backend: Root = `backend`, Start = `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Frontend: Root = `frontend` (Static)

---

## Environment Variables (Backend)

Set these in your deployment platform:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host/db` |
| `CORS_ORIGINS` | Allowed origins | `https://your-frontend.com` |
| `ENVIRONMENT` | Environment name | `production` |
| `SECRET_KEY` | App secret key | (generate random) |

---

## Quick Test After Deployment

```bash
# Test backend
curl https://YOUR-BACKEND-URL/health
curl https://YOUR-BACKEND-URL/api/stats

# Open frontend in browser
open https://YOUR-FRONTEND-URL
```

---

## Troubleshooting

### "CORS Error" in browser
- Add your frontend URL to `CORS_ORIGINS` environment variable in backend
- Format: `CORS_ORIGINS=https://your-frontend.amplifyapp.com`

### "Animals not loading"
- Check the API URL in browser dev tools Network tab
- Verify `wtl-api-base-url` meta tag is set correctly
- Test backend directly: `curl YOUR-BACKEND-URL/api/animals`

### "Database error"
- Ensure `DATABASE_URL` is set for production
- Run migrations: `alembic upgrade head`
