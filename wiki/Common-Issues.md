# Common Issues & Solutions

Quick solutions to frequently encountered problems with Kasa Monitor.

## Installation Issues

### Docker: Cannot connect to Docker daemon

**Error:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solution:**
```bash
# Start Docker service
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
exit
```

### Port already in use

**Error:**
```
Error: bind: address already in use :3000
```

**Solution:**
```bash
# Find process using port
sudo lsof -i :3000
# OR
sudo netstat -tulpn | grep 3000

# Kill process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "3001:3000"  # Use different port
```

### Permission denied

**Error:**
```
Permission denied: '/app/data/kasa_monitor.db'
```

**Solution:**
```bash
# Fix volume permissions
docker exec kasa-monitor chown -R appuser:appuser /app/data

# Or recreate volume
docker volume rm kasa_data
docker-compose up -d
```

## Device Discovery Issues

### No devices found

**Problem:** Discovery returns 0 devices

**Solutions:**

1. **Check network mode:**
```bash
# Verify using host or macvlan
docker inspect kasa-monitor | grep NetworkMode
```

2. **Allow UDP broadcasts:**
```bash
sudo ufw allow 9999/udp
```

3. **Verify same network:**
```bash
# In container
docker exec kasa-monitor ip addr
# Should be same subnet as devices
```

4. **Use manual entry:**
- Settings → Device Management
- Add Device Manually
- Enter IP address

### Devices show offline

**Problem:** Devices appear but show as offline

**Solutions:**

1. **Check device power:**
- Ensure device is plugged in
- Verify device LED is on

2. **Test connectivity:**
```bash
docker exec kasa-monitor ping <device-ip>
```

3. **Reset device:**
- Hold reset button 10 seconds
- Re-configure via Kasa app
- Re-add to Kasa Monitor

4. **Check firewall:**
```bash
sudo iptables -L | grep DROP
```

### Discovery works then stops

**Problem:** Devices discovered initially but stop responding

**Solution:**
```bash
# Restart discovery service
docker restart kasa-monitor

# Clear device cache
docker exec kasa-monitor rm /app/data/device_cache.json

# Increase timeout
environment:
  - DISCOVERY_TIMEOUT=10
```

## Authentication Issues

### Cannot create admin account

**Problem:** Setup page doesn't appear or errors

**Solutions:**

1. **Clear database:**
```bash
docker exec kasa-monitor rm /app/data/kasa_monitor.db
docker restart kasa-monitor
```

2. **Check API connectivity:**
```bash
curl http://localhost:8000/api/auth/setup-required
```

3. **View logs:**
```bash
docker logs kasa-monitor --tail 50
```

### Login redirect loop

**Problem:** After login, redirected back to login page

**Solutions:**

1. **Clear browser data:**
- Clear cookies for localhost
- Clear localStorage
- Try incognito mode

2. **Check token storage:**
```javascript
// In browser console
localStorage.getItem('token')
```

3. **Verify API response:**
```bash
# Test login endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

### Forgot admin password

**Problem:** Cannot log in as admin

**Solution:**
```bash
# Stop container
docker stop kasa-monitor

# Reset database
docker run --rm -v kasa_data:/data alpine \
  rm /data/kasa_monitor.db

# Restart
docker start kasa-monitor
# Go to /setup to create new admin
```

## Performance Issues

### High CPU usage

**Problem:** Container using excessive CPU

**Solutions:**

1. **Reduce polling frequency:**
```yaml
environment:
  - POLLING_INTERVAL=120  # 2 minutes instead of 1
```

2. **Limit device count:**
- Remove unused devices
- Disable monitoring for idle devices

3. **Set resource limits:**
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
```

### High memory usage

**Problem:** Container consuming too much RAM

**Solutions:**

1. **For Node.js:**
```yaml
environment:
  - NODE_OPTIONS=--max-old-space-size=512
```

2. **Reduce data retention:**
```yaml
environment:
  - DATA_RETENTION_DAYS=30  # Instead of 365
```

3. **Use InfluxDB for storage:**
- Offload time-series data
- Better compression
- Automatic downsampling

### Slow web interface

**Problem:** Dashboard loads slowly

**Solutions:**

1. **Clear browser cache:**
- Ctrl+Shift+R (hard refresh)
- Clear site data

2. **Reduce dashboard devices:**
- Filter to show only active
- Group by rooms
- Paginate results

3. **Check network latency:**
```bash
# From browser machine
ping <docker-host-ip>
```

## Data Issues

### Incorrect power readings

**Problem:** Power values seem wrong

**Solutions:**

1. **Calibrate device:**
```python
# If device supports calibration
device.set_calibration_values(
    voltage=120,
    current=1.0,
    power=120
)
```

2. **Update firmware:**
- Use Kasa mobile app
- Check for updates
- Install and restart

3. **Verify with kill-a-watt:**
- Compare readings
- Adjust calibration factor

### Missing historical data

**Problem:** Gaps in graphs

**Solutions:**

1. **Check polling status:**
```bash
docker logs kasa-monitor | grep "Polling"
```

2. **Verify database writes:**
```bash
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "SELECT COUNT(*) FROM readings WHERE date > datetime('now', '-1 day');"
```

3. **Check disk space:**
```bash
docker exec kasa-monitor df -h /app/data
```

### Cost calculations wrong

**Problem:** Costs don't match expectations

**Solutions:**

1. **Verify rate configuration:**
- Settings → Electricity Rates
- Compare with utility bill
- Include all fees/taxes

2. **Check time zone:**
```bash
docker exec kasa-monitor date
# Should match local time
```

3. **Align billing period:**
- Set correct billing cycle start
- Account for partial months

## Docker Issues

### Container keeps restarting

**Problem:** Container in restart loop

**Solutions:**

1. **Check logs:**
```bash
docker logs kasa-monitor --tail 100
```

2. **Verify image:**
```bash
docker pull xante8088/kasa-monitor:latest
```

3. **Check disk space:**
```bash
df -h
docker system prune
```

### Cannot access web interface

**Problem:** http://localhost:3000 doesn't work

**Solutions:**

1. **Check container status:**
```bash
docker ps
# Should show kasa-monitor running
```

2. **Verify port mapping:**
```bash
docker port kasa-monitor
# Should show 3000/tcp -> 0.0.0.0:3000
```

3. **Test from container:**
```bash
docker exec kasa-monitor curl http://localhost:3000
```

4. **Check firewall:**
```bash
sudo ufw status | grep 3000
```

### Volume permission errors

**Problem:** Cannot write to volumes

**Solution:**
```bash
# Fix ownership
docker exec -u root kasa-monitor chown -R appuser:appuser /app/data

# Or recreate with correct permissions
docker-compose down
docker volume rm kasa_data
docker-compose up -d
```

## Network Issues

### Container has no internet

**Problem:** Container cannot reach external services

**Solutions:**

1. **Check DNS:**
```bash
docker exec kasa-monitor nslookup google.com
```

2. **Set custom DNS:**
```yaml
services:
  kasa-monitor:
    dns:
      - 8.8.8.8
      - 8.8.4.4
```

3. **Check proxy settings:**
```bash
docker exec kasa-monitor env | grep -i proxy
```

### Cannot reach devices from container

**Problem:** Container cannot ping devices

**Solutions:**

1. **Bridge mode - use host gateway:**
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

2. **Check routing:**
```bash
docker exec kasa-monitor ip route
```

3. **Try host network mode:**
```yaml
network_mode: host
```

## Database Issues

### Database locked

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Restart container
docker restart kasa-monitor

# If persists, check for locks
docker exec kasa-monitor fuser /app/data/kasa_monitor.db
```

### Database corruption

**Error:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution:**
```bash
# Backup corrupted database
docker exec kasa-monitor cp /app/data/kasa_monitor.db /app/data/backup.db

# Attempt repair
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db ".recover" | \
  sqlite3 /app/data/recovered.db

# Replace if successful
docker exec kasa-monitor mv /app/data/recovered.db /app/data/kasa_monitor.db
```

## Quick Fixes

### Complete Reset

```bash
# Nuclear option - full reset
docker-compose down
docker volume rm kasa_data kasa_logs
docker rmi xante8088/kasa-monitor
docker-compose up -d
```

### Update Everything

```bash
# Update image and restart
docker-compose pull
docker-compose down
docker-compose up -d
```

### Debug Mode

```yaml
# Enable debug logging
environment:
  - LOG_LEVEL=DEBUG
  - PYTHONUNBUFFERED=1
```

## Getting More Help

If these solutions don't work:

1. **Check logs thoroughly:**
```bash
docker logs kasa-monitor --tail 200 > debug.log
```

2. **Search existing issues:**
- [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)

3. **Create detailed bug report:**
- Describe problem
- Include error messages
- List steps to reproduce
- Attach debug.log

4. **Ask community:**
- [GitHub Discussions](https://github.com/xante8088/kasa-monitor/discussions)

## Related Pages

- [FAQ](FAQ) - Frequently asked questions
- [Installation](Installation) - Setup guide
- [Network Configuration](Network-Configuration) - Network setup
- [Docker Issues](Docker-Issues) - Docker-specific problems

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added