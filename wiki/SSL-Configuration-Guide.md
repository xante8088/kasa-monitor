# SSL Configuration Guide

Complete guide for configuring and managing SSL certificates in Kasa Monitor with persistent storage support.

## Overview

Kasa Monitor now includes enhanced SSL certificate management with Docker volume persistence, ensuring certificates remain intact across container updates and restarts.

```
┌─────────────────────────────────────┐
│      SSL Certificate System         │
├─────────────────────────────────────┤
│  1. Certificate Upload & Validation │
│  2. Persistent Volume Storage       │
│  3. Auto-Detection & Loading        │
│  4. Database Path Storage           │
│  5. UI Configuration Management     │
└─────────────────────────────────────┘
```

## New Features (v1.2.0)

### SSL Certificate Persistence
- **Docker Volume Support** - Certificates persist across container restarts
- **Cross-Device Link Fix** - Resolved Docker filesystem compatibility issues
- **Database Path Storage** - Certificate paths saved for automatic loading
- **Auto-Detection** - Automatically loads certificates on startup
- **UI Integration** - Configure SSL directly from the admin interface

## Quick Start

### Docker Compose Configuration

**Enable SSL with Persistent Storage:**
```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    ports:
      - "443:443"     # HTTPS port
      - "80:3000"     # HTTP redirect to HTTPS
      - "5272:5272"   # API port
    volumes:
      - kasa_data:/app/data
      - kasa_ssl:/app/ssl    # Persistent SSL volume
    environment:
      - SSL_ENABLED=true
      - SSL_CERT_PATH=/app/ssl/certificate.crt
      - SSL_KEY_PATH=/app/ssl/private.key
      - SSL_REDIRECT_HTTP=true
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}

volumes:
  kasa_data:
  kasa_ssl:    # Define SSL volume
```

## Certificate Installation

### Method 1: UI Upload (Recommended)

1. **Access Admin Panel:**
   ```
   https://your-domain/admin/system
   ```

2. **Navigate to SSL Configuration:**
   - Click on "SSL/TLS Settings"
   - Select "Upload Certificates"

3. **Upload Certificate Files:**
   - Certificate file (`.crt`, `.pem`)
   - Private key file (`.key`)
   - Optional: Certificate chain file

4. **Apply Configuration:**
   - Click "Save and Apply"
   - Service will automatically restart with SSL enabled

### Method 2: Docker Volume Mount

1. **Prepare Certificate Files:**
   ```bash
   # Create local SSL directory
   mkdir -p ./ssl
   
   # Copy certificates
   cp /path/to/certificate.crt ./ssl/
   cp /path/to/private.key ./ssl/
   
   # Set proper permissions
   chmod 644 ./ssl/certificate.crt
   chmod 600 ./ssl/private.key
   ```

2. **Mount in Docker Compose:**
   ```yaml
   volumes:
     - ./ssl:/app/ssl:ro
   ```

### Method 3: API Upload

```bash
# Upload certificate via API
curl -X POST https://localhost:5272/api/ssl/upload \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "certificate=@/path/to/certificate.crt" \
  -F "private_key=@/path/to/private.key"
```

## Certificate Types

### Let's Encrypt (Production)

**Automatic Certificate with Certbot:**
```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone \
  -d your-domain.com \
  --email admin@your-domain.com \
  --agree-tos

# Certificates will be in:
# /etc/letsencrypt/live/your-domain.com/
```

**Docker Compose with Let's Encrypt:**
```yaml
services:
  kasa-monitor:
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - kasa_ssl:/app/ssl
    environment:
      - SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
      - SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
```

### Self-Signed Certificate (Development)

**Generate Self-Signed Certificate:**
```bash
# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout private.key \
  -out certificate.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# For local development with multiple domains
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout private.key \
  -out certificate.crt \
  -subj "/CN=localhost" \
  -addext "subjectAltName = DNS:localhost,DNS:*.local,IP:127.0.0.1,IP:192.168.1.100"
```

### Commercial SSL Certificate

**Prepare Commercial Certificate:**
```bash
# Generate CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout private.key \
  -out request.csr

# Submit CSR to Certificate Authority
# Download certificate files

# Combine certificates if needed
cat your_domain.crt intermediate.crt root.crt > fullchain.pem
```

## Persistence Configuration

### Docker Volume Persistence

The SSL system now uses Docker volumes to ensure certificates persist across container updates:

**Key Changes in docker-compose.yml:**
```yaml
volumes:
  kasa_ssl:  # Named volume for SSL persistence
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${PWD}/ssl  # Optional: bind to local directory
```

**Benefits:**
- Certificates survive container recreation
- No data loss during updates
- Atomic file operations (no cross-device link errors)
- Backup-friendly volume management

### Database Path Storage

Certificate paths are now stored in the database for automatic loading:

```sql
-- SSL configuration table
CREATE TABLE ssl_config (
    id INTEGER PRIMARY KEY,
    cert_path TEXT,
    key_path TEXT,
    chain_path TEXT,
    enabled BOOLEAN DEFAULT false,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fingerprint TEXT
);
```

## SSL Configuration Options

### Environment Variables

```bash
# Basic SSL Configuration
SSL_ENABLED=true                    # Enable SSL
SSL_CERT_PATH=/app/ssl/cert.crt    # Certificate file path
SSL_KEY_PATH=/app/ssl/private.key   # Private key path
SSL_CHAIN_PATH=/app/ssl/chain.crt   # Certificate chain (optional)

# SSL Behavior
SSL_REDIRECT_HTTP=true      # Redirect HTTP to HTTPS
SSL_STRICT_MODE=true        # Enforce strict SSL/TLS
SSL_PORT=443                # HTTPS port
HTTP_PORT=80                # HTTP port (for redirect)

# Security Headers
SSL_HSTS_ENABLED=true                    # Enable HSTS
SSL_HSTS_MAX_AGE=31536000               # HSTS max age (1 year)
SSL_HSTS_INCLUDE_SUBDOMAINS=true        # Include subdomains
SSL_HSTS_PRELOAD=false                  # HSTS preload (careful!)

# TLS Configuration
SSL_MIN_VERSION=TLSv1.2     # Minimum TLS version
SSL_CIPHERS=HIGH:!aNULL:!MD5 # Cipher suite
```

### Nginx Reverse Proxy

**nginx.conf with SSL:**
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # Certificate files
    ssl_certificate /app/ssl/fullchain.pem;
    ssl_certificate_key /app/ssl/private.key;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # SSL session caching
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://kasa-monitor:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Troubleshooting SSL Issues

### Certificate Not Loading

**Check certificate paths:**
```bash
# Verify files exist in container
docker exec kasa-monitor ls -la /app/ssl/

# Check permissions
docker exec kasa-monitor stat /app/ssl/certificate.crt
docker exec kasa-monitor stat /app/ssl/private.key

# View SSL configuration in database
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "SELECT * FROM ssl_config;"
```

### Cross-Device Link Error (Fixed in v1.2.0)

**Previous Issue:**
```
OSError: [Errno 18] Invalid cross-device link
```

**Solution Implemented:**
- Uses `shutil.move()` instead of `os.rename()`
- Properly handles Docker volume boundaries
- Atomic operations within same filesystem

### Certificate Validation Errors

**Verify certificate:**
```bash
# Check certificate details
openssl x509 -in certificate.crt -text -noout

# Verify certificate and key match
openssl x509 -noout -modulus -in certificate.crt | openssl md5
openssl rsa -noout -modulus -in private.key | openssl md5

# Test SSL connection
openssl s_client -connect localhost:443 -servername your-domain.com
```

### Permission Issues

**Fix certificate permissions:**
```bash
# In Docker volume
docker exec kasa-monitor sh -c "
  chown app:app /app/ssl/*
  chmod 644 /app/ssl/*.crt
  chmod 600 /app/ssl/*.key
"
```

## SSL Security Best Practices

### Certificate Management

1. **Use Strong Keys:**
   - Minimum 2048-bit RSA keys
   - Consider ECDSA for better performance

2. **Regular Renewal:**
   - Set up automatic renewal for Let's Encrypt
   - Monitor expiration dates
   - Test renewal process

3. **Secure Storage:**
   - Use Docker secrets for production
   - Restrict file permissions (600 for keys)
   - Never commit certificates to Git

### Configuration Hardening

```yaml
# Production SSL configuration
environment:
  - SSL_ENABLED=true
  - SSL_STRICT_MODE=true
  - SSL_MIN_VERSION=TLSv1.2
  - SSL_CIPHERS=ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
  - SSL_HSTS_ENABLED=true
  - SSL_HSTS_MAX_AGE=63072000  # 2 years
  - SSL_HSTS_INCLUDE_SUBDOMAINS=true
```

### Monitoring & Alerts

```bash
#!/bin/bash
# Certificate expiration check
CERT_FILE="/app/ssl/certificate.crt"
DAYS_WARNING=30

EXPIRY_DATE=$(openssl x509 -in $CERT_FILE -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
    echo "WARNING: Certificate expires in $DAYS_LEFT days"
    # Send alert notification
fi
```

## API Endpoints

### Upload SSL Certificate

```http
POST /api/ssl/upload
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

certificate: (binary)
private_key: (binary)
chain: (binary, optional)
```

### Get SSL Status

```http
GET /api/ssl/status
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "ssl_enabled": true,
  "certificate": {
    "subject": "CN=your-domain.com",
    "issuer": "CN=Let's Encrypt Authority X3",
    "valid_from": "2024-01-01T00:00:00Z",
    "valid_to": "2024-04-01T00:00:00Z",
    "fingerprint": "SHA256:abc123...",
    "days_remaining": 45
  },
  "paths": {
    "certificate": "/app/ssl/certificate.crt",
    "private_key": "/app/ssl/private.key",
    "chain": "/app/ssl/chain.crt"
  },
  "persistence": {
    "volume_mounted": true,
    "database_stored": true,
    "auto_load_enabled": true
  }
}
```

### Enable/Disable SSL

```http
POST /api/ssl/toggle
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "enabled": true
}
```

## Migration from Previous Versions

### Upgrading from Pre-v1.2.0

1. **Backup existing certificates:**
   ```bash
   docker cp kasa-monitor:/app/ssl ./ssl-backup
   ```

2. **Update docker-compose.yml:**
   - Add SSL volume definition
   - Mount volume to /app/ssl

3. **Restart with new configuration:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Restore certificates:**
   ```bash
   docker cp ./ssl-backup/. kasa-monitor:/app/ssl/
   ```

## Related Documentation

- [Security Guide](Security-Guide) - Overall security configuration
- [Docker Deployment](Docker-Deployment) - Docker setup and configuration
- [Installation](Installation) - Initial setup guide
- [System Configuration](System-Configuration) - System-wide settings

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-26  
**Review Status:** Current  
**Change Summary:** Initial documentation for SSL persistence features in v1.2.0