#!/bin/bash
# ==============================================================================
# Waiting The Longest™ - Master Deployment Script
# ==============================================================================
# This script deploys the complete platform on Ubuntu 24.04
#
# Usage:
#   chmod +x deploy.sh
#   sudo ./deploy.sh
#
# Server: IONOS VPS (67.217.244.241)
# Domains: WaitingTheLongest.com (primary), WaitedTheLongest.com (redirect)
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="waitingthelongest"
APP_USER="waitingapp"
APP_GROUP="waitingapp"
APP_DIR="/opt/waitingthelongest"
BACKEND_DIR="${APP_DIR}/backend"
FRONTEND_DIR="${APP_DIR}/frontend"
LOG_DIR="/var/log/waitingthelongest"

PRIMARY_DOMAIN="waitingthelongest.com"
REDIRECT_DOMAIN="waitedthelongest.com"

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# ==============================================================================
# PRE-FLIGHT CHECKS
# ==============================================================================

log "Starting Waiting The Longest Deployment"
log "============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo ./deploy.sh)"
fi

# Check Ubuntu version
if ! grep -q "24.04" /etc/os-release 2>/dev/null; then
    warn "This script is designed for Ubuntu 24.04. Proceeding anyway..."
fi

# ==============================================================================
# STEP 1: SYSTEM UPDATE & DEPENDENCIES
# ==============================================================================

log "Step 1: Installing system dependencies..."

apt update && apt upgrade -y

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

log "System dependencies installed"

# ==============================================================================
# STEP 2: CREATE APPLICATION USER (Security)
# ==============================================================================

log "Step 2: Creating application user..."

if ! id "$APP_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash "$APP_USER"
    log "User $APP_USER created"
else
    log "User $APP_USER already exists"
fi

# ==============================================================================
# STEP 3: CREATE DIRECTORIES
# ==============================================================================

log "Step 3: Creating directories..."

mkdir -p "$APP_DIR"/{backend,frontend,data/{videos,images,uploads}}
mkdir -p "$LOG_DIR"

chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
chown -R "$APP_USER:$APP_GROUP" "$LOG_DIR"
chmod 755 "$APP_DIR"
chmod 755 "$LOG_DIR"

log "Directories created"

# ==============================================================================
# STEP 4: GENERATE SECURE CREDENTIALS
# ==============================================================================

log "Step 4: Generating secure credentials..."

CREDENTIALS_FILE="$APP_DIR/.credentials"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

    cat > "$CREDENTIALS_FILE" << EOF
# Waiting The Longest - Secure Credentials
# Generated: $(date)
# KEEP THIS FILE SECURE!

DB_PASSWORD=$DB_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
SECRET_KEY=$SECRET_KEY
JWT_SECRET=$JWT_SECRET
EOF

    chmod 600 "$CREDENTIALS_FILE"
    chown root:root "$CREDENTIALS_FILE"

    log "Credentials generated and saved to $CREDENTIALS_FILE"
else
    log "Using existing credentials"
    source "$CREDENTIALS_FILE"
fi

# ==============================================================================
# STEP 5: CONFIGURE POSTGRESQL
# ==============================================================================

log "Step 5: Configuring PostgreSQL..."

# Start PostgreSQL
systemctl enable postgresql
systemctl start postgresql

# Create database and user
sudo -u postgres psql << EOF
-- Create database
CREATE DATABASE waiting_the_longest;

-- Create user with secure password
CREATE USER waiting_user WITH PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE waiting_the_longest TO waiting_user;
ALTER DATABASE waiting_the_longest OWNER TO waiting_user;

-- Grant schema permissions
\c waiting_the_longest
GRANT ALL ON SCHEMA public TO waiting_user;
EOF

log "PostgreSQL configured"

# ==============================================================================
# STEP 6: CONFIGURE REDIS
# ==============================================================================

log "Step 6: Configuring Redis..."

# Backup original config
cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# Configure Redis with password
cat >> /etc/redis/redis.conf << EOF

# Waiting The Longest configuration
requirepass $REDIS_PASSWORD
bind 127.0.0.1
maxmemory 256mb
maxmemory-policy allkeys-lru
EOF

systemctl enable redis-server
systemctl restart redis-server

log "Redis configured with authentication"

# ==============================================================================
# STEP 7: SETUP PYTHON ENVIRONMENT
# ==============================================================================

log "Step 7: Setting up Python environment..."

cd "$BACKEND_DIR"

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies (if requirements.txt exists)
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    log "Python dependencies installed from requirements.txt"
else
    # Install core dependencies
    pip install fastapi uvicorn gunicorn sqlalchemy psycopg2-binary redis \
                pydantic pydantic-settings python-dotenv requests pillow imagehash
    log "Core Python dependencies installed"
fi

# ==============================================================================
# STEP 8: CREATE .ENV FILE
# ==============================================================================

log "Step 8: Creating .env configuration..."

cat > "$BACKEND_DIR/.env" << EOF
# Waiting The Longest - Production Configuration
# Generated: $(date)

APP_NAME="Waiting The Longest"
APP_TAGLINE="Because Every Day Matters"
DEBUG=false

# Security
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET

# Database
DATABASE_URL=postgresql://waiting_user:${DB_PASSWORD}@localhost:5432/waiting_the_longest
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD

# Amazon Associates
AMAZON_ASSOCIATE_ID=waitingthelon-20

# CORS
CORS_ORIGINS=https://waitingthelongest.com,https://www.waitingthelongest.com,https://waitedthelongest.com

# File paths
VIDEO_OUTPUT_DIR=${APP_DIR}/data/videos
IMAGE_CACHE_DIR=${APP_DIR}/data/images
UPLOAD_DIR=${APP_DIR}/data/uploads
EOF

chmod 600 "$BACKEND_DIR/.env"
chown "$APP_USER:$APP_GROUP" "$BACKEND_DIR/.env"

log "Environment configuration created"

# ==============================================================================
# STEP 9: CONFIGURE FIREWALL (UFW)
# ==============================================================================

log "Step 9: Configuring firewall..."

ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall (non-interactive)
echo "y" | ufw enable

log "Firewall configured (SSH, HTTP, HTTPS only)"

# ==============================================================================
# STEP 10: CONFIGURE FAIL2BAN
# ==============================================================================

log "Step 10: Configuring Fail2ban..."

cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true

[nginx-botsearch]
enabled = true

[nginx-req-limit]
enabled = true
filter = nginx-req-limit
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 60
bantime = 600
EOF

systemctl enable fail2ban
systemctl restart fail2ban

log "Fail2ban configured"

# ==============================================================================
# STEP 11: CREATE SYSTEMD SERVICE
# ==============================================================================

log "Step 11: Creating systemd service..."

cat > /etc/systemd/system/waitingthelongest.service << EOF
[Unit]
Description=Waiting The Longest API
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$BACKEND_DIR/venv/bin/gunicorn app.main:app \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 127.0.0.1:8000 \\
    --access-logfile $LOG_DIR/access.log \\
    --error-logfile $LOG_DIR/error.log \\
    --log-level info
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable waitingthelongest

log "Systemd service created"

# ==============================================================================
# STEP 12: SETUP LOG ROTATION
# ==============================================================================

log "Step 12: Configuring log rotation..."

cat > /etc/logrotate.d/waitingthelongest << EOF
$LOG_DIR/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $APP_USER $APP_GROUP
    sharedscripts
    postrotate
        systemctl reload waitingthelongest > /dev/null 2>&1 || true
    endscript
}
EOF

log "Log rotation configured"

# ==============================================================================
# STEP 13: ENABLE AUTOMATIC SECURITY UPDATES
# ==============================================================================

log "Step 13: Enabling automatic security updates..."

cat > /etc/apt/apt.conf.d/20auto-upgrades << EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

log "Automatic security updates enabled"

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}   Waiting The Longest - Deployment Complete!         ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo ""
echo -e "${GREEN} System dependencies installed${NC}"
echo -e "${GREEN} Application user created: $APP_USER${NC}"
echo -e "${GREEN} PostgreSQL configured${NC}"
echo -e "${GREEN} Redis configured with authentication${NC}"
echo -e "${GREEN} Python environment ready${NC}"
echo -e "${GREEN} Firewall configured (UFW)${NC}"
echo -e "${GREEN} Fail2ban configured${NC}"
echo -e "${GREEN} Systemd service created${NC}"
echo -e "${GREEN} Log rotation configured${NC}"
echo -e "${GREEN} Automatic updates enabled${NC}"
echo ""
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "1. Deploy your application code to: $BACKEND_DIR"
echo "2. Deploy frontend files to: $FRONTEND_DIR"
echo "3. Configure DNS for both domains to point to this server"
echo "4. Run SSL setup: certbot --nginx -d $PRIMARY_DOMAIN -d www.$PRIMARY_DOMAIN -d $REDIRECT_DOMAIN -d www.$REDIRECT_DOMAIN"
echo "5. Start the service: systemctl start waitingthelongest"
echo ""
echo -e "${YELLOW}CREDENTIALS SAVED TO: $CREDENTIALS_FILE${NC}"
echo "   Database password, Redis password, and secret keys are stored there."
echo "   BACK UP THIS FILE AND KEEP IT SECURE!"
echo ""
echo -e "${GREEN}Mission: Help shelter animals who have waited the longest find forever homes!${NC}"
