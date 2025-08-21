# 🐳 Docker Deployment for Raspberry Pi 5

This guide explains how to run Kasa Monitor in Docker on a Raspberry Pi 5, optimized for ARM64 architecture.

## 📋 Prerequisites

### Required Software
- Raspberry Pi OS (64-bit) or Ubuntu Server 22.04+
- Docker Engine 20.10+ 
- Docker Compose 2.0+
- At least 4GB RAM (8GB recommended)

### Install Docker on Raspberry Pi 5

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Reboot to apply group changes
sudo reboot
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor
```

### 2. Build and Run
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 3. Access Application
- **Frontend**: http://your-pi-ip:3000
- **Backend API**: http://your-pi-ip:5272
- **API Documentation**: http://your-pi-ip:5272/docs

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:

```bash
# Database
SQLITE_PATH=/app/data/kasa_monitor.db

# Optional: TP-Link Cloud credentials
TPLINK_USERNAME=your-email@example.com
TPLINK_PASSWORD=your-password

# Security
JWT_SECRET_KEY=your-secure-random-key-here
ALLOW_LOCAL_ONLY=true

# Optional: InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=kasa-monitor
INFLUXDB_BUCKET=device-data
```

### SSL/HTTPS Setup
1. Create SSL directory and add certificates:
```bash
mkdir ssl
# Copy your cert.pem and key.pem files to ssl/
```

2. Enable HTTPS in docker-compose.yml:
```yaml
environment:
  - USE_HTTPS=true
  - SSL_CERT_PATH=/app/ssl/cert.pem
  - SSL_KEY_PATH=/app/ssl/key.pem
```

## 🗄️ Data Persistence

### Default Volumes
- `./data` - SQLite database and application data
- `./logs` - Application logs
- `./ssl` - SSL certificates (optional)

### Backup Data
```bash
# Create backup
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db ".backup /app/data/backup-$(date +%Y%m%d).db"

# Copy to host
docker cp kasa-monitor:/app/data/backup-$(date +%Y%m%d).db ./backups/
```

## 📊 Optional: InfluxDB for Time-Series Data

### Start with InfluxDB
```bash
# Start main app + InfluxDB
docker-compose --profile influxdb up -d

# InfluxDB will be available at http://your-pi-ip:8086
# Login: admin / kasaMonitor2025
```

### Configure Kasa Monitor for InfluxDB
Update environment variables in docker-compose.yml:
```yaml
environment:
  - INFLUXDB_URL=http://influxdb:8086
  - INFLUXDB_TOKEN=your-token-from-influxdb
  - INFLUXDB_ORG=kasa-monitor
  - INFLUXDB_BUCKET=device-data
```

## 🔧 Management Commands

### Container Management
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f kasa-monitor

# Update to latest
docker-compose pull
docker-compose up -d
```

### Monitor Performance
```bash
# Container stats
docker stats kasa-monitor

# System resources
htop

# Storage usage
df -h
docker system df
```

## 🛠️ Troubleshooting

### Common Issues

**1. Out of Memory**
```bash
# Check memory usage
free -h
docker stats

# Reduce Node.js memory limit in docker-compose.yml:
NODE_OPTIONS=--max-old-space-size=512
```

**2. Port Conflicts**
```bash
# Check what's using ports
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :5272

# Change ports in docker-compose.yml if needed:
ports:
  - "3001:3000"  # Frontend
  - "8001:5272"  # Backend
```

**3. Slow Performance**
```bash
# Monitor I/O
iotop

# Check SD card speed
sudo hdparm -t /dev/mmcblk0

# Consider using USB 3.0 SSD for better performance
```

**4. Container Won't Start**
```bash
# Check container logs
docker-compose logs kasa-monitor

# Check system logs
journalctl -u docker

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Build Issues
```bash
# Clean Docker system
docker system prune -af

# Rebuild with verbose output
docker-compose build --no-cache --progress=plain

# Force ARM64 platform
docker buildx build --platform linux/arm64 -t kasa-monitor .
```

## 🔒 Security Best Practices

### 1. Network Security
- Change default ports if exposed to internet
- Use reverse proxy (nginx) with SSL termination
- Configure firewall rules

### 2. Container Security
```bash
# Run security scan
docker scout quickview kasa-monitor

# Update base images regularly
docker-compose pull
```

### 3. Data Protection
- Regular database backups
- Secure SSL certificates
- Strong JWT secret keys
- Monitor access logs

## 📈 Performance Optimization

### Raspberry Pi 5 Specific
```yaml
# In docker-compose.yml, optimize resource limits:
deploy:
  resources:
    limits:
      memory: 3G        # Use more RAM if available
      cpus: '3.0'       # Use more CPU cores
    reservations:
      memory: 1G
      cpus: '1.0'
```

### Storage Optimization
```bash
# Use fast USB 3.0 SSD instead of SD card
# Mount at /opt/kasa-monitor for better performance

# Update docker-compose.yml volumes:
volumes:
  - /opt/kasa-monitor/data:/app/data
  - /opt/kasa-monitor/logs:/app/logs
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Raspberry Pi Docker Guide](https://docs.docker.com/engine/install/debian/)
- [Kasa Monitor API Documentation](http://your-pi-ip:5272/docs)

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs -f`
3. Open an issue on [GitHub](https://github.com/xante8088/kasa-monitor/issues)

---

🐳 **Happy Containerizing!** Your Kasa Monitor is now running efficiently in Docker on Raspberry Pi 5!