# 🐳 Docker Hub Deployment Guide

This guide explains how to set up automated Docker builds and deploy from Docker Hub.

## 📋 Prerequisites

1. **Docker Hub Account**: [hub.docker.com](https://hub.docker.com)
2. **GitHub Account**: For automated builds
3. **Raspberry Pi 5**: With Docker installed

## 🏗️ Step 1: Create Docker Hub Repository

### Manual Setup
1. Login to [Docker Hub](https://hub.docker.com)
2. Click "Create Repository"
3. **Repository Name**: `kasa-monitor`
4. **Description**: `Web application for monitoring Kasa smart devices - Raspberry Pi optimized`
5. **Visibility**: Public (recommended) or Private
6. Click "Create"

### Your Repository URL
```
https://hub.docker.com/r/YOUR-USERNAME/kasa-monitor
```

## 🤖 Step 2: Set up GitHub Actions (Automated Builds)

### Configure GitHub Secrets
1. Go to your GitHub repository: `https://github.com/xante8088/kasa-monitor`
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add these Repository secrets:

| Secret Name | Value | Description |
|-------------|--------|-------------|
| `DOCKER_USERNAME` | your-dockerhub-username | Your Docker Hub username |
| `DOCKER_PASSWORD` | your-dockerhub-token | Docker Hub access token |

### Create Docker Hub Access Token
1. Login to Docker Hub
2. Go to **Account Settings** → **Security** → **New Access Token**
3. **Description**: `GitHub Actions - Kasa Monitor`
4. **Permissions**: `Read, Write, Delete`
5. Copy the token and use it as `DOCKER_PASSWORD` secret

### Automated Build Triggers
The GitHub Action will automatically build and push when:
- ✅ Push to `main` branch
- ✅ Create a new release/tag
- ✅ Changes to Dockerfile, source code, or dependencies

## 🚀 Step 3: Deploy from Docker Hub

### Quick Start - Production Deployment
```bash
# Download production compose file
curl -o docker-compose.yml https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.prod.yml

# Edit the image name to match your Docker Hub username
sed -i 's/xante8088/YOUR-DOCKERHUB-USERNAME/g' docker-compose.yml

# Create environment file
cat > .env << EOF
DOCKER_USERNAME=YOUR-DOCKERHUB-USERNAME
SQLITE_PATH=/app/data/kasa_monitor.db
ALLOW_LOCAL_ONLY=true
NODE_OPTIONS=--max-old-space-size=1024
PYTHONUNBUFFERED=1
EOF

# Start the application
docker-compose up -d
```

### Alternative: Direct Docker Run
```bash
# Pull the latest image
docker pull YOUR-DOCKERHUB-USERNAME/kasa-monitor:pi5

# Run container
docker run -d \
  --name kasa-monitor \
  --restart unless-stopped \
  -p 3000:3000 \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e SQLITE_PATH=/app/data/kasa_monitor.db \
  -e ALLOW_LOCAL_ONLY=true \
  YOUR-DOCKERHUB-USERNAME/kasa-monitor:pi5
```

## 🏷️ Available Image Tags

| Tag | Description | Platform | Use Case |
|-----|-------------|----------|----------|
| `latest` | Latest stable build | ARM64, AMD64 | General use |
| `pi5` | Raspberry Pi 5 optimized | ARM64, AMD64 | Recommended for Pi |
| `v1.0.0` | Specific version | ARM64, AMD64 | Production pinning |
| `main-abc1234` | Development builds | ARM64, AMD64 | Testing |

## 🔄 Update Process

### Automatic Updates
```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d

# Clean up old images
docker system prune -f
```

### Manual Version Pinning
```yaml
# In docker-compose.yml, pin to specific version
services:
  kasa-monitor:
    image: YOUR-USERNAME/kasa-monitor:v1.0.0  # Pin to specific version
```

## 📊 Docker Hub Repository Features

### Repository Information
- **Multi-architecture support**: ARM64 (Pi 5) + AMD64 (x86)
- **Automated builds**: Triggered by GitHub commits
- **Vulnerability scanning**: Automatic security analysis
- **Build history**: Track all builds and versions
- **Download stats**: Monitor usage

### Image Details
- **Base**: Python 3.11 slim + Node.js 18 Alpine
- **Size**: ~800MB compressed
- **Layers**: Optimized multi-stage build
- **Security**: Non-root user, minimal attack surface

## 🛠️ Advanced Configuration

### Environment Variables
```bash
# Create comprehensive .env file
cat > .env << EOF
# Docker Hub Configuration
DOCKER_USERNAME=your-dockerhub-username

# Database
SQLITE_PATH=/app/data/kasa_monitor.db

# Optional: TP-Link Cloud Credentials
TPLINK_USERNAME=user@example.com
TPLINK_PASSWORD=your-password

# Security
JWT_SECRET_KEY=your-secure-random-key
ALLOW_LOCAL_ONLY=true
ALLOWED_NETWORKS=192.168.0.0/16,10.0.0.0/8

# Performance (Raspberry Pi 5)
NODE_OPTIONS=--max-old-space-size=1024
PYTHONUNBUFFERED=1

# Optional: InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=kasa-monitor
INFLUXDB_BUCKET=device-data
EOF
```

### Resource Limits
```yaml
# Optimize for your Pi's available resources
deploy:
  resources:
    limits:
      memory: 3G      # Increase if you have 8GB Pi
      cpus: '3.0'     # Use more cores if needed
    reservations:
      memory: 1G
      cpus: '1.0'
```

## 🔍 Monitoring & Maintenance

### Container Health
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f kasa-monitor

# Monitor resources
docker stats kasa-monitor

# Health check
curl http://localhost:8000/api/devices
```

### Updates & Maintenance
```bash
# Weekly update routine
docker-compose pull                    # Pull latest images
docker-compose up -d                   # Restart with new images
docker system prune -f                 # Clean up old images
docker volume prune -f                 # Clean up unused volumes
```

## 🆘 Troubleshooting

### Common Issues

**1. Image Pull Errors**
```bash
# Check Docker Hub credentials
docker login

# Verify image exists
docker search YOUR-USERNAME/kasa-monitor

# Pull specific tag
docker pull YOUR-USERNAME/kasa-monitor:pi5
```

**2. Architecture Mismatch**
```bash
# Force ARM64 platform on Pi
docker pull --platform linux/arm64 YOUR-USERNAME/kasa-monitor:pi5
```

**3. Build Failures in GitHub Actions**
```bash
# Check GitHub Actions logs in your repository
# Go to: Actions tab → Latest workflow run → View logs
```

## 📈 Performance Optimization

### Multi-Stage Build Benefits
- **Smaller image size**: ~800MB vs 2GB+ without optimization
- **Faster pulls**: Optimized layer caching
- **Better security**: Minimal runtime dependencies
- **Cross-platform**: Single image for ARM64 + AMD64

### Raspberry Pi 5 Specific
```bash
# Monitor performance
htop
docker stats

# Optimize storage (use SSD if possible)
# Mount data volume to faster storage:
docker-compose.yml:
volumes:
  - /mnt/ssd/kasa-data:/app/data  # External SSD
```

## 🔗 Useful Links

- **Docker Hub Repository**: `https://hub.docker.com/r/YOUR-USERNAME/kasa-monitor`
- **GitHub Repository**: `https://github.com/xante8088/kasa-monitor`
- **Documentation**: [DOCKER.md](./DOCKER.md)
- **Issues & Support**: GitHub Issues

## 📚 Example Deployment Commands

### Complete Raspberry Pi 5 Setup
```bash
#!/bin/bash
# Complete setup script for Raspberry Pi 5

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker if not already installed
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt install docker-compose-plugin

# Create project directory
mkdir -p ~/kasa-monitor
cd ~/kasa-monitor

# Download docker-compose file
curl -o docker-compose.yml https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.prod.yml

# Replace username (update this line)
sed -i 's/xante8088/YOUR-DOCKERHUB-USERNAME/g' docker-compose.yml

# Create environment
cat > .env << EOF
DOCKER_USERNAME=YOUR-DOCKERHUB-USERNAME
SQLITE_PATH=/app/data/kasa_monitor.db
ALLOW_LOCAL_ONLY=true
NODE_OPTIONS=--max-old-space-size=1024
PYTHONUNBUFFERED=1
EOF

# Create data directories
mkdir -p data logs ssl

# Deploy
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f

echo "🎉 Kasa Monitor deployed!"
echo "🌐 Access at: http://$(hostname -I | awk '{print $1}'):3000"
```

---

🐳 **Happy Docker Hub Deployment!** Your Kasa Monitor is now available as a public Docker image for easy deployment on any Raspberry Pi 5!