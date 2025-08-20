# Backup & Recovery

Comprehensive guide for backing up and restoring your Kasa Monitor data.

## Backup Strategy Overview

```
┌─────────────────────────────────────┐
│        Backup Components            │
├─────────────────────────────────────┤
│  1. Database (SQLite)               │
│  2. Configuration Files             │
│  3. Docker Volumes                  │
│  4. InfluxDB Data (if used)        │
│  5. User Settings                   │
└─────────────────────────────────────┘
```

## Quick Backup

### One-Command Backup

```bash
#!/bin/bash
# Quick backup script

BACKUP_NAME="kasa-backup-$(date +%Y%m%d-%H%M%S)"

# Create backup
docker run --rm \
  -v kasa_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/$BACKUP_NAME.tar.gz -C /data .

echo "Backup created: $BACKUP_NAME.tar.gz"
```

### Docker Volume Backup

```bash
# Backup all volumes
docker run --rm \
  -v kasa_data:/source/data \
  -v kasa_logs:/source/logs \
  -v $(pwd)/backups:/backup \
  alpine sh -c "cd /source && tar czf /backup/kasa-volumes-$(date +%Y%m%d).tar.gz ."
```

## Comprehensive Backup

### Full Backup Script

```bash
#!/bin/bash
# comprehensive-backup.sh

set -e

# Configuration
BACKUP_DIR="/backups/kasa-monitor"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"
CONTAINER="kasa-monitor"

# Create backup directory
mkdir -p $BACKUP_PATH

echo "Starting Kasa Monitor backup..."

# 1. Stop writes (optional for consistency)
docker exec $CONTAINER sqlite3 /app/data/kasa_monitor.db "PRAGMA wal_checkpoint(TRUNCATE);"

# 2. Backup SQLite database
echo "Backing up database..."
docker exec $CONTAINER sqlite3 /app/data/kasa_monitor.db ".backup /tmp/backup.db"
docker cp $CONTAINER:/tmp/backup.db $BACKUP_PATH/database.db

# 3. Backup configuration
echo "Backing up configuration..."
docker exec $CONTAINER tar czf /tmp/config.tar.gz -C /app config/
docker cp $CONTAINER:/tmp/config.tar.gz $BACKUP_PATH/config.tar.gz

# 4. Backup Docker volumes
echo "Backing up volumes..."
docker run --rm \
  -v kasa_data:/data \
  -v $BACKUP_PATH:/backup \
  alpine tar czf /backup/volumes.tar.gz -C /data .

# 5. Export Docker compose and env
echo "Backing up Docker configuration..."
cp docker-compose.yml $BACKUP_PATH/
cp .env $BACKUP_PATH/ 2>/dev/null || true

# 6. Create metadata
echo "Creating metadata..."
cat > $BACKUP_PATH/metadata.json << EOF
{
  "timestamp": "$TIMESTAMP",
  "version": "$(docker exec $CONTAINER cat /app/version.json | jq -r .version)",
  "container": "$CONTAINER",
  "host": "$(hostname)",
  "docker_version": "$(docker --version)",
  "size": "$(du -sh $BACKUP_PATH | cut -f1)"
}
EOF

# 7. Create archive
echo "Creating archive..."
cd $BACKUP_DIR
tar czf kasa-backup-$TIMESTAMP.tar.gz $TIMESTAMP/
rm -rf $TIMESTAMP

# 8. Verify backup
echo "Verifying backup..."
tar tzf kasa-backup-$TIMESTAMP.tar.gz > /dev/null

echo "✅ Backup complete: $BACKUP_DIR/kasa-backup-$TIMESTAMP.tar.gz"
echo "Size: $(du -h kasa-backup-$TIMESTAMP.tar.gz | cut -f1)"

# 9. Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "kasa-backup-*.tar.gz" -mtime +30 -delete
```

### Database-Only Backup

```bash
# SQLite backup
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  ".backup /app/data/backup-$(date +%Y%m%d).db"

# SQL dump
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db .dump \
  > backup-$(date +%Y%m%d).sql

# With compression
docker exec kasa-monitor sh -c \
  "sqlite3 /app/data/kasa_monitor.db .dump | gzip > /tmp/backup.sql.gz"
docker cp kasa-monitor:/tmp/backup.sql.gz ./
```

### InfluxDB Backup

```bash
# Backup InfluxDB
docker exec kasa-influxdb influx backup \
  /tmp/influx-backup \
  -t $INFLUX_TOKEN

# Copy to host
docker cp kasa-influxdb:/tmp/influx-backup ./influx-backup-$(date +%Y%m%d)

# Backup specific bucket
docker exec kasa-influxdb influx backup \
  /tmp/influx-backup \
  --bucket device-data \
  -t $INFLUX_TOKEN
```

## Automated Backups

### Cron Job Setup

```bash
# Edit crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /opt/kasa-monitor/scripts/backup.sh >> /var/log/kasa-backup.log 2>&1

# Weekly full backup on Sunday
0 3 * * 0 /opt/kasa-monitor/scripts/full-backup.sh >> /var/log/kasa-backup.log 2>&1

# Monthly archive on 1st
0 4 1 * * /opt/kasa-monitor/scripts/archive-backup.sh >> /var/log/kasa-backup.log 2>&1
```

### Docker-Based Scheduler

```yaml
# docker-compose.yml addition
services:
  backup:
    image: alpine:latest
    container_name: kasa-backup
    volumes:
      - kasa_data:/data:ro
      - ./backups:/backups
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - BACKUP_SCHEDULE=0 2 * * *
    command: |
      sh -c "
        apk add --no-cache docker-cli
        while true; do
          sleep 86400
          tar czf /backups/backup-$$(date +%Y%m%d).tar.gz -C /data .
        done
      "
```

### Backup to Cloud

**AWS S3:**
```bash
#!/bin/bash
# backup-to-s3.sh

# Create local backup
./comprehensive-backup.sh

# Upload to S3
aws s3 cp \
  kasa-backup-$(date +%Y%m%d).tar.gz \
  s3://your-bucket/kasa-monitor/backups/ \
  --storage-class GLACIER

# Verify upload
aws s3 ls s3://your-bucket/kasa-monitor/backups/
```

**Google Cloud Storage:**
```bash
# Upload to GCS
gsutil cp kasa-backup-*.tar.gz gs://your-bucket/kasa-monitor/backups/

# Set lifecycle policy
gsutil lifecycle set lifecycle.json gs://your-bucket
```

**Backblaze B2:**
```bash
# Upload to B2
b2 upload-file \
  your-bucket \
  kasa-backup-$(date +%Y%m%d).tar.gz \
  kasa-monitor/backups/
```

## Recovery Procedures

### Quick Restore

```bash
#!/bin/bash
# quick-restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./quick-restore.sh backup-file.tar.gz"
  exit 1
fi

# Stop container
docker-compose down

# Extract backup
docker run --rm \
  -v kasa_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/$BACKUP_FILE"

# Start container
docker-compose up -d

echo "✅ Restore complete"
```

### Full Recovery

```bash
#!/bin/bash
# full-restore.sh

set -e

BACKUP_FILE=$1
RESTORE_DIR="/tmp/kasa-restore"

echo "Starting Kasa Monitor recovery..."

# 1. Extract backup
echo "Extracting backup..."
mkdir -p $RESTORE_DIR
tar xzf $BACKUP_FILE -C $RESTORE_DIR

# 2. Stop existing container
echo "Stopping container..."
docker-compose down

# 3. Remove old volumes
echo "Removing old data..."
docker volume rm kasa_data kasa_logs 2>/dev/null || true

# 4. Recreate volumes
echo "Creating new volumes..."
docker volume create kasa_data
docker volume create kasa_logs

# 5. Restore database
echo "Restoring database..."
docker run --rm \
  -v kasa_data:/data \
  -v $RESTORE_DIR:/restore \
  alpine cp -r /restore/*/volumes/* /data/

# 6. Restore configuration
echo "Restoring configuration..."
cp $RESTORE_DIR/*/docker-compose.yml ./
cp $RESTORE_DIR/*/.env ./ 2>/dev/null || true

# 7. Start services
echo "Starting services..."
docker-compose up -d

# 8. Verify
echo "Verifying restore..."
sleep 10
curl -f http://localhost:3000 || echo "Warning: Service not yet ready"

# 9. Cleanup
rm -rf $RESTORE_DIR

echo "✅ Recovery complete"
```

### Database Recovery

```bash
# From SQL dump
docker exec -i kasa-monitor sqlite3 /app/data/kasa_monitor.db < backup.sql

# From .db file
docker cp backup.db kasa-monitor:/app/data/kasa_monitor.db
docker restart kasa-monitor

# Repair corrupted database
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db "PRAGMA integrity_check;"
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db ".recover" | \
  sqlite3 /app/data/recovered.db
```

### InfluxDB Recovery

```bash
# Restore InfluxDB
docker cp influx-backup kasa-influxdb:/tmp/
docker exec kasa-influxdb influx restore \
  /tmp/influx-backup \
  -t $INFLUX_TOKEN

# Restore specific bucket
docker exec kasa-influxdb influx restore \
  /tmp/influx-backup \
  --bucket device-data \
  -t $INFLUX_TOKEN
```

## Disaster Recovery

### Disaster Recovery Plan

```yaml
# disaster-recovery-plan.yml
recovery_objectives:
  rpo: 24 hours  # Recovery Point Objective
  rto: 1 hour    # Recovery Time Objective

backup_locations:
  primary: /backups/kasa-monitor
  secondary: s3://backup-bucket/kasa-monitor
  tertiary: offsite-nas:/backups

recovery_steps:
  1: Assess damage and data loss
  2: Identify latest valid backup
  3: Provision new infrastructure
  4: Restore from backup
  5: Verify data integrity
  6: Test functionality
  7: Resume operations
```

### Emergency Recovery Script

```bash
#!/bin/bash
# emergency-recovery.sh

echo "🚨 EMERGENCY RECOVERY INITIATED"

# Find latest backup
LATEST_BACKUP=$(ls -t /backups/kasa-backup-*.tar.gz | head -1)

if [ -z "$LATEST_BACKUP" ]; then
  echo "❌ No backup found!"
  # Try cloud backup
  aws s3 cp s3://backup-bucket/kasa-monitor/latest.tar.gz ./
  LATEST_BACKUP="./latest.tar.gz"
fi

echo "Using backup: $LATEST_BACKUP"

# Fresh install
docker pull xante8088/kasa-monitor:latest

# Restore
./full-restore.sh $LATEST_BACKUP

# Verify
if curl -f http://localhost:3000/health; then
  echo "✅ Recovery successful"
else
  echo "❌ Recovery failed - manual intervention required"
  exit 1
fi
```

## Backup Validation

### Validation Script

```bash
#!/bin/bash
# validate-backup.sh

BACKUP_FILE=$1
TEMP_DIR="/tmp/backup-test"

echo "Validating backup: $BACKUP_FILE"

# 1. Check file exists
if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Backup file not found"
  exit 1
fi

# 2. Test extraction
mkdir -p $TEMP_DIR
if ! tar tzf $BACKUP_FILE > /dev/null 2>&1; then
  echo "❌ Backup file corrupted"
  exit 1
fi

# 3. Extract and verify
tar xzf $BACKUP_FILE -C $TEMP_DIR

# 4. Check database
if [ -f "$TEMP_DIR/*/database.db" ]; then
  sqlite3 $TEMP_DIR/*/database.db "PRAGMA integrity_check;" > /dev/null
  if [ $? -eq 0 ]; then
    echo "✅ Database valid"
  else
    echo "❌ Database corrupted"
    exit 1
  fi
fi

# 5. Check size
SIZE=$(du -sh $BACKUP_FILE | cut -f1)
echo "Backup size: $SIZE"

# 6. Cleanup
rm -rf $TEMP_DIR

echo "✅ Backup validation passed"
```

### Restore Testing

```bash
# Test restore in isolated environment
docker-compose -f docker-compose.test.yml up -d
./restore.sh test-backup.tar.gz
docker-compose -f docker-compose.test.yml down
```

## Backup Best Practices

### 3-2-1 Rule

- **3** copies of important data
- **2** different storage media
- **1** offsite backup

```bash
# Implementation
LOCAL="/backups/kasa-monitor"      # Copy 1
NAS="nas:/volume1/backups"         # Copy 2
CLOUD="s3://backup-bucket"         # Copy 3 (offsite)
```

### Retention Policy

```bash
# Retention schedule
Daily backups:   Keep 7 days
Weekly backups:  Keep 4 weeks
Monthly backups: Keep 12 months
Yearly backups:  Keep 5 years

# Implementation
find /backups -name "daily-*.tar.gz" -mtime +7 -delete
find /backups -name "weekly-*.tar.gz" -mtime +28 -delete
find /backups -name "monthly-*.tar.gz" -mtime +365 -delete
```

### Encryption

```bash
# Encrypt backup
openssl enc -aes-256-cbc -salt \
  -in backup.tar.gz \
  -out backup.tar.gz.enc \
  -k "your-encryption-password"

# Decrypt backup
openssl enc -aes-256-cbc -d \
  -in backup.tar.gz.enc \
  -out backup.tar.gz \
  -k "your-encryption-password"

# Using GPG
gpg --encrypt --recipient admin@example.com backup.tar.gz
gpg --decrypt backup.tar.gz.gpg > backup.tar.gz
```

## Monitoring Backups

### Backup Health Check

```bash
#!/bin/bash
# check-backups.sh

# Check latest backup age
LATEST=$(ls -t /backups/kasa-backup-*.tar.gz | head -1)
AGE=$((($(date +%s) - $(stat -f %m "$LATEST")) / 3600))

if [ $AGE -gt 25 ]; then
  echo "⚠️ WARNING: Latest backup is $AGE hours old"
  # Send alert
  curl -X POST https://hooks.slack.com/services/xxx \
    -d '{"text":"Kasa Monitor backup is overdue!"}'
fi

# Check backup size
SIZE=$(stat -f %z "$LATEST")
if [ $SIZE -lt 1000000 ]; then
  echo "⚠️ WARNING: Backup suspiciously small"
fi
```

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Backup Status",
      "targets": [{
        "expr": "time() - backup_last_success_timestamp"
      }]
    },
    {
      "title": "Backup Size Trend",
      "targets": [{
        "expr": "backup_size_bytes"
      }]
    }
  ]
}
```

## Troubleshooting

### Common Issues

**Backup fails with "Permission denied"**
```bash
# Fix permissions
docker exec -u root kasa-monitor chown -R appuser:appuser /app/data
```

**Restore fails with "Database locked"**
```bash
# Stop all connections
docker-compose down
docker-compose up -d
```

**Backup too large**
```bash
# Compress more aggressively
tar czf - /data | xz -9 > backup.tar.xz

# Exclude unnecessary files
tar czf backup.tar.gz \
  --exclude='*.log' \
  --exclude='*.tmp' \
  /data
```

## Related Pages

- [Database Schema](Database-Schema) - Understanding data structure
- [Docker Deployment](Docker-Deployment) - Container management
- [Security Guide](Security-Guide) - Securing backups
- [System Configuration](System-Configuration) - Backup settings

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added