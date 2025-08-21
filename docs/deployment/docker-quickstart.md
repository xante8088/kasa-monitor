# 🚀 Quick Start Guide - Docker Deployment

Get Kasa Monitor running in under 5 minutes with Docker!

## Prerequisites

- Docker and Docker Compose installed
- Network access to your Kasa smart devices
- 2GB+ RAM available

## 🎯 Option 1: Fastest Setup (Recommended)

Copy and run these commands:

```bash
# Create project directory
mkdir -p ~/kasa-monitor && cd ~/kasa-monitor

# Download docker-compose file
curl -o docker-compose.yml https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.sample.yml

# No need to create directories - Docker will manage named volumes

# Start Kasa Monitor
docker-compose up -d

# View logs
docker-compose logs -f
```

**Access the application:**
- Frontend: http://localhost:3000
- API: http://localhost:5272/docs

## 🔧 Option 2: Customized Setup

### Step 1: Download Files

```bash
# Clone repository (or download files)
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor

# Or just download the sample files
curl -O https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.sample.yml
curl -O https://raw.githubusercontent.com/xante8088/kasa-monitor/main/.env.sample
```

### Step 2: Configure Environment

```bash
# Copy sample files
cp docker-compose.sample.yml docker-compose.yml
cp .env.sample .env

# Edit environment variables
nano .env
```

**Key settings to change:**
- `JWT_SECRET_KEY` - Generate with: `openssl rand -hex 32`
- `TZ` - Your timezone (e.g., `America/New_York`)
- `TPLINK_USERNAME/PASSWORD` - Optional cloud credentials

### Step 3: Launch Application

```bash
# No need to create directories - Docker will manage named volumes

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f kasa-monitor
```

## 📱 First Time Setup

1. **Access the application:**
   ```
   http://your-server-ip:3000
   ```

2. **Create admin account:**
   - You'll be redirected to `/setup` on first visit
   - Create your administrator account
   - Login with your new credentials

3. **Discover devices:**
   - Go to Devices → Discover
   - Devices on your network will be auto-detected
   - Click "Add" to start monitoring

4. **Configure electricity rates:**
   - Go to Settings → Rates
   - Enter your utility rates
   - Choose from 6 rate structures

## 🐳 Docker Commands Reference

### Basic Operations

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f kasa-monitor

# View last 100 lines
docker-compose logs --tail=100 kasa-monitor
```

### Updates & Maintenance

```bash
# Update to latest version
docker-compose pull
docker-compose up -d

# Backup database
docker-compose exec kasa-monitor sqlite3 /app/data/kasa_monitor.db ".backup /app/data/backup-$(date +%Y%m%d).db"

# Clean up old images
docker system prune -af

# View volumes
docker volume ls | grep kasa

# Backup volume data
docker run --rm -v kasa_data:/data -v $(pwd):/backup alpine tar czf /backup/kasa-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restore volume data
docker run --rm -v kasa_data:/data -v $(pwd):/backup alpine tar xzf /backup/kasa-backup.tar.gz -C /data
```

### Troubleshooting

```bash
# Check container status
docker-compose ps

# Check resource usage
docker stats kasa-monitor

# Enter container shell
docker-compose exec kasa-monitor /bin/bash

# Check container health
docker inspect kasa-monitor --format='{{.State.Health.Status}}'

# Force rebuild (if needed)
docker-compose build --no-cache
docker-compose up -d
```

## 🌐 Network Configuration

### Using Different Ports

Edit `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Frontend on port 3001
  - "8001:5272"  # API on port 8001
```

### Expose to Network

By default, accessible from any network interface. To restrict:
```yaml
ports:
  - "127.0.0.1:3000:3000"  # Local only
  - "127.0.0.1:5272:5272"
```

## 🔒 Security Setup

### Generate Secure JWT Key

```bash
# Generate secure key
JWT_KEY=$(openssl rand -hex 32)

# Add to .env file
echo "JWT_SECRET_KEY=$JWT_KEY" >> .env
```

### Enable HTTPS

1. **Add certificates:**
   ```bash
   # Copy your certificates
   cp /path/to/cert.pem ./ssl/
   cp /path/to/key.pem ./ssl/
   ```

2. **Update .env:**
   ```env
   USE_HTTPS=true
   SSL_CERT_PATH=/app/ssl/cert.pem
   SSL_KEY_PATH=/app/ssl/key.pem
   ```

3. **Restart:**
   ```bash
   docker-compose restart
   ```

## 📊 Optional: Add InfluxDB

For advanced time-series data storage:

```bash
# Start with InfluxDB profile
docker-compose --profile influxdb up -d

# Access InfluxDB UI
# http://localhost:8086
# Login: admin / SuperSecurePassword123!
```

## 🐧 Raspberry Pi Deployment

### Optimized for Pi 5:

```bash
# Check architecture
uname -m  # Should show aarch64 for 64-bit

# Pull Pi-optimized image
docker pull xante8088/kasa-monitor:pi5

# Use reduced memory settings
export NODE_OPTIONS="--max-old-space-size=512"
docker-compose up -d
```

### Performance Tips:
- Use external SSD for data volume
- Limit memory: `deploy.resources.limits.memory: 1G`
- Reduce polling interval if needed

## ❓ Common Issues

### Port Already in Use
```bash
# Find what's using port 3000
sudo lsof -i :3000

# Change port in docker-compose.yml
ports:
  - "3001:3000"
```

### Can't Connect to Devices
- Ensure Docker network can reach your IoT devices
- Check firewall rules
- Verify devices are on same network segment

### Container Keeps Restarting
```bash
# Check logs for errors
docker-compose logs --tail=50 kasa-monitor

# Check memory usage
docker stats kasa-monitor
```

## 🆘 Get Help

- **Documentation**: [Full Docs](https://github.com/xante8088/kasa-monitor)
- **Issues**: [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)
- **Logs**: Always check `docker-compose logs` first!

## 🎉 Success Checklist

- [ ] Docker Compose running (`docker-compose ps`)
- [ ] Can access http://localhost:3000
- [ ] Admin account created
- [ ] Devices discovered
- [ ] Electricity rates configured
- [ ] Data being collected (check charts)

**Congratulations!** Kasa Monitor is now running and monitoring your smart devices! 🎊