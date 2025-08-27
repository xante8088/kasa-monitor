# Security Guide

Comprehensive security best practices and hardening guide for Kasa Monitor.

## Security Overview

```
┌─────────────────────────────────────┐
│         Security Layers             │
├─────────────────────────────────────┤
│  1. Network Security (Firewall)     │
│  2. Container Security (Docker)     │
│  3. Application Security (Auth)     │
│  4. Data Security (Encryption)      │
│  5. Access Control (RBAC)          │
│  6. Export Security (v1.2.0)       │
│  7. Session Management (v1.2.0)    │
└─────────────────────────────────────┘
```

## Recent Security Enhancements (v1.2.0 - v1.2.1)

### Critical Security Fixes Implemented (v1.2.0)
- **Data Export Security** - Permission enforcement, ownership validation, rate limiting
- **Authentication Improvements** - Token refresh, structured errors, session management
- **SSL Certificate Persistence** - Secure volume storage with auto-detection
- **Audit Logging Compliance** - GDPR/SOX compliant comprehensive logging
- **Session Security** - Concurrent session limits, fingerprinting, warnings

### Additional Security Improvements (v1.2.1)
- **Enhanced SSL Handling** - Better cross-device filesystem compatibility
- **Improved Database Security** - Fixed table reference vulnerabilities
- **API Rate Limiting** - Enhanced rate limiting for history endpoints
- **Data Aggregation Security** - Secure caching with user-based isolation
- **Docker Security** - Fixed build vulnerabilities in GitHub Actions

## Quick Security Checklist

### Essential Security ✅

- [ ] Change default admin password
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall rules
- [ ] Use strong passwords
- [ ] Regular updates
- [ ] Backup data

### Recommended Security 🛡️

- [ ] Network isolation (VLAN)
- [ ] Fail2ban configuration
- [ ] API rate limiting
- [ ] Audit logging
- [ ] Security scanning
- [ ] Intrusion detection

## Network Security

### Firewall Configuration

**UFW (Ubuntu/Debian):**
```bash
# Basic rules
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (if needed)
sudo ufw allow 22/tcp

# Allow Kasa Monitor
sudo ufw allow 3000/tcp  # Web interface
sudo ufw allow 5272/tcp  # API

# Allow from specific network only
sudo ufw allow from 192.168.1.0/24 to any port 3000
sudo ufw allow from 192.168.1.0/24 to any port 5272

# Enable firewall
sudo ufw enable
```

**iptables:**
```bash
# Drop all by default
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow localhost
iptables -A INPUT -i lo -j ACCEPT

# Allow Kasa Monitor from LAN only
iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 3000 -j ACCEPT
iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 5272 -j ACCEPT

# Save rules
iptables-save > /etc/iptables/rules.v4
```

### Network Isolation

**VLAN Configuration:**
```yaml
# Separate networks
Main Network: 192.168.1.0/24
  - Trusted devices
  - Kasa Monitor server

IoT VLAN: 192.168.10.0/24
  - Smart plugs/switches
  - Isolated from main

Management VLAN: 192.168.99.0/24
  - Admin access only
```

**Docker Network Isolation:**
```yaml
networks:
  frontend:
    internal: false
  backend:
    internal: true  # No external access
  database:
    internal: true  # No external access
```

### VPN Access

**WireGuard Setup:**
```bash
# Install WireGuard
sudo apt install wireguard

# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey

# Configure
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.0.0.1/24
PrivateKey = $(cat privatekey)
ListenPort = 51820

[Peer]
PublicKey = CLIENT_PUBLIC_KEY
AllowedIPs = 10.0.0.2/32
EOF

# Enable
sudo wg-quick up wg0
```

## Container Security

### Docker Security

**Secure Dockerfile:**
```dockerfile
# Run as non-root user
USER appuser:appuser

# Read-only filesystem
RUN chmod -R o-rwx /app

# No new privileges
SECURITY_OPT:
  - no-new-privileges:true

# Drop capabilities
CAP_DROP:
  - ALL
CAP_ADD:
  - NET_BIND_SERVICE
```

**Docker Compose Security:**
```yaml
services:
  kasa-monitor:
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
      - seccomp:default
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    user: "1001:1001"
```

### Container Scanning

**Docker Scout:**
```bash
# Scan for vulnerabilities
docker scout cves kasa-monitor:latest

# Get recommendations
docker scout recommendations kasa-monitor:latest
```

**Trivy:**
```bash
# Install Trivy
brew install aquasecurity/trivy/trivy

# Scan image
trivy image kasa-monitor:latest

# Scan with severity filter
trivy image --severity HIGH,CRITICAL kasa-monitor:latest
```

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
      pids: 200
    reservations:
      cpus: '0.5'
      memory: 512M
```

## Application Security

### CORS Configuration

**Environment-Based CORS:**
```bash
# Set allowed origins in .env file
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Production mode enforces strict origin checking
ENVIRONMENT=production
```

The application uses `security_fixes/critical/cors_fix.py` for secure CORS handling:
- Validates origins against whitelist
- Supports pattern matching for subdomains
- Blocks wildcard origins in production
- Logs CORS violations for security monitoring

### File Upload Security

**Upload Validation:**
```bash
# Configure in environment
MAX_UPLOAD_SIZE_MB=10
ALLOWED_UPLOAD_EXTENSIONS=.zip,.py,.json
REQUIRE_PLUGIN_SIGNATURES=true
```

The application uses `security_fixes/critical/file_upload_security.py`:
- File type validation (extension and MIME type)
- Size limits enforcement
- Quarantine system for suspicious files
- Virus scanning integration (when available)
- Content validation for specific file types
- Secure filename sanitization

**Quarantine System:**
- Uploaded files are first placed in quarantine
- Validation checks are performed
- Only validated files are moved to final destination
- Failed validations are logged and files deleted

### Authentication (Enhanced v1.2.0)

**Token Refresh System:**
```python
# Dual-token authentication
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Short-lived access token
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Long-lived refresh token

# Automatic token refresh before expiry
# Frontend handles refresh 5 minutes before expiration
```

**Session Management:**
```python
# Session limits and tracking
MAX_CONCURRENT_SESSIONS = 3       # Per user limit
SESSION_TIMEOUT_MINUTES = 30      # Inactivity timeout
SESSION_WARNING_MINUTES = 5       # Warning before expiry

# Session fingerprinting
SESSION_FINGERPRINT = hash(IP + User_Agent + Device_ID)
```

**Strong Password Policy:**
```python
# Requirements
MIN_LENGTH = 12
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL = True
MAX_AGE_DAYS = 90
```

**Structured Error Responses:**
```json
// New standardized 401 response format
{
  "error": "authentication_expired",
  "message": "Your session has expired. Please log in again.",
  "error_code": "TOKEN_EXPIRED",
  "timestamp": "2024-01-01T10:00:00Z",
  "redirect_to": "/login"
}
```

**Password Hashing:**
```python
# Using bcrypt (current implementation)
import bcrypt

# Hash password
password = "SecurePassword123!"
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

# Verify
bcrypt.checkpw(password.encode('utf-8'), hashed)
```

### JWT Configuration

**Secure JWT Settings:**
```python
# Strong secret key with automatic rotation support
# The system now uses jwt_secret_manager.py for secure key management
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  # Required in production

# Generate secure key:
# openssl rand -base64 32

# Short expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Algorithm
ALGORITHM = "HS256"  # Consider RS256 for production
```

**Key Rotation:**
The application now supports JWT key rotation with grace periods:
- Keys are stored securely in `data/jwt_secrets.json` with 600 permissions
- Old keys are retained for validation during rotation
- Automatic rotation can be triggered via API (admin only)

**Token Storage:**
```javascript
// Store in httpOnly cookie (more secure)
document.cookie = `token=${token}; HttpOnly; Secure; SameSite=Strict`;

// Or localStorage with XSS protection
if (window.isSecureContext) {
    localStorage.setItem('token', token);
}
```

### Session Security

```python
# Session configuration
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JS access
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_TIMEOUT = 1800  # 30 minutes
```

## HTTPS/SSL Configuration

### Using Let's Encrypt

**Certbot Setup:**
```bash
# Install Certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone \
  -d yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos
```

**Docker Compose with SSL:**
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - ./dhparam.pem:/etc/nginx/dhparam.pem:ro
```

**Nginx Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Other security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### Self-Signed Certificate

```bash
# Generate self-signed cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /app/ssl/private.key \
  -out /app/ssl/certificate.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate DH params
openssl dhparam -out /app/ssl/dhparam.pem 2048
```

## Access Control

### Role-Based Access Control (RBAC)

**Role Definitions:**
```python
ROLES = {
    'admin': [
        'devices.*',
        'users.*',
        'system.*',
        'rates.*'
    ],
    'operator': [
        'devices.view',
        'devices.control',
        'devices.edit',
        'rates.view'
    ],
    'viewer': [
        'devices.view',
        'rates.view',
        'costs.view'
    ],
    'guest': [
        'devices.view'
    ]
}
```

### API Security (Enhanced v1.2.0)

**Data Export Security:**
```python
# Permission-based access control
@require_permission(Permission.DATA_EXPORT)
async def export_data(user: User = Depends(get_current_user)):
    # User ownership validation
    if user.role != "admin" and export.user_id != user.id:
        raise HTTPException(403, "Access denied")
    
    # Rate limiting: 10 exports per hour
    if get_export_count(user.id, last_hour=True) >= 10:
        raise HTTPException(429, "Export rate limit exceeded")
    
    # Comprehensive audit logging
    log_audit_event(
        event_type=AuditEventType.DATA_EXPORT,
        user_id=user.id,
        details={"devices": devices, "format": format}
    )
```

**Rate Limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute", "1000 per hour"]
)

# Endpoint-specific limits
@app.get("/api/devices")
@limiter.limit("10 per minute")
async def get_devices():
    pass

# Export-specific limits
@app.post("/api/exports/create")
@limiter.limit("10 per hour")  # Export rate limit
async def create_export():
    pass
```

**API Key Authentication:**
```python
API_KEY_HEADER = "X-API-Key"

async def verify_api_key(api_key: str = Header(...)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403)
    return api_key
```

## Data Security

### Database Encryption

**SQLite Encryption:**
```python
# Using SQLCipher
import sqlcipher3

conn = sqlcipher3.connect('/app/data/kasa_monitor.db')
conn.execute("PRAGMA key = 'your-encryption-key'")
```

**Backup Encryption:**
```bash
# Encrypt backup
openssl enc -aes-256-cbc -salt \
  -in backup.sql \
  -out backup.sql.enc \
  -k "encryption-password"

# Decrypt backup
openssl enc -aes-256-cbc -d \
  -in backup.sql.enc \
  -out backup.sql \
  -k "encryption-password"
```

### Sensitive Data Handling

**Environment Variables:**
```bash
# Never commit .env files
echo ".env" >> .gitignore

# Required security variables for production
JWT_SECRET_KEY=$(openssl rand -base64 32)
DOCKER_INFLUXDB_INIT_PASSWORD=$(openssl rand -base64 24)
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=$(openssl rand -hex 32)

# Use Docker secrets
docker secret create jwt_secret jwt_secret.txt
docker secret create db_password password.txt

# Or use encrypted config
ansible-vault encrypt config.yml
```

**Database Credentials:**
- InfluxDB credentials now use environment variables
- No hardcoded passwords in docker-compose.yml
- Passwords are loaded from .env files
- Production deployments should use Docker secrets or external secret management

**Secrets Management:**
```yaml
# docker-compose with secrets
secrets:
  db_password:
    external: true
  jwt_secret:
    external: true

services:
  app:
    secrets:
      - db_password
      - jwt_secret
```

## Monitoring & Auditing (Enhanced v1.2.0)

### Comprehensive Audit Logging

**GDPR/SOX Compliant Logging:**
```python
from enum import Enum
from datetime import datetime

class AuditEventType(Enum):
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    SESSION_EXPIRED = "session_expired"
    
    # Data export events
    DATA_EXPORT = "data_export"
    DATA_EXPORTED = "data_exported"
    DATA_DELETED = "data_deleted"
    EXPORT_DOWNLOADED = "export_downloaded"
    
    # Security events
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

class AuditLogger:
    def log_event(self, event_type: AuditEventType, user_id: int, 
                  severity: str, details: dict):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type.value,
            'user_id': user_id,
            'severity': severity,  # INFO, WARNING, ERROR, CRITICAL
            'details': details,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'session_id': session.get('session_id'),
            'checksum': self.calculate_checksum()  # Tamper-evident
        }
        
        # Store in database for compliance
        db.audit_logs.insert(log_entry)
        
        # Also write to file for backup
        logging.info(f"AUDIT: {json.dumps(log_entry)}")
```

**Export Activity Tracking:**
```python
# All export operations are logged
await log_audit_event(
    event_type=AuditEventType.DATA_EXPORT,
    user_id=user.id,
    severity="INFO",
    details={
        "export_id": export_id,
        "devices": devices,
        "date_range": date_range,
        "format": format,
        "records_count": count,
        "file_size": size
    }
)
```

### Intrusion Detection

**Fail2ban Configuration:**
```ini
# /etc/fail2ban/jail.local
[kasa-monitor]
enabled = true
port = 3000,5272
filter = kasa-monitor
logpath = /var/log/kasa-monitor/access.log
maxretry = 5
bantime = 3600

# /etc/fail2ban/filter.d/kasa-monitor.conf
[Definition]
failregex = ^<HOST> .* "POST /api/auth/login" 401
ignoreregex =
```

### Security Monitoring

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Histogram

auth_attempts = Counter('auth_attempts_total', 'Total auth attempts')
auth_failures = Counter('auth_failures_total', 'Failed auth attempts')
api_latency = Histogram('api_latency_seconds', 'API latency')
```

## Security Hardening Checklist

### Initial Setup
- [ ] Change default passwords
- [ ] Create non-admin users
- [ ] Configure firewall
- [ ] Enable HTTPS
- [ ] Set up backups

### Ongoing Security
- [ ] Regular updates
- [ ] Security scanning
- [ ] Log monitoring
- [ ] Access reviews
- [ ] Penetration testing

### Incident Response
- [ ] Incident plan documented
- [ ] Backup restoration tested
- [ ] Contact list updated
- [ ] Recovery procedures ready

## Vulnerability Management

### Regular Scanning

```bash
#!/bin/bash
# Weekly security scan script

# Update dependencies
npm audit fix
pip-audit --fix

# Scan Docker images
docker scout cves kasa-monitor:latest

# Check for exposed secrets
trufflehog filesystem /app

# Port scan
nmap -sV localhost
```

### Update Schedule

- **Critical**: Within 24 hours
- **High**: Within 7 days
- **Medium**: Within 30 days
- **Low**: Next maintenance window

## Reporting Security Issues

### Responsible Disclosure

If you discover a security vulnerability:

1. **DO NOT** create public issue
2. Email: security@[project-domain]
3. Include:
   - Description
   - Steps to reproduce
   - Impact assessment
   - Suggested fix

### Security Response

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix timeline**: Based on severity
- **Disclosure**: After patch released

## Compliance (Enhanced v1.2.0)

### Standards

- OWASP Top 10
- CIS Docker Benchmark
- NIST Cybersecurity Framework
- ISO 27001 principles
- **GDPR Article 30** - Records of processing activities
- **SOX Section 404** - Internal control assessment

### Privacy & Data Protection

**GDPR Compliance:**
- Right to data portability (export personal data)
- Comprehensive audit trail of all data access
- User consent tracking and management
- Data anonymization options in exports
- Retention policies with automatic deletion
- User ownership validation on all exports

**SOX Compliance:**
- Tamper-evident audit logging with checksums
- Complete user identity tracking
- Data access authorization controls
- Change management documentation
- Segregation of duties (role-based access)
- Regular compliance reporting

### Data Export Compliance

```python
# GDPR-compliant export with audit trail
@require_permission(Permission.DATA_EXPORT)
async def export_user_data(user_id: int):
    # Log data access for GDPR Article 30
    await log_audit_event(
        event_type=AuditEventType.DATA_EXPORT,
        user_id=user_id,
        severity="INFO",
        details={
            "purpose": "User data portability request",
            "lawful_basis": "User consent",
            "data_categories": ["device_data", "energy_usage"],
            "retention_days": 7
        }
    )
    
    # Export with privacy options
    return export_with_privacy_options(
        user_id=user_id,
        anonymize_ip=True,
        exclude_sensitive=True
    )
```

## Related Pages

- [Installation](Installation) - Secure installation
- [Docker Deployment](Docker-Deployment) - Container security
- [User Management](User-Management) - Access control
- [Backup & Recovery](Backup-Recovery) - Data protection

## Resources

- [OWASP Security Guide](https://owasp.org)
- [Docker Security](https://docs.docker.com/security/)
- [NIST Cybersecurity](https://www.nist.gov/cybersecurity)
- [CIS Benchmarks](https://www.cisecurity.org)

---

**Document Version:** 2.1.0  
**Last Updated:** 2025-08-27  
**Review Status:** Current  
**Change Summary:** Updated for v1.2.1 with additional security improvements including enhanced SSL handling, database security fixes, and improved API rate limiting