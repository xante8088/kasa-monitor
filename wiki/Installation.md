# Installation Guide

This guide covers all installation methods for Kasa Monitor.

## Table of Contents
- [Requirements](#requirements)
- [Docker Installation](#docker-installation)
- [Manual Installation](#manual-installation)
- [Raspberry Pi Setup](#raspberry-pi-setup)
- [Post-Installation](#post-installation)

## Requirements

### System Requirements
- **OS**: Linux, macOS, Windows (via Docker)
- **RAM**: Minimum 512MB, recommended 2GB
- **Storage**: 500MB for application + space for data
- **Network**: Same network as Kasa devices

### Software Requirements
- **Docker**: Version 20.10+ (for Docker installation)
- **Node.js**: Version 18+ (for manual installation)
- **Python**: Version 3.11+ (for manual installation)

## Docker Installation

### Quick Start (Recommended)

```bash
# Pull and run with default settings (bridge network)
docker run -d \
  --name kasa-monitor \
  -p 3000:3000 \
  -p 5272:5272 \
  -v kasa_data:/app/data \
  xante8088/kasa-monitor:latest
```

Access at: `http://localhost:3000`

### Docker Compose with SSL Persistence (v1.2.0)

```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    ports:
      - "443:443"      # HTTPS
      - "80:3000"      # HTTP (redirects to HTTPS)
      - "5272:5272"    # API
    volumes:
      - kasa_data:/app/data
      - kasa_ssl:/app/ssl      # SSL certificate persistence
    environment:
      - SSL_ENABLED=true
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}  # Required for production
      - ENVIRONMENT=production

volumes:
  kasa_data:
  kasa_ssl:  # Persistent SSL storage
```

### Docker Compose Options

#### Option 1: Bridge Network (Most Secure)
```bash
# Download compose file
curl -O https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.yml

# Start the application
docker-compose up -d
```

**Note**: Device discovery won't work. Use [manual device entry](Device-Management#manual-entry).

#### Option 2: Host Network (Best Discovery)
```bash
# Download host network compose
curl -O https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.host.yml

# Run with host network
docker-compose -f docker-compose.host.yml up -d
```

**Note**: Linux only. Full device discovery enabled.

#### Option 3: Macvlan Network (Advanced)
```bash
# Download macvlan compose
curl -O https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.macvlan.yml

# Edit network settings
nano docker-compose.macvlan.yml
# Update: parent interface, subnet, gateway

# Run with macvlan
docker-compose -f docker-compose.macvlan.yml up -d
```

See [Network Configuration](Network-Configuration) for detailed setup.

### Environment Variables

```yaml
environment:
  # Security (REQUIRED FOR PRODUCTION)
  - JWT_SECRET_KEY=CHANGE_ME_TO_SECURE_256_BIT_KEY  # Generate with: openssl rand -base64 32
  - ENVIRONMENT=production  # Enable strict security
  
  # Authentication & Sessions (v1.2.0)
  - ACCESS_TOKEN_EXPIRE_MINUTES=30
  - REFRESH_TOKEN_EXPIRE_DAYS=7
  - MAX_CONCURRENT_SESSIONS=3
  - SESSION_TIMEOUT_MINUTES=30
  - SESSION_WARNING_MINUTES=5
  
  # SSL Configuration (v1.2.0)
  - SSL_ENABLED=true
  - SSL_CERT_PATH=/app/ssl/certificate.crt
  - SSL_KEY_PATH=/app/ssl/private.key
  - SSL_REDIRECT_HTTP=true
  - SSL_HSTS_ENABLED=true
  
  # Data Export Security (v1.2.0)
  - EXPORT_RATE_LIMIT=10  # Per hour per user
  - EXPORT_RETENTION_DAYS=7
  - EXPORT_REQUIRE_PERMISSION=true
  - EXPORT_AUDIT_LOGGING=true
  
  # Database
  - SQLITE_PATH=/app/data/kasa_monitor.db
  
  # Network Mode
  - NETWORK_MODE=bridge
  - DISCOVERY_ENABLED=false
  - MANUAL_DEVICES_ENABLED=true
  
  # CORS Security
  - CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
  
  # File Upload Security
  - MAX_UPLOAD_SIZE_MB=10
  - ALLOWED_UPLOAD_EXTENSIONS=.zip,.py,.json
  - REQUIRE_PLUGIN_SIGNATURES=true
  
  # Optional: TP-Link Cloud
  - TPLINK_USERNAME=your@email.com
  - TPLINK_PASSWORD=yourpassword
  
  # Optional: InfluxDB (use env vars instead of hardcoding)
  - INFLUXDB_URL=http://influxdb:8086
  - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}  # Set in .env file
  - INFLUXDB_ORG=kasa-monitor
  - INFLUXDB_BUCKET=device-data
  
  # InfluxDB Docker Init (for docker-compose)
  - DOCKER_INFLUXDB_INIT_USERNAME=${DOCKER_INFLUXDB_INIT_USERNAME}
  - DOCKER_INFLUXDB_INIT_PASSWORD=${DOCKER_INFLUXDB_INIT_PASSWORD}
  - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}
  
  # Performance (Raspberry Pi)
  - NODE_OPTIONS=--max-old-space-size=1024
```

## Manual Installation

### Prerequisites

1. **Install Node.js 18+**
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node

# Verify
node --version  # Should be 18.x or higher
```

2. **Install Python 3.11+**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# macOS
brew install python@3.11

# Verify
python3 --version  # Should be 3.11.x or higher
```

### Installation Steps

1. **Clone the repository**
```bash
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor
```

2. **Install frontend dependencies**
```bash
npm install
```

3. **Set up Python virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Build the frontend**
```bash
npm run build
```

5. **Initialize the database**
```bash
python3 backend/server.py --init-db
```

6. **Start the application**
```bash
# Terminal 1: Start backend
source venv/bin/activate
python3 backend/server.py

# Terminal 2: Start frontend
npm start
```

Access at: `http://localhost:3000`

### Running as a Service

#### systemd (Linux)

Create `/etc/systemd/system/kasa-monitor.service`:

```ini
[Unit]
Description=Kasa Monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/kasa-monitor
ExecStart=/home/pi/kasa-monitor/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kasa-monitor
sudo systemctl start kasa-monitor
```

## Raspberry Pi Setup

### Optimized for Raspberry Pi 5

1. **Update system**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in
```

3. **Deploy with host network**
```bash
# Best for Pi - full discovery support
docker run -d \
  --name kasa-monitor \
  --network host \
  --restart unless-stopped \
  -v kasa_data:/app/data \
  -e NODE_OPTIONS="--max-old-space-size=1024" \
  xante8088/kasa-monitor:latest
```

4. **Access the application**
```
http://[raspberry-pi-ip]:3000
```

### Performance Optimization

For Raspberry Pi, use these settings:

```yaml
# docker-compose.yml
services:
  kasa-monitor:
    environment:
      - NODE_OPTIONS=--max-old-space-size=1024
      - PYTHONUNBUFFERED=1
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

## Post-Installation

### Initial Security Setup (v1.2.0)

1. **Generate Secure JWT Secret:**
   ```bash
   # Generate and save to .env file
   echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
   ```

2. **Configure SSL Certificate:**
   - Access admin panel: `https://localhost/admin/system`
   - Navigate to SSL/TLS Settings
   - Upload certificate and private key
   - Or use Let's Encrypt for automatic certificates

3. **Set Up User Permissions:**
   ```bash
   # Grant data export permission to users
   docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
     "INSERT INTO user_permissions (user_id, permission_id) \
      SELECT u.id, p.id FROM users u, permissions p \
      WHERE u.username='operator' AND p.name='DATA_EXPORT';"
   ```

4. **Configure Export Retention:**
   ```bash
   # Set retention policies
   docker exec kasa-monitor python3 -c "
   from export_retention_config import configure_retention
   configure_retention(device_data_days=7, audit_logs_days=30)
   "
   ```

5. **Verify Security Status:**
   ```bash
   # Check authentication security
   curl -H "Authorization: Bearer $TOKEN" \
     https://localhost:5272/api/auth/security-status
   ```

### 1. Initial Setup

1. Navigate to `http://localhost:3000`
2. Create admin account
3. Configure electricity rates
4. Add devices (discovery or manual)

### 2. Verify Installation

```bash
# Check services are running
docker ps  # For Docker
curl http://localhost:5272/api/devices  # API check
```

### 3. Configure Firewall

```bash
# Allow required ports
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 5272/tcp  # API
sudo ufw allow 9999/udp  # Device discovery
```

### 4. Set Up Backups

```bash
# Backup Docker volumes
docker run --rm \
  -v kasa_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/kasa-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## Troubleshooting Installation

### Docker Issues

**Cannot connect to Docker daemon**
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in
```

**Port already in use**
```bash
# Find process using port
sudo lsof -i :3000
# Change port in docker-compose.yml
```

### Manual Installation Issues

**Node.js version too old**
```bash
# Update Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Python module not found**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Device Discovery Issues

See [Network Configuration](Network-Configuration) for detailed troubleshooting.

## Next Steps

- [First Time Setup](First-Time-Setup) - Configure your installation
- [Device Management](Device-Management) - Add your devices
- [Dashboard Overview](Dashboard-Overview) - Understanding the interface
- [Security Guide](Security-Guide) - Secure your installation

## Getting Help

- Check [Common Issues](Common-Issues)
- Browse [FAQ](FAQ)
- Open an [issue](https://github.com/xante8088/kasa-monitor/issues)

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Added security environment variables for JWT, CORS, file uploads, and InfluxDB credentials