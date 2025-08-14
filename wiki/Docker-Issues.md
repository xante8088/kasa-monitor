# Docker Issues

Comprehensive troubleshooting guide for Docker-related issues with Kasa Monitor.

## Docker Overview

```
┌─────────────────────────────────────┐
│     Common Docker Issues            │
├─────────────────────────────────────┤
│  1. Container Won't Start           │
│  2. Network Connectivity            │
│  3. Volume Permissions              │
│  4. Resource Constraints            │
│  5. Image Problems                  │
└─────────────────────────────────────┘
```

## Container Startup Issues

### Container Exits Immediately

**Symptoms:**
- Container starts then stops
- Exit code 1, 125, 126, or 127
- No logs available

**Diagnosis:**
```bash
# Check exit code
docker ps -a | grep kasa-monitor

# View detailed error
docker logs kasa-monitor

# Inspect container
docker inspect kasa-monitor | grep -A 10 "State"

# Debug with shell
docker run -it --entrypoint /bin/sh xante8088/kasa-monitor
```

**Common Causes & Solutions:**

#### 1. Port Already in Use
```bash
# Check if ports are in use
sudo netstat -tulpn | grep -E "3000|8000"
sudo lsof -i :3000
sudo lsof -i :8000

# Solution: Use different ports
docker run -p 3001:3000 -p 8001:8000 xante8088/kasa-monitor

# Or in docker-compose.yml
ports:
  - "3001:3000"
  - "8001:8000"
```

#### 2. Missing Environment Variables
```bash
# Check required variables
docker run -e NODE_ENV=production \
  -e TZ=America/New_York \
  -e JWT_SECRET_KEY=your-secret \
  xante8088/kasa-monitor

# Use env file
docker run --env-file .env xante8088/kasa-monitor
```

#### 3. Incorrect Entrypoint
```bash
# Override entrypoint for debugging
docker run --entrypoint /bin/bash -it xante8088/kasa-monitor

# Check startup script
cat /app/start.sh
chmod +x /app/start.sh
```

### Container Crash Loop

**Symptoms:**
- Container restarts repeatedly
- Status: "Restarting"
- High restart count

**Solutions:**

```bash
# Disable auto-restart for debugging
docker update --restart=no kasa-monitor

# Check logs for crash reason
docker logs --tail 50 -f kasa-monitor

# Increase restart delay
docker run --restart-delay=30s xante8088/kasa-monitor

# Resource limits might be too low
docker run -m 512m --cpus="1.0" xante8088/kasa-monitor
```

## Network Issues

### Cannot Access Web Interface

**Symptoms:**
- Cannot reach http://localhost:3000
- Connection refused or timeout
- "This site can't be reached"

**Diagnosis & Solutions:**

```bash
# 1. Check if container is running
docker ps | grep kasa-monitor

# 2. Check port mapping
docker port kasa-monitor

# 3. Test from inside container
docker exec kasa-monitor curl http://localhost:3000

# 4. Check container logs
docker logs kasa-monitor | grep -i error

# 5. Verify network
docker network ls
docker network inspect bridge

# 6. Test with explicit IP
docker inspect kasa-monitor | grep IPAddress
curl http://172.17.0.2:3000  # Use container IP

# 7. Firewall issues
sudo ufw status
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
```

### Container Cannot Reach Devices

**Problem:** Container isolated from local network

**Solution 1: Host Network Mode**
```bash
docker run --network host xante8088/kasa-monitor
```

**Solution 2: Custom Bridge Network**
```bash
# Create network
docker network create --driver bridge \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  kasa-net

# Run container
docker run --network kasa-net xante8088/kasa-monitor
```

**Solution 3: Macvlan Network**
```bash
# Create macvlan
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 macvlan-net

# Run with static IP
docker run --network macvlan-net \
  --ip=192.168.1.199 \
  xante8088/kasa-monitor
```

### DNS Resolution Issues

```bash
# Test DNS inside container
docker exec kasa-monitor nslookup google.com
docker exec kasa-monitor cat /etc/resolv.conf

# Fix: Use custom DNS
docker run --dns 8.8.8.8 --dns 8.8.4.4 xante8088/kasa-monitor

# Or in docker-compose.yml
dns:
  - 8.8.8.8
  - 8.8.4.4
```

## Volume and Permission Issues

### Permission Denied Errors

**Symptoms:**
- "Permission denied" in logs
- Cannot write to database
- Cannot create files

**Solutions:**

```bash
# Check volume permissions
docker exec kasa-monitor ls -la /app/data

# Fix ownership
docker exec -u root kasa-monitor chown -R 1000:1000 /app/data

# Run as root (temporary fix)
docker run --user root xante8088/kasa-monitor

# Proper fix: Set correct permissions on host
sudo chown -R 1000:1000 ./data
sudo chmod -R 755 ./data
```

### Volume Not Persisting Data

```bash
# Check volume mounting
docker inspect kasa-monitor | grep -A 10 Mounts

# Ensure volume exists
docker volume ls
docker volume create kasa_data

# Mount correctly
docker run -v kasa_data:/app/data xante8088/kasa-monitor

# For bind mounts, use absolute paths
docker run -v /absolute/path/to/data:/app/data xante8088/kasa-monitor
```

### Database Lock Issues

```bash
# SQLite database locked
docker exec kasa-monitor lsof | grep kasa_monitor.db

# Fix: Stop all connections
docker restart kasa-monitor

# Or remove lock file
docker exec kasa-monitor rm -f /app/data/kasa_monitor.db-wal
docker exec kasa-monitor rm -f /app/data/kasa_monitor.db-shm
```

## Resource Issues

### Out of Memory

**Symptoms:**
- Container killed with exit code 137
- "Out of memory" in system logs
- Container becomes unresponsive

**Solutions:**

```bash
# Check memory usage
docker stats kasa-monitor

# Increase memory limit
docker run -m 1g xante8088/kasa-monitor

# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 256M

# Check system memory
free -h
```

### High CPU Usage

```bash
# Monitor CPU usage
docker stats --no-stream

# Limit CPU usage
docker run --cpus="1.5" xante8088/kasa-monitor

# Set CPU shares
docker run --cpu-shares=512 xante8088/kasa-monitor
```

### Disk Space Issues

```bash
# Check disk usage
docker system df
df -h

# Clean up unused resources
docker system prune -a
docker volume prune
docker image prune -a

# Remove old logs
docker exec kasa-monitor sh -c "rm -f /app/logs/*.log.old"

# Limit log size
docker run --log-opt max-size=10m --log-opt max-file=3 xante8088/kasa-monitor
```

## Image Issues

### Cannot Pull Image

```bash
# Check Docker Hub status
curl https://status.docker.com/

# Try explicit tag
docker pull xante8088/kasa-monitor:latest
docker pull xante8088/kasa-monitor:v1.0.0

# Use different registry
docker pull ghcr.io/xante8088/kasa-monitor:latest

# Build locally if needed
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor
docker build -t kasa-monitor .
```

### Image Compatibility Issues

```bash
# Check architecture
docker version
uname -m

# For ARM devices (Raspberry Pi)
docker pull --platform linux/arm64 xante8088/kasa-monitor

# Multi-arch image
docker buildx build --platform linux/amd64,linux/arm64 -t kasa-monitor .
```

## Docker Compose Issues

### Compose File Errors

```yaml
# Common syntax issues

# Wrong: No quotes for environment values with special chars
environment:
  PASSWORD: p@ssw0rd!  # Will cause error

# Correct:
environment:
  PASSWORD: "p@ssw0rd!"

# Wrong: Incorrect indentation
services:
kasa-monitor:  # Missing indent
  image: xante8088/kasa-monitor

# Correct:
services:
  kasa-monitor:
    image: xante8088/kasa-monitor
```

### Service Dependencies

```yaml
# Ensure services start in order
services:
  database:
    image: postgres:13
    
  kasa-monitor:
    image: xante8088/kasa-monitor
    depends_on:
      - database
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### Environment Variable Issues

```bash
# Check if .env file is loaded
docker-compose config

# Explicitly specify env file
docker-compose --env-file .env.production up

# Debug environment variables
docker-compose run kasa-monitor env
```

## Docker Desktop Issues

### Windows-Specific Issues

```powershell
# WSL2 backend issues
wsl --list --verbose
wsl --set-default-version 2

# Reset Docker Desktop
# Settings -> Troubleshoot -> Reset to factory defaults

# Firewall blocking
New-NetFirewallRule -DisplayName "Docker" -Direction Inbound -Protocol TCP -LocalPort 3000,8000 -Action Allow
```

### macOS-Specific Issues

```bash
# Resource limits in Docker Desktop
# Docker Desktop -> Preferences -> Resources
# Increase CPUs and Memory

# File sharing issues
# Docker Desktop -> Preferences -> Resources -> File Sharing
# Add project directory

# Reset Docker Desktop
rm -rf ~/Library/Group\ Containers/group.com.docker
rm -rf ~/Library/Containers/com.docker.docker
```

## Debugging Tools

### Interactive Debugging

```bash
# Start container with shell
docker run -it --entrypoint /bin/bash xante8088/kasa-monitor

# Attach to running container
docker exec -it kasa-monitor /bin/bash

# Run commands inside container
docker exec kasa-monitor python3 -c "import sys; print(sys.version)"
```

### Log Analysis

```bash
# View all logs
docker logs kasa-monitor

# Follow logs
docker logs -f kasa-monitor

# Timestamps
docker logs -t kasa-monitor

# Since specific time
docker logs --since 2024-01-15T10:00:00 kasa-monitor

# Export logs
docker logs kasa-monitor > kasa-monitor.log 2>&1
```

### Health Check Debugging

```bash
# Check health status
docker inspect kasa-monitor | jq '.[0].State.Health'

# Run health check manually
docker exec kasa-monitor /bin/sh -c "curl -f http://localhost:8000/health"

# View health check logs
docker inspect kasa-monitor | jq '.[0].State.Health.Log'
```

## Recovery Procedures

### Container Recovery

```bash
#!/bin/bash
# recover-container.sh

# Stop and remove problematic container
docker stop kasa-monitor
docker rm kasa-monitor

# Backup data volume
docker run --rm -v kasa_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/data-backup.tar.gz -C /data .

# Pull fresh image
docker pull xante8088/kasa-monitor:latest

# Start new container
docker run -d \
  --name kasa-monitor \
  --restart unless-stopped \
  -v kasa_data:/app/data \
  -p 3000:3000 \
  -p 8000:8000 \
  xante8088/kasa-monitor

# Verify
sleep 10
curl http://localhost:8000/health
```

### Data Recovery

```bash
# Restore from backup
docker run --rm -v kasa_data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/data-backup.tar.gz"

# Fix permissions
docker run --rm -v kasa_data:/data \
  alpine chown -R 1000:1000 /data

# Verify database
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db "PRAGMA integrity_check"
```

## Prevention Best Practices

1. **Always Use Named Volumes** for persistent data
2. **Set Resource Limits** to prevent system exhaustion
3. **Enable Health Checks** for automatic recovery
4. **Use Specific Image Tags** instead of latest
5. **Regular Backups** of data volumes
6. **Monitor Container Logs** for early warning signs
7. **Test in Development** before production deployment

## Diagnostic Script

```bash
#!/bin/bash
# diagnose-docker.sh

echo "=== Docker Diagnostics for Kasa Monitor ==="

# Docker version
echo "Docker Version:"
docker version --format "Client: {{.Client.Version}}, Server: {{.Server.Version}}"

# Container status
echo -e "\nContainer Status:"
docker ps -a --filter name=kasa-monitor --format "table {{.Status}}\t{{.Ports}}"

# Resource usage
echo -e "\nResource Usage:"
docker stats --no-stream kasa-monitor

# Network info
echo -e "\nNetwork Configuration:"
docker inspect kasa-monitor | jq '.[0].NetworkSettings.Networks'

# Volume info
echo -e "\nVolume Mounts:"
docker inspect kasa-monitor | jq '.[0].Mounts'

# Recent logs
echo -e "\nRecent Logs:"
docker logs --tail 20 kasa-monitor

# Health status
echo -e "\nHealth Check:"
docker inspect kasa-monitor | jq '.[0].State.Health.Status'
```

## Related Pages

- [Docker Deployment](Docker-Deployment) - Deployment guide
- [Installation](Installation) - Installation instructions
- [Common Issues](Common-Issues) - General troubleshooting
- [Device Discovery Issues](Device-Discovery-Issues) - Network-specific issues