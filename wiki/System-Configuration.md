# System Configuration

Complete guide for configuring and customizing Kasa Monitor system settings.

## Configuration Overview

```
┌─────────────────────────────────────┐
│     Configuration Hierarchy         │
├─────────────────────────────────────┤
│  1. Environment Variables           │
│  2. Configuration Files             │
│  3. Database Settings               │
│  4. Runtime Configuration           │
│  5. User Preferences                │
└─────────────────────────────────────┘
```

## Quick Configuration

### Essential Settings

```bash
# .env file
NODE_ENV=production
TZ=America/New_York
POLLING_INTERVAL=60
DATA_RETENTION_DAYS=365
LOG_LEVEL=info
```

### Docker Environment

```yaml
# docker-compose.yml
environment:
  - NODE_ENV=production
  - TZ=America/New_York
  - POLLING_INTERVAL=60
  - DATABASE_PATH=/app/data/kasa_monitor.db
  - LOG_LEVEL=info
```

## Environment Variables

### Core Settings

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `NODE_ENV` | Application environment | development | development, production, test |
| `TZ` | System timezone | UTC | Any valid timezone |
| `LOG_LEVEL` | Logging verbosity | info | debug, info, warn, error |
| `PORT` | Frontend port | 3000 | Any available port |
| `API_PORT` | Backend API port | 8000 | Any available port |

### Database Configuration

```bash
# SQLite
SQLITE_PATH=/app/data/kasa_monitor.db
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_SCHEDULE="0 2 * * *"
DATABASE_BACKUP_RETENTION_DAYS=30

# InfluxDB (Optional)
INFLUXDB_ENABLED=false
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-secure-token
INFLUXDB_ORG=kasa-monitor
INFLUXDB_BUCKET=device-data
INFLUXDB_RETENTION_DAYS=90
```

### Security Settings

```bash
# Authentication
JWT_SECRET_KEY=your-very-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Session
SESSION_SECRET=another-random-string
SESSION_TIMEOUT_MINUTES=30
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# CORS
ALLOWED_ORIGINS=https://yourdomain.com
ALLOWED_METHODS=GET,POST,PUT,DELETE
ALLOWED_HEADERS=Content-Type,Authorization
```

### Performance Settings

```bash
# Polling
POLLING_INTERVAL=60  # Seconds
POLLING_THREADS=4
POLLING_BATCH_SIZE=10
POLLING_TIMEOUT=10

# Caching
CACHE_ENABLED=true
CACHE_TTL=300  # Seconds
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=

# Data Management
DATA_RETENTION_DAYS=365
DATA_AGGREGATION_ENABLED=true
DATA_COMPRESSION_ENABLED=true
```

### Network Configuration

```bash
# Device Discovery
DISCOVERY_ENABLED=true
DISCOVERY_BROADCAST_ADDRESS=255.255.255.255
DISCOVERY_PORT=9999
DISCOVERY_TIMEOUT=5
DISCOVERY_INTERVAL=3600

# Network Ranges
ALLOWED_SUBNETS=192.168.1.0/24,10.0.0.0/8
BLOCKED_IPS=
```

## Configuration Files

### Main Configuration

**config/production.yml:**
```yaml
app:
  name: Kasa Monitor
  version: 1.0.0
  environment: production
  debug: false

server:
  host: 0.0.0.0
  port: 8000
  workers: 4
  timeout: 30

database:
  type: sqlite
  path: /app/data/kasa_monitor.db
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30

influxdb:
  enabled: false
  url: http://influxdb:8086
  token: ${INFLUXDB_TOKEN}
  org: kasa-monitor
  bucket: device-data

redis:
  enabled: true
  url: redis://redis:6379
  password: 
  db: 0
  decode_responses: true

logging:
  level: INFO
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: /app/logs/kasa-monitor.log
  max_bytes: 10485760  # 10MB
  backup_count: 5

security:
  jwt_secret: ${JWT_SECRET_KEY}
  algorithm: HS256
  access_token_expire: 30  # minutes
  refresh_token_expire: 7  # days
  password_min_length: 12
  password_require_special: true

monitoring:
  metrics_enabled: true
  metrics_port: 9090
  health_check_interval: 30
  alerting_enabled: true

features:
  auto_discovery: true
  energy_monitoring: true
  cost_calculation: true
  scheduling: true
  notifications: true
  api_enabled: true
```

### Device Configuration

**config/devices.yml:**
```yaml
defaults:
  polling_interval: 60
  timeout: 10
  retry_count: 3
  retry_delay: 5

device_types:
  HS110:
    has_energy_meter: true
    max_power: 1800
    calibration_factor: 1.0
  
  HS100:
    has_energy_meter: false
    max_power: 1800
  
  KP115:
    has_energy_meter: true
    max_power: 1800
    calibration_factor: 1.0

groups:
  Living Room:
    polling_interval: 30
    alert_threshold: 100
  
  Bedroom:
    polling_interval: 120
    alert_threshold: 50

calibration:
  voltage_correction: 1.0
  current_correction: 1.0
  power_factor_correction: 1.0
```

### Rate Configuration

**config/electricity_rates.yml:**
```yaml
default_rate:
  type: simple
  currency: USD
  rate_per_kwh: 0.12

time_of_use:
  enabled: false
  rates:
    peak:
      rate: 0.15
      hours: "14:00-20:00"
      days: ["mon", "tue", "wed", "thu", "fri"]
    off_peak:
      rate: 0.08
      hours: "20:00-14:00"
    weekend:
      rate: 0.10
      days: ["sat", "sun"]

tiered_rates:
  enabled: false
  tiers:
    - limit: 500
      rate: 0.10
    - limit: 1000
      rate: 0.12
    - limit: null
      rate: 0.15

seasonal_rates:
  enabled: false
  seasons:
    summer:
      months: [6, 7, 8]
      rate: 0.14
    winter:
      months: [12, 1, 2]
      rate: 0.11
    standard:
      rate: 0.12
```

## Database Settings

### System Configuration Table

```sql
-- View current settings
SELECT * FROM system_config;

-- Update setting
UPDATE system_config 
SET value = '30' 
WHERE key = 'polling_interval';

-- Add new setting
INSERT INTO system_config (key, value, type, description)
VALUES ('custom_setting', 'value', 'string', 'Description');
```

### Common Settings

```sql
-- Core settings
INSERT OR REPLACE INTO system_config VALUES
  ('polling_interval', '60', 'integer', 'Device polling interval in seconds'),
  ('data_retention_days', '365', 'integer', 'Days to retain detailed data'),
  ('summary_retention_days', '1825', 'integer', 'Days to retain summary data'),
  ('timezone', 'America/New_York', 'string', 'System timezone'),
  ('date_format', 'YYYY-MM-DD', 'string', 'Date display format'),
  ('time_format', 'HH:mm:ss', 'string', 'Time display format'),
  ('currency', 'USD', 'string', 'Currency for cost calculations'),
  ('theme', 'auto', 'string', 'UI theme (light/dark/auto)');

-- Feature flags
INSERT OR REPLACE INTO system_config VALUES
  ('auto_discovery_enabled', 'true', 'boolean', 'Enable automatic device discovery'),
  ('energy_monitoring_enabled', 'true', 'boolean', 'Enable energy monitoring'),
  ('cost_calculation_enabled', 'true', 'boolean', 'Enable cost calculations'),
  ('scheduling_enabled', 'true', 'boolean', 'Enable device scheduling'),
  ('notifications_enabled', 'true', 'boolean', 'Enable notifications'),
  ('api_enabled', 'true', 'boolean', 'Enable API access');

-- Performance settings
INSERT OR REPLACE INTO system_config VALUES
  ('max_concurrent_polls', '10', 'integer', 'Maximum concurrent device polls'),
  ('poll_timeout', '10', 'integer', 'Device poll timeout in seconds'),
  ('cache_ttl', '300', 'integer', 'Cache time-to-live in seconds'),
  ('batch_size', '100', 'integer', 'Batch processing size');
```

## Runtime Configuration

### Dynamic Settings

```python
# Get runtime config
@app.get("/api/config")
async def get_config():
    config = {
        "polling_interval": int(os.getenv("POLLING_INTERVAL", 60)),
        "timezone": os.getenv("TZ", "UTC"),
        "features": {
            "discovery": os.getenv("DISCOVERY_ENABLED", "true") == "true",
            "scheduling": os.getenv("SCHEDULING_ENABLED", "true") == "true"
        }
    }
    return config

# Update runtime config
@app.post("/api/config")
async def update_config(settings: dict):
    for key, value in settings.items():
        db.execute(
            "UPDATE system_config SET value = ? WHERE key = ?",
            (value, key)
        )
    # Reload configuration
    reload_config()
```

### Feature Toggles

```python
FEATURE_FLAGS = {
    "energy_monitoring": True,
    "cost_calculation": True,
    "scheduling": True,
    "notifications": True,
    "advanced_analytics": False,
    "cloud_sync": False
}

def is_feature_enabled(feature: str) -> bool:
    return FEATURE_FLAGS.get(feature, False)

# Usage
if is_feature_enabled("scheduling"):
    schedule_device_tasks()
```

## User Preferences

### User-Specific Settings

```json
{
  "theme": "dark",
  "language": "en",
  "timezone": "America/New_York",
  "date_format": "MM/DD/YYYY",
  "time_format": "12h",
  "notifications": {
    "email": true,
    "push": false,
    "sms": false
  },
  "dashboard": {
    "refresh_interval": 30,
    "default_view": "grid",
    "show_costs": true,
    "show_graphs": true
  },
  "devices": {
    "sort_by": "name",
    "group_by": "location",
    "show_offline": true
  }
}
```

### Preference API

```python
# Get user preferences
@app.get("/api/users/me/preferences")
async def get_preferences(user: User = Depends(get_current_user)):
    return json.loads(user.settings or "{}")

# Update preferences
@app.patch("/api/users/me/preferences")
async def update_preferences(
    preferences: dict,
    user: User = Depends(get_current_user)
):
    db.execute(
        "UPDATE users SET settings = ? WHERE id = ?",
        (json.dumps(preferences), user.id)
    )
```

## Configuration Management

### Backup Configuration

```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR="/backups/config"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Backup all config files
tar czf $BACKUP_DIR/config-$TIMESTAMP.tar.gz \
  /app/config/*.yml \
  /app/.env \
  /app/data/system_config.sql

# Export database settings
sqlite3 /app/data/kasa_monitor.db \
  "SELECT * FROM system_config" > $BACKUP_DIR/settings-$TIMESTAMP.csv
```

### Restore Configuration

```bash
#!/bin/bash
# restore-config.sh

BACKUP_FILE=$1

# Extract config files
tar xzf $BACKUP_FILE -C /

# Restart application
docker-compose restart
```

### Configuration Validation

```python
import yaml
import jsonschema

def validate_config(config_file):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    schema = {
        "type": "object",
        "required": ["app", "server", "database"],
        "properties": {
            "app": {
                "type": "object",
                "required": ["name", "version", "environment"]
            },
            "server": {
                "type": "object",
                "required": ["host", "port"]
            }
        }
    }
    
    jsonschema.validate(config, schema)
    return True
```

## Advanced Configuration

### Custom Modules

```python
# config/custom_modules.py

CUSTOM_MODULES = {
    "authentication": "custom_auth.CustomAuthProvider",
    "discovery": "custom_discovery.CustomDiscovery",
    "notifications": "custom_notify.CustomNotifier"
}

# Load custom module
def load_custom_module(module_type):
    module_path = CUSTOM_MODULES.get(module_type)
    if module_path:
        module_name, class_name = module_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)()
```

### Plugin System

```python
# config/plugins.yml
plugins:
  - name: weather_integration
    enabled: true
    config:
      api_key: ${WEATHER_API_KEY}
      update_interval: 3600
  
  - name: smart_scheduling
    enabled: false
    config:
      ml_model: /models/scheduling.pkl
  
  - name: voice_control
    enabled: false
    config:
      provider: alexa
```

### Environment-Specific Overrides

```python
# Load environment-specific config
def load_config():
    env = os.getenv('NODE_ENV', 'development')
    
    # Base config
    with open('config/base.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Environment override
    env_file = f'config/{env}.yml'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_config = yaml.safe_load(f)
            config = merge_configs(config, env_config)
    
    return config
```

## Configuration Examples

### High-Performance Setup

```yaml
# High device count configuration
server:
  workers: 8
  thread_pool: 16

database:
  pool_size: 20
  max_overflow: 40

polling:
  interval: 30
  threads: 8
  batch_size: 50

cache:
  enabled: true
  ttl: 600
  size: 1000
```

### Energy-Saving Setup

```yaml
# Low-power configuration
polling:
  interval: 300  # 5 minutes
  threads: 2

features:
  auto_discovery: false
  real_time_updates: false

database:
  pool_size: 2
  compression: true
```

### Development Setup

```yaml
# Development configuration
app:
  debug: true
  reload: true

logging:
  level: DEBUG
  console: true

security:
  cors_enabled: true
  allowed_origins: "*"
```

## Troubleshooting

### Configuration Issues

**Config not loading:**
```bash
# Check file permissions
ls -la /app/config/

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('/app/config/production.yml'))"

# Check environment variables
docker exec kasa-monitor env | grep -E "NODE_ENV|TZ|LOG_LEVEL"
```

**Settings not applying:**
```bash
# Restart application
docker-compose restart

# Clear cache
docker exec kasa-monitor redis-cli FLUSHALL

# Check database
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "SELECT * FROM system_config WHERE key='polling_interval'"
```

## Best Practices

1. **Use Environment Variables** for sensitive data
2. **Version Control** configuration files
3. **Validate** configurations before applying
4. **Document** custom settings
5. **Test** configuration changes in staging
6. **Backup** before major changes
7. **Monitor** after configuration updates

## Related Pages

- [Installation](Installation) - Initial configuration
- [Docker Deployment](Docker-Deployment) - Container configuration
- [Security Guide](Security-Guide) - Security settings
- [Performance Tuning](Performance-Tuning) - Performance configuration
- [Backup & Recovery](Backup-Recovery) - Configuration backup