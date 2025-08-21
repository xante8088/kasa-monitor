# Docker Deployment

Complete guide for deploying Kasa Monitor with Docker in production environments.

## Deployment Overview

```
┌────────────────────────────────────┐
│     Production Architecture        │
├────────────────────────────────────┤
│  Load Balancer (Nginx/Traefik)     │
│           ↓                        │
│  Kasa Monitor Container            │
│           ↓                        │
│  Database (SQLite/InfluxDB)        │
│           ↓                        │
│  Persistent Volumes                │
└────────────────────────────────────┘
```

## Quick Deployment

### Single Command Deploy

```bash
# Production deployment
docker run -d \
  --name kasa-monitor \
  --restart unless-stopped \
  --network host \
  -v kasa_data:/app/data \
  -v kasa_logs:/app/logs \
  -e NODE_ENV=production \
  -e TZ=America/New_York \
  xante8088/kasa-monitor:latest
```

### Docker Compose Deploy

```bash
# Download production compose file
curl -O https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.yml

# Deploy
docker-compose up -d

# Check status
docker-compose ps
```

## Production Configuration

### docker-compose.production.yml

```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:v1.0.0  # Use specific version
    container_name: kasa-monitor
    restart: unless-stopped
    
    # Network configuration
    networks:
      - frontend
      - backend
    
    # Port mapping
    ports:
      - "127.0.0.1:3000:3000"  # Localhost only
      - "127.0.0.1:5272:5272"
    
    # Volumes
    volumes:
      - kasa_data:/app/data
      - kasa_logs:/app/logs
      - ./config:/app/config:ro  # Config files
      - /etc/localtime:/etc/localtime:ro  # Sync time
    
    # Environment
    env_file:
      - .env.production
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=info
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}  # Required for production
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
      
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5272/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    
    # Security
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    depends_on:
      - redis
      - influxdb

  # Redis for caching/sessions
  redis:
    image: redis:7-alpine
    container_name: kasa-redis
    restart: unless-stopped
    networks:
      - backend
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    deploy:
      resources:
        limits:
          memory: 256M

  # InfluxDB for time-series data
  influxdb:
    image: influxdb:2.7-alpine
    container_name: kasa-influxdb
    restart: unless-stopped
    networks:
      - backend
    volumes:
      - influxdb_data:/var/lib/influxdb2
      - influxdb_config:/etc/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=${DOCKER_INFLUXDB_INIT_USERNAME}
      - DOCKER_INFLUXDB_INIT_PASSWORD=${DOCKER_INFLUXDB_INIT_PASSWORD}
      - DOCKER_INFLUXDB_INIT_ORG=${DOCKER_INFLUXDB_INIT_ORG:-kasa-monitor}
      - DOCKER_INFLUXDB_INIT_BUCKET=${DOCKER_INFLUXDB_INIT_BUCKET:-device-data}
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}
      - DOCKER_INFLUXDB_INIT_RETENTION=90d
    deploy:
      resources:
        limits:
          memory: 1G

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: kasa-nginx
    restart: unless-stopped
    networks:
      - frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx_cache:/var/cache/nginx
    depends_on:
      - kasa-monitor

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

volumes:
  kasa_data:
    driver: local
  kasa_logs:
    driver: local
  redis_data:
    driver: local
  influxdb_data:
    driver: local
  influxdb_config:
    driver: local
  nginx_cache:
    driver: local
```

### Environment Configuration

**.env.production:**
```bash
# Application
NODE_ENV=production
LOG_LEVEL=info
TZ=America/New_York

# Database
SQLITE_PATH=/app/data/kasa_monitor.db
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_SCHEDULE="0 2 * * *"

# InfluxDB (Use environment variables, not hardcoded values)
INFLUXDB_URL=http://influxdb:8086
DOCKER_INFLUXDB_INIT_USERNAME=admin
DOCKER_INFLUXDB_INIT_PASSWORD=$(openssl rand -base64 24)  # Generate secure password
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=$(openssl rand -hex 32)  # Generate secure token
DOCKER_INFLUXDB_INIT_ORG=kasa-monitor
DOCKER_INFLUXDB_INIT_BUCKET=device-data

# Redis
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=

# Security (CRITICAL - Generate secure values for production)
JWT_SECRET_KEY=$(openssl rand -base64 32)  # Generate secure key
SESSION_SECRET=$(openssl rand -base64 32)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# File Upload Security
MAX_UPLOAD_SIZE_MB=10
ALLOWED_UPLOAD_EXTENSIONS=.zip,.py,.json
REQUIRE_PLUGIN_SIGNATURES=true
UPLOAD_QUARANTINE_DIR=/app/quarantine

# Performance
POLLING_INTERVAL=60
DATA_RETENTION_DAYS=365
CACHE_TTL=300

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Deployment Strategies

### Blue-Green Deployment

```bash
#!/bin/bash
# Blue-green deployment script

# Deploy green (new version)
docker-compose -f docker-compose.green.yml up -d

# Health check
for i in {1..30}; do
  if curl -f http://localhost:3001/health; then
    echo "Green deployment healthy"
    break
  fi
  sleep 2
done

# Switch traffic
docker-compose -f docker-compose.blue.yml down
mv docker-compose.green.yml docker-compose.blue.yml

echo "Deployment complete"
```

### Rolling Update

```yaml
# Docker Swarm rolling update
services:
  kasa-monitor:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      rollback_config:
        parallelism: 1
        delay: 10s
```

### Canary Deployment

```nginx
# Nginx canary routing
upstream kasa_stable {
    server kasa-stable:3000 weight=9;
}

upstream kasa_canary {
    server kasa-canary:3000 weight=1;
}

server {
    location / {
        proxy_pass http://kasa_stable;
        # 10% traffic to canary
        if ($cookie_canary = "1") {
            proxy_pass http://kasa_canary;
        }
    }
}
```

## High Availability

### Docker Swarm Setup

```bash
# Initialize swarm
docker swarm init --advertise-addr 192.168.1.100

# Join workers
docker swarm join --token SWMTKN-1-xxx 192.168.1.100:2377

# Deploy stack
docker stack deploy -c docker-stack.yml kasa-monitor
```

**docker-stack.yml:**
```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.role == worker
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    networks:
      - kasa-network
    volumes:
      - kasa_data:/app/data
    configs:
      - source: kasa_config
        target: /app/config/production.yml

networks:
  kasa-network:
    driver: overlay
    attachable: true

volumes:
  kasa_data:
    driver: local

configs:
  kasa_config:
    external: true
```

### Kubernetes Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kasa-monitor
  namespace: smart-home
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kasa-monitor
  template:
    metadata:
      labels:
        app: kasa-monitor
    spec:
      containers:
      - name: kasa-monitor
        image: xante8088/kasa-monitor:v1.0.0
        ports:
        - containerPort: 3000
        - containerPort: 5272
        env:
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5272
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5272
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: kasa-data-pvc
```

## Reverse Proxy Setup

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/kasa-monitor
server {
    listen 80;
    server_name kasa.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name kasa.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/kasa.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/kasa.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Proxy Configuration
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api {
        proxy_pass http://localhost:5272;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support
    location /ws {
        proxy_pass http://localhost:5272;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Traefik Configuration

```yaml
# docker-compose with Traefik
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
    networks:
      - web

  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kasa.rule=Host(`kasa.yourdomain.com`)"
      - "traefik.http.routers.kasa.entrypoints=websecure"
      - "traefik.http.routers.kasa.tls.certresolver=letsencrypt"
      - "traefik.http.services.kasa.loadbalancer.server.port=3000"
    networks:
      - web
```

## Monitoring

### Health Checks

```python
# Health check endpoint
@app.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "database": check_database(),
        "redis": check_redis(),
        "influxdb": check_influxdb(),
        "timestamp": datetime.utcnow()
    }
    
    if not all([checks["database"], checks["redis"]]):
        return JSONResponse(status_code=503, content=checks)
    
    return checks
```

### Prometheus Metrics

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'kasa-monitor'
    static_configs:
      - targets: ['kasa-monitor:9090']
    metrics_path: /metrics
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Kasa Monitor Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Device Count",
        "targets": [
          {
            "expr": "kasa_devices_total"
          }
        ]
      }
    ]
  }
}
```

## Backup & Restore

### Automated Backups

```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR="/backups/kasa-monitor"
DATE=$(date +%Y%m%d-%H%M%S)

# Backup database
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db ".backup /tmp/backup.db"
docker cp kasa-monitor:/tmp/backup.db $BACKUP_DIR/db-$DATE.db

# Backup volumes
docker run --rm \
  -v kasa_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/data-$DATE.tar.gz -C /data .

# Keep last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Restore Procedure

```bash
# Stop container
docker-compose down

# Restore database
docker run --rm \
  -v kasa_data:/data \
  -v ./backups:/backup \
  alpine sh -c "cd /data && tar xzf /backup/data-20240115.tar.gz"

# Start container
docker-compose up -d
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs kasa-monitor --tail 100

# Check resources
docker system df
docker system prune -a

# Verify image
docker pull xante8088/kasa-monitor:latest
```

### Performance Issues

```bash
# Monitor resources
docker stats kasa-monitor

# Check limits
docker inspect kasa-monitor | grep -A 10 "Resources"

# Adjust limits
docker update --memory=4g --cpus=4 kasa-monitor
```

### Network Issues

```bash
# Test connectivity
docker exec kasa-monitor ping 8.8.8.8
docker exec kasa-monitor nslookup google.com

# Check networks
docker network ls
docker network inspect bridge
```

## Best Practices

### Security
- Use specific version tags
- Run as non-root user
- Enable read-only filesystem
- Use secrets management
- Regular security scanning

### Performance
- Set resource limits
- Use caching (Redis)
- Optimize images
- Monitor metrics
- Regular maintenance

### Reliability
- Health checks
- Automatic restarts
- Backup strategy
- Monitoring alerts
- Disaster recovery plan

## Related Pages

- [Installation](Installation) - Initial setup
- [Network Configuration](Network-Configuration) - Network modes
- [Security Guide](Security-Guide) - Security hardening
- [Backup & Recovery](Backup-Recovery) - Data protection
- [Performance Tuning](Performance-Tuning) - Optimization

## Security Hardening

### Critical Security Configuration

**1. JWT Secret Management:**
```bash
# Generate secure JWT secret (required for production)
export JWT_SECRET_KEY=$(openssl rand -base64 32)
echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}" >> .env.production

# The application uses jwt_secret_manager.py for:
# - Secure key storage with 600 permissions
# - Key rotation support
# - Backward compatibility during rotation
```

**2. CORS Configuration:**
```bash
# Configure allowed origins (no wildcards in production)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
ENVIRONMENT=production  # Enforces strict CORS checking
```

**3. Database Credentials:**
```bash
# Generate secure InfluxDB credentials
export DOCKER_INFLUXDB_INIT_PASSWORD=$(openssl rand -base64 24)
export DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=$(openssl rand -hex 32)

# Never hardcode credentials in docker-compose.yml
# Always use environment variables or Docker secrets
```

**4. File Upload Security:**
```yaml
environment:
  - MAX_UPLOAD_SIZE_MB=10
  - ALLOWED_UPLOAD_EXTENSIONS=.zip,.py,.json
  - REQUIRE_PLUGIN_SIGNATURES=true
  - UPLOAD_QUARANTINE_DIR=/app/quarantine
```

### Docker Secrets Integration

```yaml
# docker-compose with secrets
services:
  kasa-monitor:
    secrets:
      - jwt_secret
      - db_password
      - influx_token
    environment:
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - INFLUX_TOKEN_FILE=/run/secrets/influx_token

secrets:
  jwt_secret:
    external: true
  db_password:
    external: true
  influx_token:
    external: true
```

**Create secrets:**
```bash
# Create Docker secrets
echo "$(openssl rand -base64 32)" | docker secret create jwt_secret -
echo "$(openssl rand -base64 24)" | docker secret create db_password -
echo "$(openssl rand -hex 32)" | docker secret create influx_token -
```

### Security Checklist

- [ ] JWT_SECRET_KEY configured with secure 256-bit key
- [ ] CORS_ALLOWED_ORIGINS restricted to your domains
- [ ] Database passwords use environment variables
- [ ] File upload restrictions configured
- [ ] Container running with security_opt: no-new-privileges
- [ ] Volumes mounted as read-only where possible
- [ ] Network isolation configured
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Regular security updates applied

---

**Document Version:** 1.1.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Added security hardening section with JWT, CORS, database credentials, and file upload security configurations