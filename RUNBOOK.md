# Waiting The Longest - Operations Runbook

> Quick reference guide for common operations, troubleshooting, and emergency procedures

**Last Updated:** 2025-12-07
**Platform:** Ubuntu 24.04 LTS
**Server:** IONOS VPS (67.217.244.241)

---

## Table of Contents

1. [Common Operations](#common-operations)
2. [Service Management](#service-management)
3. [Log Management](#log-management)
4. [Database Operations](#database-operations)
5. [Redis Operations](#redis-operations)
6. [Monitoring Checks](#monitoring-checks)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Emergency Procedures](#emergency-procedures)
9. [Maintenance Windows](#maintenance-windows)
10. [Contact Information](#contact-information)

---

## Common Operations

### Quick Status Check

```bash
# Single command to check all services
systemctl status waitingthelongest postgresql redis-server nginx
```

### Service Health Check

```bash
# Check API health
curl https://waitingthelongest.com/health

# Check liveness (lightweight)
curl https://waitingthelongest.com/healthz

# Check readiness (comprehensive - DB, dataset, uptime)
curl https://waitingthelongest.com/readyz
```

### View Recent Logs

```bash
# Application logs (last 50 lines)
journalctl -u waitingthelongest -n 50

# Follow application logs in real-time
journalctl -u waitingthelongest -f

# Nginx access logs
tail -f /var/log/nginx/access.log

# Application error logs
tail -f /var/log/waitingthelongest/error.log
```

### Restart Services

```bash
# Restart application
sudo systemctl restart waitingthelongest

# Restart Nginx
sudo systemctl restart nginx

# Restart PostgreSQL
sudo systemctl restart postgresql

# Restart Redis
sudo systemctl restart redis-server

# Restart all services
sudo systemctl restart waitingthelongest nginx postgresql redis-server
```

### Deploy Code Updates

```bash
# Standard deployment procedure
cd /opt/waitingthelongest
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart waitingthelongest
sudo systemctl status waitingthelongest
```

---

## Service Management

### Application Service

```bash
# Start service
sudo systemctl start waitingthelongest

# Stop service
sudo systemctl stop waitingthelongest

# Restart service
sudo systemctl restart waitingthelongest

# Reload service (graceful restart)
sudo systemctl reload waitingthelongest

# Check status
sudo systemctl status waitingthelongest

# Enable on boot
sudo systemctl enable waitingthelongest

# Disable on boot
sudo systemctl disable waitingthelongest

# View service configuration
systemctl cat waitingthelongest
```

### Nginx Service

```bash
# Test configuration before reload
sudo nginx -t

# Reload configuration (no downtime)
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx

# View current configuration
nginx -T
```

### PostgreSQL Service

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Stop PostgreSQL
sudo systemctl stop postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Reload configuration
sudo systemctl reload postgresql

# Check status
sudo systemctl status postgresql
```

### Redis Service

```bash
# Start Redis
sudo systemctl start redis-server

# Stop Redis
sudo systemctl stop redis-server

# Restart Redis
sudo systemctl restart redis-server

# Check status
sudo systemctl status redis-server
```

---

## Log Management

### Application Logs

```bash
# View systemd logs
journalctl -u waitingthelongest

# Last 100 lines
journalctl -u waitingthelongest -n 100

# Follow logs (real-time)
journalctl -u waitingthelongest -f

# Logs from specific time
journalctl -u waitingthelongest --since "2025-12-07 10:00:00"

# Logs from last hour
journalctl -u waitingthelongest --since "1 hour ago"

# Only errors
journalctl -u waitingthelongest -p err

# Export logs to file
journalctl -u waitingthelongest --since today > app_logs_$(date +%Y%m%d).log
```

### Gunicorn Logs

```bash
# Access logs
tail -f /var/log/waitingthelongest/access.log

# Error logs
tail -f /var/log/waitingthelongest/error.log

# Search for specific errors
grep -i "error" /var/log/waitingthelongest/error.log

# Count 500 errors
grep "500" /var/log/waitingthelongest/access.log | wc -l

# View requests by IP
awk '{print $1}' /var/log/waitingthelongest/access.log | sort | uniq -c | sort -rn | head
```

### Nginx Logs

```bash
# Access logs
tail -f /var/log/nginx/access.log

# Error logs
tail -f /var/log/nginx/error.log

# Check for 404 errors
grep "404" /var/log/nginx/access.log

# Check for 500 errors
grep "500" /var/log/nginx/access.log

# Top requesting IPs
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# Requests per hour
awk '{print $4}' /var/log/nginx/access.log | cut -d: -f1-2 | sort | uniq -c
```

### PostgreSQL Logs

```bash
# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Search for errors
sudo grep -i error /var/log/postgresql/postgresql-16-main.log

# Check slow queries
sudo grep -i "duration" /var/log/postgresql/postgresql-16-main.log | grep -v "duration: 0"
```

### Redis Logs

```bash
# View Redis logs
sudo tail -f /var/log/redis/redis-server.log

# Check for connection issues
sudo grep -i "connection" /var/log/redis/redis-server.log

# Check for memory warnings
sudo grep -i "memory" /var/log/redis/redis-server.log
```

### Log Rotation

Log rotation is configured automatically. Check configuration:

```bash
# View logrotate config
cat /etc/logrotate.d/waitingthelongest

# Test logrotate
sudo logrotate -d /etc/logrotate.d/waitingthelongest

# Force log rotation
sudo logrotate -f /etc/logrotate.conf
```

---

## Database Operations

### Connection and Access

```bash
# Connect to database
sudo -u postgres psql -d waiting_the_longest

# Connect as application user
psql -h localhost -U waiting_user -d waiting_the_longest

# Run single query
sudo -u postgres psql -d waiting_the_longest -c "SELECT COUNT(*) FROM animals;"
```

### Database Backup

#### Manual Backup

```bash
# Create backup directory
sudo mkdir -p /opt/waitingthelongest/backups

# Full database backup
sudo -u postgres pg_dump waiting_the_longest | gzip > /opt/waitingthelongest/backups/waiting_the_longest_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup specific tables
sudo -u postgres pg_dump waiting_the_longest -t animals -t shelters | gzip > /opt/waitingthelongest/backups/core_tables_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup with custom format (faster restore)
sudo -u postgres pg_dump -Fc waiting_the_longest > /opt/waitingthelongest/backups/waiting_the_longest_$(date +%Y%m%d_%H%M%S).dump
```

#### Automated Backup Script

Create `/opt/waitingthelongest/scripts/backup_database.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/waitingthelongest/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/waiting_the_longest_$TIMESTAMP.sql.gz"

# Create backup
sudo -u postgres pg_dump waiting_the_longest | gzip > "$BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

Make it executable:

```bash
chmod +x /opt/waitingthelongest/scripts/backup_database.sh
```

#### Schedule Daily Backups

```bash
# Add to crontab
sudo crontab -e

# Add this line (runs at 2 AM daily)
0 2 * * * /opt/waitingthelongest/scripts/backup_database.sh >> /var/log/waitingthelongest/backup.log 2>&1
```

### Database Restore

```bash
# Stop application first
sudo systemctl stop waitingthelongest

# Restore from gzipped SQL backup
gunzip -c /opt/waitingthelongest/backups/waiting_the_longest_20251207_020000.sql.gz | sudo -u postgres psql waiting_the_longest

# Restore from custom format backup
sudo -u postgres pg_restore -d waiting_the_longest /opt/waitingthelongest/backups/waiting_the_longest_20251207_020000.dump

# Restore specific tables only
sudo -u postgres pg_restore -d waiting_the_longest -t animals -t shelters /opt/waitingthelongest/backups/backup.dump

# Start application
sudo systemctl start waitingthelongest
```

### Database Maintenance

```bash
# Vacuum database (reclaim space)
sudo -u postgres psql -d waiting_the_longest -c "VACUUM FULL VERBOSE;"

# Analyze database (update statistics)
sudo -u postgres psql -d waiting_the_longest -c "ANALYZE VERBOSE;"

# Reindex database
sudo -u postgres psql -d waiting_the_longest -c "REINDEX DATABASE waiting_the_longest;"

# Check database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('waiting_the_longest'));"

# Check table sizes
sudo -u postgres psql -d waiting_the_longest -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;"
```

### Database Monitoring

```bash
# Active connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'waiting_the_longest';"

# View active queries
sudo -u postgres psql -d waiting_the_longest -c "SELECT pid, usename, state, query FROM pg_stat_activity WHERE datname = 'waiting_the_longest' AND state = 'active';"

# Long-running queries
sudo -u postgres psql -d waiting_the_longest -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes';"

# Kill long-running query (if needed)
sudo -u postgres psql -c "SELECT pg_terminate_backend(PID);"
```

---

## Redis Operations

### Connection and Monitoring

```bash
# Connect to Redis
redis-cli -a "YOUR_REDIS_PASSWORD"

# Inside redis-cli:
# Check status
INFO

# Get memory usage
INFO memory

# Get stats
INFO stats

# Monitor commands in real-time
MONITOR

# Check connected clients
CLIENT LIST

# Get all keys (use carefully in production!)
KEYS *

# Count total keys
DBSIZE
```

### Redis Backup

```bash
# Trigger background save
redis-cli -a "YOUR_REDIS_PASSWORD" BGSAVE

# Check last save time
redis-cli -a "YOUR_REDIS_PASSWORD" LASTSAVE

# Copy RDB file
sudo cp /var/lib/redis/dump.rdb /opt/waitingthelongest/backups/redis_$(date +%Y%m%d_%H%M%S).rdb
```

### Redis Maintenance

```bash
# Clear all cache (use with caution!)
redis-cli -a "YOUR_REDIS_PASSWORD" FLUSHALL

# Clear specific database
redis-cli -a "YOUR_REDIS_PASSWORD" FLUSHDB

# Get memory usage
redis-cli -a "YOUR_REDIS_PASSWORD" INFO memory | grep used_memory_human

# Analyze keyspace
redis-cli -a "YOUR_REDIS_PASSWORD" --bigkeys
```

---

## Monitoring Checks

### System Health Check

```bash
#!/bin/bash
# Save as /opt/waitingthelongest/scripts/health_check.sh

echo "=== System Health Check ==="
echo "Date: $(date)"
echo ""

# Check services
echo "--- Service Status ---"
systemctl is-active waitingthelongest && echo "Application: OK" || echo "Application: FAILED"
systemctl is-active nginx && echo "Nginx: OK" || echo "Nginx: FAILED"
systemctl is-active postgresql && echo "PostgreSQL: OK" || echo "PostgreSQL: FAILED"
systemctl is-active redis-server && echo "Redis: OK" || echo "Redis: FAILED"
echo ""

# Check API endpoints
echo "--- API Health ---"
curl -sf https://waitingthelongest.com/health && echo "API Health: OK" || echo "API Health: FAILED"
curl -sf https://waitingthelongest.com/readyz && echo "API Readiness: OK" || echo "API Readiness: FAILED"
echo ""

# Check disk space
echo "--- Disk Usage ---"
df -h | grep -E "Filesystem|/$"
echo ""

# Check memory
echo "--- Memory Usage ---"
free -h
echo ""

# Check database connections
echo "--- Database Connections ---"
sudo -u postgres psql -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE datname = 'waiting_the_longest';"
echo ""

# Check SSL certificate expiry
echo "--- SSL Certificate ---"
echo | openssl s_client -connect waitingthelongest.com:443 -servername waitingthelongest.com 2>/dev/null | openssl x509 -noout -dates
echo ""
```

Make it executable:

```bash
chmod +x /opt/waitingthelongest/scripts/health_check.sh
```

### Resource Monitoring

```bash
# CPU and memory usage
htop

# Disk space
df -h

# Disk I/O
iostat -x 1

# Network usage
iftop

# Process list
ps aux | grep -E "gunicorn|postgres|redis|nginx"

# Check system load
uptime

# Check memory details
free -h

# Check swap usage
swapon --show
```

### Application Metrics

```bash
# Request rate (requests per second)
tail -1000 /var/log/nginx/access.log | awk '{print $4}' | cut -d: -f1-3 | sort | uniq -c

# Response time analysis
tail -1000 /var/log/waitingthelongest/access.log | awk '{print $NF}' | sort -n | tail -20

# Error rate
grep -c "500" /var/log/nginx/access.log

# Active Gunicorn workers
ps aux | grep gunicorn | grep -v grep | wc -l

# Database query count
sudo -u postgres psql -d waiting_the_longest -c "SELECT sum(calls) as total_queries FROM pg_stat_statements;"
```

### SSL Certificate Monitoring

```bash
# Check certificate expiration
echo | openssl s_client -connect waitingthelongest.com:443 -servername waitingthelongest.com 2>/dev/null | openssl x509 -noout -dates

# Days until expiration
echo | openssl s_client -connect waitingthelongest.com:443 -servername waitingthelongest.com 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2 | xargs -I {} date -d {} +%s | awk '{print int(($1 - systime()) / 86400)}'

# Check all certificates
certbot certificates
```

---

## Troubleshooting Guide

### Application Won't Start

**Symptom:** `systemctl start waitingthelongest` fails

**Steps:**

1. Check logs for errors:
   ```bash
   journalctl -u waitingthelongest -n 100 --no-pager
   ```

2. Verify dependencies are running:
   ```bash
   systemctl status postgresql redis-server
   ```

3. Test database connection:
   ```bash
   psql -h localhost -U waiting_user -d waiting_the_longest -c "SELECT 1;"
   ```

4. Test Redis connection:
   ```bash
   redis-cli -a "YOUR_REDIS_PASSWORD" ping
   ```

5. Check if port 8000 is in use:
   ```bash
   sudo netstat -tlnp | grep 8000
   ```

6. Try manual startup to see errors:
   ```bash
   cd /opt/waitingthelongest/backend
   source venv/bin/activate
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

7. Check environment file:
   ```bash
   cat /opt/waitingthelongest/backend/.env | grep -E "DATABASE_URL|REDIS"
   ```

### High CPU Usage

**Symptom:** Server is slow, high CPU usage

**Steps:**

1. Identify process:
   ```bash
   top
   # or
   htop
   ```

2. Check application workers:
   ```bash
   ps aux | grep gunicorn
   ```

3. Check for long-running queries:
   ```bash
   sudo -u postgres psql -d waiting_the_longest -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"
   ```

4. Kill problematic query if needed:
   ```bash
   sudo -u postgres psql -c "SELECT pg_terminate_backend(PID);"
   ```

5. Restart application:
   ```bash
   sudo systemctl restart waitingthelongest
   ```

### High Memory Usage

**Symptom:** Running out of memory

**Steps:**

1. Check memory usage:
   ```bash
   free -h
   ```

2. Check largest processes:
   ```bash
   ps aux --sort=-%mem | head -20
   ```

3. Check database memory:
   ```bash
   sudo -u postgres psql -d waiting_the_longest -c "SELECT pg_size_pretty(sum(pg_total_relation_size(table_name::regclass))::bigint) FROM information_schema.tables WHERE table_schema = 'public';"
   ```

4. Check Redis memory:
   ```bash
   redis-cli -a "YOUR_REDIS_PASSWORD" INFO memory | grep used_memory_human
   ```

5. Clear Redis cache if needed:
   ```bash
   redis-cli -a "YOUR_REDIS_PASSWORD" FLUSHALL
   ```

6. Consider adding swap or increasing server RAM

### Database Connection Pool Exhausted

**Symptom:** "Too many connections" errors

**Steps:**

1. Check active connections:
   ```bash
   sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'waiting_the_longest';"
   ```

2. View connection details:
   ```bash
   sudo -u postgres psql -c "SELECT pid, usename, state, query FROM pg_stat_activity WHERE datname = 'waiting_the_longest';"
   ```

3. Restart application to reset pool:
   ```bash
   sudo systemctl restart waitingthelongest
   ```

4. Increase pool size if needed (edit `.env`):
   ```bash
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=20
   ```

### SSL Certificate Issues

**Symptom:** Certificate expired or invalid

**Steps:**

1. Check certificate status:
   ```bash
   certbot certificates
   ```

2. Renew certificate:
   ```bash
   sudo certbot renew
   ```

3. Force renewal if needed:
   ```bash
   sudo certbot renew --force-renewal
   ```

4. Reload Nginx:
   ```bash
   sudo systemctl reload nginx
   ```

### Site is Slow

**Symptom:** Pages loading slowly

**Steps:**

1. Check response times:
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s https://waitingthelongest.com/api/animals
   ```

   Create `curl-format.txt`:
   ```
   time_namelookup:  %{time_namelookup}\n
   time_connect:  %{time_connect}\n
   time_appconnect:  %{time_appconnect}\n
   time_pretransfer:  %{time_pretransfer}\n
   time_redirect:  %{time_redirect}\n
   time_starttransfer:  %{time_starttransfer}\n
   ----------\n
   time_total:  %{time_total}\n
   ```

2. Check database query performance:
   ```bash
   sudo -u postgres psql -d waiting_the_longest -c "SELECT query, calls, mean_time, max_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
   ```

3. Enable query logging temporarily:
   ```bash
   sudo -u postgres psql -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"  # Log queries > 1s
   sudo systemctl reload postgresql
   ```

4. Check Redis hit rate:
   ```bash
   redis-cli -a "YOUR_REDIS_PASSWORD" INFO stats | grep keyspace
   ```

5. Optimize slow queries or add indexes

### Disk Space Full

**Symptom:** "No space left on device" errors

**Steps:**

1. Check disk usage:
   ```bash
   df -h
   ```

2. Find largest directories:
   ```bash
   du -h --max-depth=1 /opt/waitingthelongest | sort -hr
   du -h --max-depth=1 /var/log | sort -hr
   ```

3. Clear old logs:
   ```bash
   sudo journalctl --vacuum-time=7d
   sudo find /var/log -name "*.log.*" -mtime +30 -delete
   ```

4. Clear old backups:
   ```bash
   sudo find /opt/waitingthelongest/backups -name "*.sql.gz" -mtime +30 -delete
   ```

5. Clean package cache:
   ```bash
   sudo apt clean
   sudo apt autoremove
   ```

---

## Emergency Procedures

### Site is Down - Emergency Response

**Priority:** Get site back online ASAP

1. **Check if services are running:**
   ```bash
   systemctl status waitingthelongest nginx postgresql redis-server
   ```

2. **Start any stopped services:**
   ```bash
   sudo systemctl start waitingthelongest
   sudo systemctl start nginx
   ```

3. **Check error logs:**
   ```bash
   journalctl -u waitingthelongest -n 100
   tail -50 /var/log/nginx/error.log
   ```

4. **Quick restart all services:**
   ```bash
   sudo systemctl restart waitingthelongest nginx
   ```

5. **Verify site is back:**
   ```bash
   curl -I https://waitingthelongest.com
   ```

6. **If still down, rollback to previous version:**
   ```bash
   cd /opt/waitingthelongest
   git log --oneline -10  # Find last known good commit
   git checkout <commit-hash>
   sudo systemctl restart waitingthelongest
   ```

### Database Corruption

**Priority:** Restore from backup

1. **Stop application:**
   ```bash
   sudo systemctl stop waitingthelongest
   ```

2. **Assess damage:**
   ```bash
   sudo -u postgres psql -d waiting_the_longest -c "SELECT * FROM pg_stat_database WHERE datname = 'waiting_the_longest';"
   ```

3. **Restore from most recent backup:**
   ```bash
   # List available backups
   ls -lh /opt/waitingthelongest/backups/

   # Restore (adjust filename)
   gunzip -c /opt/waitingthelongest/backups/waiting_the_longest_LATEST.sql.gz | sudo -u postgres psql waiting_the_longest
   ```

4. **Start application:**
   ```bash
   sudo systemctl start waitingthelongest
   ```

5. **Verify data:**
   ```bash
   curl https://waitingthelongest.com/api/stats
   ```

### Security Breach

**Priority:** Contain and assess

1. **Immediately stop affected services:**
   ```bash
   sudo systemctl stop waitingthelongest nginx
   ```

2. **Check for unauthorized access:**
   ```bash
   last | head -20
   sudo grep -i "authentication failure" /var/log/auth.log
   ```

3. **Review fail2ban:**
   ```bash
   sudo fail2ban-client status sshd
   ```

4. **Check for modified files:**
   ```bash
   find /opt/waitingthelongest -type f -mtime -1
   ```

5. **Review nginx access logs for suspicious activity:**
   ```bash
   awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20
   ```

6. **Rotate all passwords:**
   - Database password
   - Redis password
   - SECRET_KEY and JWT_SECRET_KEY
   - SSH keys

7. **Restore from clean backup if compromised**

8. **Contact security team (see contact info below)**

### Data Loss Prevention

**If you suspect data loss is imminent:**

1. **Immediate database backup:**
   ```bash
   sudo -u postgres pg_dump waiting_the_longest | gzip > /opt/waitingthelongest/backups/emergency_backup_$(date +%Y%m%d_%H%M%S).sql.gz
   ```

2. **Copy to remote location:**
   ```bash
   scp /opt/waitingthelongest/backups/emergency_backup_*.sql.gz user@backup-server:/backups/
   ```

3. **Snapshot Redis:**
   ```bash
   redis-cli -a "YOUR_REDIS_PASSWORD" BGSAVE
   cp /var/lib/redis/dump.rdb /opt/waitingthelongest/backups/
   ```

---

## Maintenance Windows

### Planned Maintenance Procedure

1. **Announce maintenance (24-48 hours in advance)**

2. **Pre-maintenance backup:**
   ```bash
   /opt/waitingthelongest/scripts/backup_database.sh
   ```

3. **Enable maintenance mode:**
   ```bash
   # Create maintenance page
   echo "<html><body><h1>Scheduled Maintenance</h1><p>We'll be back soon!</p></body></html>" > /opt/waitingthelongest/frontend/maintenance.html

   # Update Nginx config to show maintenance page
   # Add before location / block:
   # location / {
   #     return 503;
   # }
   # error_page 503 /maintenance.html;

   sudo systemctl reload nginx
   ```

4. **Perform maintenance tasks**

5. **Test thoroughly**

6. **Disable maintenance mode:**
   ```bash
   # Restore Nginx config
   sudo systemctl reload nginx
   ```

7. **Verify site is operational**

8. **Announce completion**

### Weekly Maintenance Tasks

Run these tasks during low-traffic periods:

```bash
# Sunday 2:00 AM
0 2 * * 0 /opt/waitingthelongest/scripts/weekly_maintenance.sh
```

Create `/opt/waitingthelongest/scripts/weekly_maintenance.sh`:

```bash
#!/bin/bash
echo "=== Weekly Maintenance $(date) ===" >> /var/log/waitingthelongest/maintenance.log

# Vacuum and analyze database
sudo -u postgres psql -d waiting_the_longest -c "VACUUM ANALYZE;"

# Clear old logs
find /var/log/waitingthelongest -name "*.log.*" -mtime +14 -delete

# Clear old backups
find /opt/waitingthelongest/backups -name "*.sql.gz" -mtime +30 -delete

# Restart services for clean state
systemctl restart waitingthelongest

echo "=== Maintenance Complete ===" >> /var/log/waitingthelongest/maintenance.log
```

---

## Contact Information

### Emergency Contacts

**Primary Contact:**
- **Name:** [Your Name]
- **Role:** System Administrator
- **Email:** [your-email@example.com]
- **Phone:** [Your Phone]
- **Availability:** 24/7 for critical issues

**Secondary Contact:**
- **Name:** [Backup Admin Name]
- **Role:** Backup Administrator
- **Email:** [backup-email@example.com]
- **Phone:** [Backup Phone]
- **Availability:** Business hours

**Developer Contact:**
- **Name:** Ian Merrill
- **Email:** [developer-email@example.com]
- **GitHub:** [@ianmerrill10](https://github.com/ianmerrill10)

### Service Providers

**Hosting Provider:**
- **Provider:** IONOS
- **Account:** [Account Number]
- **Support:** [Support Phone/Email]
- **Control Panel:** [URL]

**Domain Registrar:**
- **Registrar:** [Domain Registrar Name]
- **Account:** [Account Number]
- **Support:** [Support Contact]

**SSL Certificate:**
- **Provider:** Let's Encrypt
- **Auto-renewal:** Enabled via Certbot
- **Email:** [Your Email for renewal notifications]

### External Services

**RescueGroups.org:**
- **API Key:** Stored in `.env`
- **Support:** https://rescuegroups.org/support
- **Documentation:** https://rescuegroups.org/services/adoptable-pet-data-api/

**Amazon Associates:**
- **Associate ID:** waitingthelon-20
- **Dashboard:** https://affiliate-program.amazon.com/
- **Support:** https://affiliate-program.amazon.com/help

### Monitoring Services (If Configured)

**Uptime Monitoring:**
- **Service:** [e.g., UptimeRobot]
- **Dashboard:** [URL]
- **Alerts:** [Email/SMS]

**Error Tracking:**
- **Service:** [e.g., Sentry]
- **Dashboard:** [URL]
- **API Key:** [In .env file]

**Log Aggregation:**
- **Service:** [e.g., Papertrail, Loggly]
- **Dashboard:** [URL]
- **API Key:** [In .env file]

### Important URLs

- **Production Site:** https://waitingthelongest.com
- **API Documentation:** https://waitingthelongest.com/api/docs
- **GitHub Repository:** https://github.com/ianmerrill10/WaitingTheLongest
- **Server IP:** 67.217.244.241

### Escalation Matrix

| Severity | Response Time | Who to Contact |
|----------|---------------|----------------|
| **Critical** (Site down, data loss) | 15 minutes | Primary Contact (24/7) |
| **High** (Performance issues, errors) | 1 hour | Primary Contact |
| **Medium** (Non-critical bugs) | 4 hours | Developer |
| **Low** (Feature requests, improvements) | Next business day | Developer |

### Incident Response Process

1. **Detect** - Monitoring alerts or user report
2. **Assess** - Determine severity and impact
3. **Notify** - Contact appropriate personnel
4. **Respond** - Execute emergency procedures
5. **Resolve** - Fix issue and verify
6. **Document** - Record incident and resolution
7. **Review** - Post-mortem to prevent recurrence

---

## Quick Reference Commands

### One-Liner Cheat Sheet

```bash
# Full system check
systemctl status waitingthelongest postgresql redis-server nginx && curl -s https://waitingthelongest.com/health

# Quick restart
sudo systemctl restart waitingthelongest && journalctl -u waitingthelongest -f

# Emergency backup
sudo -u postgres pg_dump waiting_the_longest | gzip > ~/emergency_$(date +%Y%m%d_%H%M%S).sql.gz

# Clear cache
redis-cli -a "PASSWORD" FLUSHALL

# View errors
journalctl -u waitingthelongest -p err -n 50

# Top processes by memory
ps aux --sort=-%mem | head -10

# Top processes by CPU
ps aux --sort=-%cpu | head -10

# Disk space
df -h | grep -E "Filesystem|/$"

# Check all logs
multitail /var/log/waitingthelongest/error.log /var/log/nginx/error.log /var/log/postgresql/postgresql-16-main.log
```

---

**Mission:** Help shelter animals who have waited the longest find forever homes.

**Remember:** When in doubt, backup first, then act!

---

## AWS App Runner Deployment (Alternative to VPS)

If running on AWS App Runner instead of IONOS VPS, use these commands:

### Health Check
```bash
# Local check (requires Python)
python scripts/health_check.py https://<your-app-runner-url>

# Or curl
curl https://<your-app-runner-url>/health
```

### API Smoke Test
```bash
python backend/tools/api_smoke_test.py --base-url https://<your-app-runner-url>
```

### View Logs
- AWS Console → App Runner → Your service → Logs
- Or use CloudWatch Logs if configured

### Redeploy
1. Build and push new image to ECR
2. In App Runner console → Deployments → Deploy

### Environment Variables
Update via App Runner console → Configuration → Environment variables:
- `SECRET_KEY`
- `DATABASE_URL`
- `CORS_ORIGINS`

See [DEPLOY_AWS_APP_RUNNER.md](DEPLOY_AWS_APP_RUNNER.md) for full setup guide.

---

*© 2025 Waiting The Longest™*
