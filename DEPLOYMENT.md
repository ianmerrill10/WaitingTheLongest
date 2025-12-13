# Waiting The Longest - Deployment Guide

> Comprehensive deployment documentation for production server setup

**Last Updated:** 2025-12-07
**Target Platform:** Ubuntu 24.04 LTS
**Server:** IONOS VPS (67.217.244.241)
**Domains:** waitingthelongest.com (primary), waitedthelongest.com (redirect)

---

## Table of Contents

1. [Server Requirements](#server-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Installation Steps](#installation-steps)
4. [Database Setup](#database-setup)
5. [Redis Setup](#redis-setup)
6. [Application Deployment](#application-deployment)
7. [Nginx Configuration](#nginx-configuration)
8. [SSL/Let's Encrypt Setup](#ssl-lets-encrypt-setup)
9. [Systemd Service Configuration](#systemd-service-configuration)
10. [Environment Variables](#environment-variables)
11. [Deployment Commands](#deployment-commands)
12. [Post-Deployment Verification](#post-deployment-verification)
13. [Troubleshooting](#troubleshooting)

---

## Server Requirements

### Minimum Hardware Specifications

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **RAM** | 2 GB | 4-8 GB |
| **Storage** | 20 GB SSD | 50+ GB SSD |
| **Bandwidth** | 1 TB/month | Unmetered |

### Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| **OS** | Ubuntu 24.04 LTS | Server operating system |
| **Python** | 3.12+ | Application runtime |
| **PostgreSQL** | 16+ | Primary database |
| **Redis** | 7.0+ | Caching and session storage |
| **Nginx** | 1.24+ | Reverse proxy and web server |
| **Certbot** | Latest | SSL certificate management |
| **Git** | Latest | Code deployment |

### Network Requirements

- Static IP address or reliable DNS
- Open ports:
  - **22** - SSH access
  - **80** - HTTP (redirects to HTTPS)
  - **443** - HTTPS
- DNS A records pointing to server IP:
  - `waitingthelongest.com`
  - `www.waitingthelongest.com`
  - `waitedthelongest.com`
  - `www.waitedthelongest.com`

---

## Pre-Deployment Checklist

Before beginning deployment, ensure you have:

- [ ] Root or sudo access to Ubuntu 24.04 server
- [ ] DNS records configured and propagated
- [ ] Domain registrar access for verification
- [ ] SSH key pair configured for secure access
- [ ] Backup of any existing data
- [ ] API keys ready:
  - [ ] RescueGroups.org API key
  - [ ] Google OAuth credentials (optional)
  - [ ] Facebook OAuth credentials (optional)
  - [ ] Amazon Associates ID (already registered: `waitingthelon-20`)

---

## Installation Steps

### Step 1: Initial Server Setup

Connect to your server via SSH:

```bash
ssh root@67.217.244.241
```

Update system packages:

```bash
apt update && apt upgrade -y
```

### Step 2: Install System Dependencies

Install all required packages:

```bash
apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql-16 \
    postgresql-contrib \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    ufw \
    fail2ban \
    htop \
    unattended-upgrades
```

### Step 3: Create Application User

For security, run the application as a non-root user:

```bash
# Create dedicated user
useradd -r -m -s /bin/bash waitingapp

# Verify user creation
id waitingapp
```

### Step 4: Create Directory Structure

```bash
# Create application directories
mkdir -p /opt/waitingthelongest/{backend,frontend,data/{videos,images,uploads}}
mkdir -p /var/log/waitingthelongest

# Set ownership
chown -R waitingapp:waitingapp /opt/waitingthelongest
chown -R waitingapp:waitingapp /var/log/waitingthelongest

# Set permissions
chmod 755 /opt/waitingthelongest
chmod 755 /var/log/waitingthelongest
```

---

## Database Setup

### PostgreSQL Installation and Configuration

PostgreSQL should already be installed from Step 2. Now configure it:

#### 1. Start PostgreSQL Service

```bash
systemctl enable postgresql
systemctl start postgresql
systemctl status postgresql
```

#### 2. Create Database and User

Generate a secure password first:

```bash
# Generate a secure password (save this!)
DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)
echo "Database Password: $DB_PASSWORD"
```

Create the database and user:

```bash
sudo -u postgres psql << EOF
-- Create database
CREATE DATABASE waiting_the_longest;

-- Create user with secure password
CREATE USER waiting_user WITH PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE waiting_the_longest TO waiting_user;
ALTER DATABASE waiting_the_longest OWNER TO waiting_user;

-- Connect to database and grant schema permissions
\c waiting_the_longest
GRANT ALL ON SCHEMA public TO waiting_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO waiting_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO waiting_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO waiting_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO waiting_user;
EOF
```

#### 3. Configure PostgreSQL for Production

Edit PostgreSQL configuration:

```bash
nano /etc/postgresql/16/main/postgresql.conf
```

Recommended settings for production:

```conf
# Connection Settings
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_line_prefix = '%m [%p] %u@%d '
log_timezone = 'UTC'
```

Edit authentication configuration:

```bash
nano /etc/postgresql/16/main/pg_hba.conf
```

Ensure local connections are allowed:

```conf
# IPv4 local connections:
host    waiting_the_longest    waiting_user    127.0.0.1/32    scram-sha-256
```

Restart PostgreSQL:

```bash
systemctl restart postgresql
```

#### 4. Test Database Connection

```bash
# Test connection
psql -h localhost -U waiting_user -d waiting_the_longest -c "SELECT version();"
```

#### 5. Initialize Database Schema

The database schema will be automatically created when the application starts for the first time via SQLAlchemy's `create_all()` method. Alternatively, run migrations manually:

```bash
cd /opt/waitingthelongest/backend
source venv/bin/activate
python -c "from app.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
```

---

## Redis Setup

### Configure Redis for Production

#### 1. Generate Redis Password

```bash
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)
echo "Redis Password: $REDIS_PASSWORD"
```

#### 2. Backup Original Configuration

```bash
cp /etc/redis/redis.conf /etc/redis/redis.conf.backup
```

#### 3. Configure Redis

Edit Redis configuration:

```bash
nano /etc/redis/redis.conf
```

Add or modify these settings:

```conf
# Bind to localhost only (security)
bind 127.0.0.1 ::1

# Require password authentication
requirepass YOUR_REDIS_PASSWORD_HERE

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence settings
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

#### 4. Start Redis Service

```bash
systemctl enable redis-server
systemctl restart redis-server
systemctl status redis-server
```

#### 5. Test Redis Connection

```bash
redis-cli -a "$REDIS_PASSWORD" ping
# Should return: PONG
```

---

## Application Deployment

### Step 1: Clone Repository

```bash
cd /opt/waitingthelongest
git clone https://github.com/ianmerrill10/WaitingTheLongest.git .
```

Or use the deployment script:

```bash
curl -fsSL https://raw.githubusercontent.com/ianmerrill10/WaitingTheLongest/main/scripts/deploy.sh -o deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

### Step 2: Setup Python Virtual Environment

```bash
cd /opt/waitingthelongest/backend

# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Deploy Frontend Files

```bash
# Copy frontend files
cp -r /opt/waitingthelongest/frontend/* /opt/waitingthelongest/frontend/

# Set permissions
chown -R waitingapp:waitingapp /opt/waitingthelongest/frontend
chmod -R 755 /opt/waitingthelongest/frontend
```

### Step 4: Configure Environment Variables

Create the `.env` file:

```bash
nano /opt/waitingthelongest/backend/.env
```

See [Environment Variables](#environment-variables) section for complete configuration.

### Step 5: Set File Permissions

```bash
# Set ownership
chown -R waitingapp:waitingapp /opt/waitingthelongest

# Secure .env file
chmod 600 /opt/waitingthelongest/backend/.env
```

---

## Nginx Configuration

### Step 1: Copy Configuration File

```bash
cp /opt/waitingthelongest/nginx/waitingthelongest.conf /etc/nginx/sites-available/waitingthelongest
```

### Step 2: Create Symbolic Link

```bash
ln -s /etc/nginx/sites-available/waitingthelongest /etc/nginx/sites-enabled/
```

### Step 3: Remove Default Site

```bash
rm /etc/nginx/sites-enabled/default
```

### Step 4: Test Nginx Configuration

```bash
nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Step 5: Reload Nginx

```bash
systemctl reload nginx
```

### Nginx Configuration Details

The configuration includes:

- **Rate Limiting**: Prevents abuse
  - API endpoints: 10 requests/second (burst 20)
  - General pages: 30 requests/second (burst 50)
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Gzip Compression**: Reduces bandwidth usage
- **SSL/TLS**: Strong cipher suites, OCSP stapling
- **Proxy Configuration**: Forwards API requests to FastAPI backend
- **Static File Caching**: 30-day cache for assets
- **Domain Redirects**: waitedthelongest.com → waitingthelongest.com

---

## SSL/Let's Encrypt Setup

### Step 1: Install Certbot

Certbot should already be installed. Verify:

```bash
certbot --version
```

### Step 2: Obtain SSL Certificates

Before running Certbot, ensure:
- DNS records are pointing to your server
- Nginx is running
- Port 80 is accessible

Run Certbot:

```bash
certbot --nginx -d waitingthelongest.com -d www.waitingthelongest.com -d waitedthelongest.com -d www.waitedthelongest.com
```

Follow the prompts:
1. Enter email address for renewal notifications
2. Agree to terms of service
3. Choose whether to redirect HTTP to HTTPS (recommended: Yes)

### Step 3: Verify SSL Installation

```bash
# Check certificate details
certbot certificates

# Test SSL configuration
curl -I https://waitingthelongest.com
```

### Step 4: Configure Automatic Renewal

Certbot automatically installs a renewal timer. Verify:

```bash
systemctl status certbot.timer
```

Test renewal process (dry run):

```bash
certbot renew --dry-run
```

### Step 5: Configure Renewal Hook

Create a post-renewal hook to reload Nginx:

```bash
cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF

chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh
```

---

## Systemd Service Configuration

### Step 1: Copy Service File

```bash
cp /opt/waitingthelongest/systemd/waitingthelongest.service /etc/systemd/system/
```

### Step 2: Reload Systemd

```bash
systemctl daemon-reload
```

### Step 3: Enable Service

```bash
systemctl enable waitingthelongest
```

### Step 4: Start Service

```bash
systemctl start waitingthelongest
```

### Step 5: Check Service Status

```bash
systemctl status waitingthelongest
```

### Step 6: View Logs

```bash
# Follow live logs
journalctl -u waitingthelongest -f

# View recent logs
journalctl -u waitingthelongest -n 100

# View logs from specific time
journalctl -u waitingthelongest --since "1 hour ago"
```

### Service Configuration Details

The systemd service includes:

- **Automatic Restart**: Service restarts on failure
- **Dependency Management**: Waits for PostgreSQL and Redis
- **Security Hardening**:
  - NoNewPrivileges
  - PrivateTmp
  - ProtectSystem=strict
  - ProtectHome
  - Restricted system calls
- **Resource Limits**:
  - Memory: 1GB maximum
  - CPU: 80% quota
- **4 Gunicorn Workers**: Using Uvicorn worker class
- **Logging**: Access and error logs to `/var/log/waitingthelongest/`

---

## Environment Variables

Create `/opt/waitingthelongest/backend/.env` with the following configuration:

```bash
# ==============================================================================
# APPLICATION SETTINGS
# ==============================================================================
APP_NAME="Waiting The Longest™"
APP_TAGLINE="Because Every Day Matters"
DEBUG=false

# ==============================================================================
# SECURITY - GENERATE THESE!
# ==============================================================================
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=YOUR_SECURE_SECRET_KEY_HERE
JWT_SECRET_KEY=YOUR_SECURE_JWT_SECRET_HERE

# ==============================================================================
# DATABASE
# ==============================================================================
DATABASE_URL=postgresql://waiting_user:YOUR_DB_PASSWORD@localhost:5432/waiting_the_longest
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# ==============================================================================
# REDIS
# ==============================================================================
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=YOUR_REDIS_PASSWORD

# ==============================================================================
# DATA SOURCE APIs
# ==============================================================================
# RescueGroups.org (PRIMARY)
RESCUEGROUPS_API_KEY=your_rescuegroups_api_key_here

# ==============================================================================
# MONETIZATION - AMAZON ASSOCIATES
# ==============================================================================
AMAZON_ASSOCIATE_ID=waitingthelon-20

# ==============================================================================
# OAUTH AUTHENTICATION (Optional)
# ==============================================================================
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret

# ==============================================================================
# CORS SETTINGS
# ==============================================================================
CORS_ORIGINS=https://waitingthelongest.com,https://www.waitingthelongest.com,https://waitedthelongest.com

# ==============================================================================
# FILE STORAGE PATHS
# ==============================================================================
VIDEO_OUTPUT_DIR=/opt/waitingthelongest/data/videos
IMAGE_CACHE_DIR=/opt/waitingthelongest/data/images
UPLOAD_DIR=/opt/waitingthelongest/data/uploads

# ==============================================================================
# INGESTION SETTINGS
# ==============================================================================
INGEST_ENABLED=true
INGEST_PAGE_LIMIT=50
INGEST_INTERVAL_HOURS=6

# ==============================================================================
# RATE LIMITING
# ==============================================================================
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# ==============================================================================
# SOCIAL MEDIA APIs (Optional)
# ==============================================================================
TIKTOK_ACCESS_TOKEN=your_tiktok_access_token
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
FACEBOOK_PAGE_TOKEN=your_facebook_page_token
```

### Generating Secure Keys

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate database password
openssl rand -base64 32 | tr -d '/+=' | cut -c1-32

# Generate Redis password
openssl rand -base64 32 | tr -d '/+=' | cut -c1-32
```

---

## Deployment Commands

### Initial Deployment

```bash
# 1. Pull latest code
cd /opt/waitingthelongest
git pull origin main

# 2. Activate virtual environment
cd backend
source venv/bin/activate

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run database migrations (if applicable)
# python manage.py migrate  # If using migrations

# 5. Collect static files (if needed)
# python manage.py collectstatic --noinput

# 6. Restart services
sudo systemctl restart waitingthelongest
sudo systemctl reload nginx

# 7. Check status
sudo systemctl status waitingthelongest
```

### Update Deployment

```bash
# Quick update script
cd /opt/waitingthelongest
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart waitingthelongest
sudo systemctl status waitingthelongest
```

### Rollback Deployment

```bash
cd /opt/waitingthelongest
git log --oneline  # Find commit to rollback to
git checkout <commit-hash>
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart waitingthelongest
```

---

## Post-Deployment Verification

### Step 1: Check Service Health

```bash
# Check systemd service
systemctl status waitingthelongest

# Check Nginx
systemctl status nginx

# Check PostgreSQL
systemctl status postgresql

# Check Redis
systemctl status redis-server
```

### Step 2: Test API Endpoints

```bash
# Health check
curl https://waitingthelongest.com/health

# Lightweight liveness check
curl https://waitingthelongest.com/healthz

# Readiness probe (DB, dataset, uptime)
curl https://waitingthelongest.com/readyz

# API root
curl https://waitingthelongest.com/api/

# Animals endpoint
curl https://waitingthelongest.com/api/animals?page=1&page_size=10

# Stats endpoint
curl https://waitingthelongest.com/api/stats
```

### Step 3: Verify SSL

```bash
# Check SSL certificate
openssl s_client -connect waitingthelongest.com:443 -servername waitingthelongest.com < /dev/null

# Check SSL rating
curl -I https://waitingthelongest.com | grep -i strict-transport-security
```

### Step 4: Test Frontend

Visit in browser:
- https://waitingthelongest.com
- https://www.waitingthelongest.com
- https://waitedthelongest.com (should redirect)

### Step 5: Check Logs

```bash
# Application logs
tail -f /var/log/waitingthelongest/error.log
tail -f /var/log/waitingthelongest/access.log

# Systemd logs
journalctl -u waitingthelongest -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# PostgreSQL logs
tail -f /var/log/postgresql/postgresql-16-main.log
```

### Step 6: Monitor Resource Usage

```bash
# CPU and memory
htop

# Disk space
df -h

# Database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('waiting_the_longest'));"

# Active connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'waiting_the_longest';"
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check detailed logs
journalctl -u waitingthelongest -n 100 --no-pager

# Check if port is already in use
sudo netstat -tlnp | grep 8000

# Verify Python environment
cd /opt/waitingthelongest/backend
source venv/bin/activate
which python
python --version

# Test application manually
cd /opt/waitingthelongest/backend
source venv/bin/activate
python -m app.main
```

### Database Connection Issues

```bash
# Test connection
psql -h localhost -U waiting_user -d waiting_the_longest

# Check PostgreSQL is running
systemctl status postgresql

# Check connection settings in .env
cat /opt/waitingthelongest/backend/.env | grep DATABASE_URL

# View PostgreSQL logs
tail -f /var/log/postgresql/postgresql-16-main.log
```

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli -a "YOUR_REDIS_PASSWORD" ping

# Check Redis status
systemctl status redis-server

# View Redis logs
tail -f /var/log/redis/redis-server.log

# Check Redis configuration
grep -E "bind|requirepass" /etc/redis/redis.conf
```

### Nginx Issues

```bash
# Test configuration
nginx -t

# Check Nginx status
systemctl status nginx

# View error logs
tail -f /var/log/nginx/error.log

# Check if Nginx can connect to backend
curl http://127.0.0.1:8000/health
```

### SSL Certificate Issues

```bash
# Check certificate status
certbot certificates

# Test renewal
certbot renew --dry-run

# Check certificate expiration
openssl s_client -connect waitingthelongest.com:443 -servername waitingthelongest.com 2>/dev/null | openssl x509 -noout -dates
```

### Permission Issues

```bash
# Fix ownership
chown -R waitingapp:waitingapp /opt/waitingthelongest
chown -R waitingapp:waitingapp /var/log/waitingthelongest

# Fix permissions
chmod 755 /opt/waitingthelongest
chmod 600 /opt/waitingthelongest/backend/.env
chmod -R 755 /opt/waitingthelongest/frontend
```

### Performance Issues

```bash
# Check system resources
htop

# Check database performance
sudo -u postgres psql -d waiting_the_longest -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
sudo -u postgres psql -d waiting_the_longest -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Monitor application logs
tail -f /var/log/waitingthelongest/access.log | grep -E "200|500|404"
```

---

## Security Hardening Checklist

- [x] Non-root service user (waitingapp)
- [x] UFW firewall enabled (22, 80, 443 only)
- [x] Fail2ban configured for SSH and Nginx
- [x] SSL/TLS with Let's Encrypt
- [x] Strong cipher suites in Nginx
- [x] Security headers (HSTS, CSP, X-Frame-Options)
- [x] Rate limiting in Nginx
- [x] PostgreSQL password authentication
- [x] Redis password authentication
- [x] Restricted file permissions on .env
- [x] Automatic security updates enabled
- [x] Systemd security hardening (NoNewPrivileges, PrivateTmp, etc.)
- [ ] Regular security audits
- [ ] Intrusion detection system (optional)
- [ ] Log monitoring and alerting

---

## Additional Resources

- **Project Repository**: https://github.com/ianmerrill10/WaitingTheLongest
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/16/
- **Nginx Documentation**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org/docs/
- **Ubuntu Server Guide**: https://ubuntu.com/server/docs

---

**Mission**: Help shelter animals who have waited the longest find forever homes.

*© 2025 Waiting The Longest™*
