# Docker Volumes Update - Named Volumes Migration

## Summary of Changes

All Docker Compose files have been updated to use **named volumes** instead of bind mounts for better portability, security, and Docker best practices.

## What Changed

### Before (Bind Mounts)
```yaml
volumes:
  - ./data:/app/data     # Bind mount to local directory
  - ./logs:/app/logs     # Bind mount to local directory
```

### After (Named Volumes)
```yaml
volumes:
  - kasa_data:/app/data  # Named volume managed by Docker
  - kasa_logs:/app/logs  # Named volume managed by Docker
```

## Files Updated

✅ `/docker-compose.yml` - Main compose file
✅ `/docker-compose.sample.yml` - Sample configuration
✅ `/docker-compose.prod.yml` - Production configuration
✅ `/docker-compose.dynamic.yml` - Dynamic network configuration
✅ `/QUICKSTART-DOCKER.md` - Updated documentation
✅ Network helper script remains compatible

## Benefits of Named Volumes

1. **Portability**: Works consistently across different systems
2. **Docker Management**: Docker handles volume creation and permissions
3. **Performance**: Better I/O performance, especially on macOS/Windows
4. **Backup/Restore**: Easier volume management with Docker commands
5. **Security**: Better isolation from host filesystem
6. **No Directory Creation**: No need to create local directories first

## Volume Management Commands

### View Volumes
```bash
# List all Kasa volumes
docker volume ls | grep kasa

# Inspect a volume
docker volume inspect kasa_data
```

### Backup Data
```bash
# Backup data volume
docker run --rm \
  -v kasa_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/kasa-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup logs volume
docker run --rm \
  -v kasa_logs:/logs \
  -v $(pwd):/backup \
  alpine tar czf /backup/kasa-logs-$(date +%Y%m%d).tar.gz -C /logs .
```

### Restore Data
```bash
# Restore data volume
docker run --rm \
  -v kasa_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/kasa-backup.tar.gz -C /data

# Restore logs volume
docker run --rm \
  -v kasa_logs:/logs \
  -v $(pwd):/backup \
  alpine tar xzf /backup/kasa-logs.tar.gz -C /logs
```

### Clean Up
```bash
# Stop containers and remove volumes (CAUTION: Deletes all data!)
docker-compose down -v

# Remove specific volume
docker volume rm kasa_data

# Prune unused volumes
docker volume prune
```

## Migration from Bind Mounts

If you have existing data in local directories (`./data`, `./logs`), migrate to named volumes:

### Option 1: Copy Data to Named Volumes
```bash
# Stop containers
docker-compose down

# Create named volumes and copy data
docker run --rm \
  -v $(pwd)/data:/source:ro \
  -v kasa_data:/destination \
  alpine cp -av /source/. /destination/

docker run --rm \
  -v $(pwd)/logs:/source:ro \
  -v kasa_logs:/destination \
  alpine cp -av /source/. /destination/

# Start with new configuration
docker-compose up -d
```

### Option 2: Fresh Start
```bash
# Stop and remove old containers
docker-compose down

# Start with new named volumes (fresh data)
docker-compose up -d
```

## Network Auto-Detection

The network helper script (`docker-network-helper.sh`) remains fully compatible with named volumes:

```bash
# Generate docker-compose.yml with auto-detected network
./docker-network-helper.sh --generate

# Start with named volumes and unique network
docker-compose up -d
```

## Volume Locations

Named volumes are stored in Docker's volume directory:
- **Linux**: `/var/lib/docker/volumes/`
- **macOS**: `~/Library/Containers/com.docker.docker/Data/vms/0/data/docker/volumes/`
- **Windows**: `C:\ProgramData\docker\volumes\`

Volume names:
- `kasa_data` - Application database and data files
- `kasa_logs` - Application logs
- `kasa_ssl` - SSL certificates (optional)
- `kasa_config` - Custom configuration (optional)

## Troubleshooting

### "Volume not found"
```bash
# Docker will create volumes automatically on first run
docker-compose up -d
```

### "Permission denied"
```bash
# Named volumes handle permissions automatically
# If issues persist, recreate volume:
docker-compose down -v
docker-compose up -d
```

### View Volume Contents
```bash
# Browse volume contents
docker run --rm -it -v kasa_data:/data alpine sh
cd /data
ls -la
```

### Export Volume for Debugging
```bash
# Copy volume contents to local directory
docker run --rm \
  -v kasa_data:/source:ro \
  -v $(pwd)/export:/destination \
  alpine cp -av /source/. /destination/
```

## Best Practices

1. **Regular Backups**: Schedule automated backups of named volumes
2. **Volume Labels**: Use labels to organize volumes by project
3. **Separate Volumes**: Keep data, logs, and config in separate volumes
4. **Documentation**: Document volume contents and backup procedures
5. **Testing**: Test restore procedures regularly

## Notes

- Named volumes persist even when containers are removed
- Use `docker-compose down -v` carefully - it deletes all volume data
- Volumes are project-namespaced (prefix matches compose project name)
- Default project name is the directory name where compose file resides