# Database Schema

Complete documentation of the Kasa Monitor database structure for both SQLite and InfluxDB.

## Database Overview

Kasa Monitor uses a dual-database approach:

- **SQLite**: Configuration, users, device metadata
- **InfluxDB** (Optional): Time-series energy data

```
┌─────────────┐       ┌──────────────┐
│   SQLite    │       │   InfluxDB   │
├─────────────┤       ├──────────────┤
│ • Users     │       │ • Power data │
│ • Devices   │       │ • Energy     │
│ • Rates     │       │ • Costs      │
│ • Settings  │       │ • Metrics    │
└─────────────┘       └──────────────┘
```

## SQLite Schema

### Database Location

```
/app/data/kasa_monitor.db
```

### Table: users

Stores user accounts and authentication.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    settings JSON,
    
    CHECK (role IN ('admin', 'operator', 'viewer', 'guest'))
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

**Sample Data:**
```sql
INSERT INTO users VALUES (
    1,
    'admin',
    'admin@example.com',
    '$2b$12$hashed_password_here',
    'Administrator',
    'admin',
    1,
    '2024-01-01 10:00:00',
    '2024-01-15 14:30:00',
    '{"theme": "dark", "notifications": true}'
);
```

### Table: devices

Stores device information and metadata.

```sql
CREATE TABLE devices (
    device_ip TEXT PRIMARY KEY,
    device_name TEXT NOT NULL,
    device_alias TEXT,
    device_model TEXT,
    device_type TEXT,
    mac_address TEXT UNIQUE,
    firmware_version TEXT,
    hardware_version TEXT,
    is_active BOOLEAN DEFAULT 1,
    is_monitored BOOLEAN DEFAULT 1,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP,
    location TEXT,
    group_name TEXT,
    user_notes TEXT,
    config JSON,
    
    CHECK (device_type IN ('plug', 'switch', 'bulb', 'strip'))
);

CREATE INDEX idx_devices_active ON devices(is_active);
CREATE INDEX idx_devices_type ON devices(device_type);
CREATE INDEX idx_devices_group ON devices(group_name);
```

**Sample Data:**
```sql
INSERT INTO devices VALUES (
    '192.168.1.100',
    'HS110',
    'Living Room Lamp',
    'HS110(US)',
    'plug',
    'AA:BB:CC:DD:EE:FF',
    '1.5.6',
    '2.0',
    1,
    1,
    '2024-01-01 10:00:00',
    '2024-01-15 14:35:00',
    'Living Room',
    'Lighting',
    'Main floor lamp',
    '{"polling_interval": 60, "calibration": 1.0}'
);
```

### Table: readings

Stores energy consumption data (when not using InfluxDB).

```sql
CREATE TABLE readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_ip TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    power_w REAL,
    energy_kwh REAL,
    voltage_v REAL,
    current_a REAL,
    power_factor REAL,
    frequency_hz REAL,
    total_kwh REAL,
    is_on BOOLEAN,
    temperature_c REAL,
    
    FOREIGN KEY (device_ip) REFERENCES devices(device_ip)
);

CREATE INDEX idx_readings_device_time ON readings(device_ip, timestamp);
CREATE INDEX idx_readings_timestamp ON readings(timestamp);
```

**Sample Data:**
```sql
INSERT INTO readings VALUES (
    1,
    '192.168.1.100',
    '2024-01-15 14:30:00',
    45.2,
    0.045,
    120.1,
    0.38,
    0.99,
    60.0,
    125.6,
    1,
    NULL
);
```

### Table: daily_summaries

Aggregated daily statistics.

```sql
CREATE TABLE daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_ip TEXT NOT NULL,
    date DATE NOT NULL,
    total_kwh REAL,
    peak_power_w REAL,
    average_power_w REAL,
    min_power_w REAL,
    on_time_hours REAL,
    cost REAL,
    
    FOREIGN KEY (device_ip) REFERENCES devices(device_ip),
    UNIQUE(device_ip, date)
);

CREATE INDEX idx_daily_device_date ON daily_summaries(device_ip, date);
```

### Table: electricity_rates

Stores electricity rate configurations.

```sql
CREATE TABLE electricity_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rate_type TEXT NOT NULL,
    currency TEXT DEFAULT 'USD',
    rate_structure JSON NOT NULL,
    effective_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (rate_type IN ('simple', 'tou', 'tiered', 'seasonal'))
);
```

**Sample Rate Structures:**

```json
-- Simple Rate
{
    "rate_per_kwh": 0.12
}

-- Time-of-Use Rate
{
    "periods": [
        {
            "name": "peak",
            "rate": 0.15,
            "start_hour": 14,
            "end_hour": 20,
            "days": ["mon", "tue", "wed", "thu", "fri"]
        },
        {
            "name": "off_peak",
            "rate": 0.08,
            "start_hour": 20,
            "end_hour": 14
        }
    ]
}

-- Tiered Rate
{
    "tiers": [
        {"limit": 500, "rate": 0.10},
        {"limit": 1000, "rate": 0.12},
        {"limit": null, "rate": 0.15}
    ]
}
```

### Table: user_permissions

Maps users to specific permissions.

```sql
CREATE TABLE user_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    permission TEXT NOT NULL,
    granted_by INTEGER,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (granted_by) REFERENCES users(id),
    UNIQUE(user_id, permission)
);
```

### Table: system_config

Stores system-wide configuration.

```sql
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    type TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO system_config VALUES
    ('polling_interval', '60', 'integer', 'Seconds between device polls', CURRENT_TIMESTAMP),
    ('data_retention_days', '365', 'integer', 'Days to keep detailed data', CURRENT_TIMESTAMP),
    ('timezone', 'America/New_York', 'string', 'System timezone', CURRENT_TIMESTAMP);
```

### Table: audit_log

Tracks important system events.

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    details JSON,
    ip_address TEXT,
    
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_user ON audit_log(user_id);
```

## InfluxDB Schema

### Database Structure

```
Database: kasa_monitor
├── Bucket: device_data
│   ├── Measurement: power
│   ├── Measurement: energy
│   └── Measurement: costs
└── Bucket: system_metrics
    ├── Measurement: performance
    └── Measurement: api_calls
```

### Measurement: power

Real-time power consumption data.

```influxql
power,device_ip=192.168.1.100,device_name=Living\ Room,device_type=plug 
    current_w=45.2,
    voltage_v=120.1,
    current_a=0.38,
    power_factor=0.99,
    is_on=true
    1705330200000000000
```

**Fields:**
- `current_w`: Current power in watts (float)
- `voltage_v`: Voltage (float)
- `current_a`: Current in amperes (float)
- `power_factor`: Power factor 0-1 (float)
- `is_on`: Device state (boolean)

**Tags:**
- `device_ip`: Device IP address
- `device_name`: Device friendly name
- `device_type`: plug/switch/bulb/strip
- `location`: Room/zone
- `group`: Device group

### Measurement: energy

Cumulative energy consumption.

```influxql
energy,device_ip=192.168.1.100,period=daily 
    kwh=2.5,
    cost=0.30,
    on_hours=18.5
    1705330200000000000
```

**Fields:**
- `kwh`: Energy consumed (float)
- `cost`: Calculated cost (float)
- `on_hours`: Hours device was on (float)

**Tags:**
- `device_ip`: Device IP address
- `period`: hourly/daily/monthly

### Measurement: costs

Cost tracking and analysis.

```influxql
costs,device_ip=192.168.1.100,rate_type=tou,period=daily 
    total_cost=1.25,
    peak_cost=0.90,
    off_peak_cost=0.35,
    kwh_peak=6.0,
    kwh_off_peak=4.4
    1705330200000000000
```

## Database Operations

### Common Queries

**Get device status:**
```sql
SELECT d.*, 
       r.power_w, 
       r.is_on,
       r.timestamp as last_reading
FROM devices d
LEFT JOIN readings r ON d.device_ip = r.device_ip
WHERE r.timestamp = (
    SELECT MAX(timestamp) 
    FROM readings 
    WHERE device_ip = d.device_ip
);
```

**Calculate daily costs:**
```sql
SELECT 
    device_ip,
    DATE(timestamp) as date,
    SUM(energy_kwh) * 0.12 as cost
FROM readings
WHERE timestamp >= datetime('now', '-30 days')
GROUP BY device_ip, DATE(timestamp)
ORDER BY date DESC;
```

**Get user permissions:**
```sql
SELECT u.username, 
       u.role,
       GROUP_CONCAT(up.permission) as permissions
FROM users u
LEFT JOIN user_permissions up ON u.id = up.user_id
WHERE u.is_active = 1
GROUP BY u.id;
```

### Data Retention

**SQLite Cleanup:**
```sql
-- Delete old readings (keep summaries)
DELETE FROM readings 
WHERE timestamp < datetime('now', '-30 days');

-- Vacuum database
VACUUM;
```

**InfluxDB Retention Policy:**
```influxql
CREATE RETENTION POLICY "autogen" 
ON "kasa_monitor" 
DURATION 30d 
REPLICATION 1 
SHARD DURATION 1d 
DEFAULT;

CREATE RETENTION POLICY "long_term" 
ON "kasa_monitor" 
DURATION 365d 
REPLICATION 1;
```

### Continuous Queries

**InfluxDB Downsampling:**
```influxql
-- Hourly aggregation
CREATE CONTINUOUS QUERY "cq_hourly" 
ON "kasa_monitor" 
BEGIN
  SELECT mean("current_w") as power_w,
         sum("energy_kwh") as energy_kwh,
         mean("voltage_v") as voltage_v
  INTO "long_term"."hourly_power"
  FROM "power"
  GROUP BY time(1h), device_ip
END;

-- Daily aggregation
CREATE CONTINUOUS QUERY "cq_daily" 
ON "kasa_monitor" 
BEGIN
  SELECT sum("energy_kwh") as total_kwh,
         max("current_w") as peak_w,
         mean("current_w") as avg_w
  INTO "long_term"."daily_energy"
  FROM "power"
  GROUP BY time(1d), device_ip
END;
```

## Database Maintenance

### Backup Commands

**SQLite:**
```bash
# Online backup
sqlite3 /app/data/kasa_monitor.db ".backup /backup/kasa_monitor.db"

# SQL dump
sqlite3 /app/data/kasa_monitor.db .dump > backup.sql
```

**InfluxDB:**
```bash
# Backup
influx backup /backup/influxdb -t $INFLUX_TOKEN

# Restore
influx restore /backup/influxdb -t $INFLUX_TOKEN
```

### Performance Optimization

**SQLite:**
```sql
-- Analyze tables
ANALYZE;

-- Rebuild indexes
REINDEX;

-- Check integrity
PRAGMA integrity_check;

-- Optimize
PRAGMA optimize;
```

**InfluxDB:**
```bash
# Compact shards
influx-inspect buildtsi -datadir /var/lib/influxdb/data

# Verify data
influx-inspect verify-seriesfile
```

## Migration Scripts

### SQLite Schema Updates

```sql
-- Add new column
ALTER TABLE devices 
ADD COLUMN cloud_device_id TEXT;

-- Create migration table
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Data Migration

```python
# Migrate from SQLite to InfluxDB
import sqlite3
from influxdb_client import InfluxDBClient

# Connect to both databases
sqlite_conn = sqlite3.connect('/app/data/kasa_monitor.db')
influx_client = InfluxDBClient(url="http://localhost:8086", 
                               token="your-token")

# Read from SQLite
cursor = sqlite_conn.execute("""
    SELECT device_ip, timestamp, power_w, energy_kwh 
    FROM readings 
    WHERE timestamp >= datetime('now', '-7 days')
""")

# Write to InfluxDB
write_api = influx_client.write_api()
for row in cursor:
    point = {
        "measurement": "power",
        "tags": {"device_ip": row[0]},
        "time": row[1],
        "fields": {
            "current_w": row[2],
            "energy_kwh": row[3]
        }
    }
    write_api.write(bucket="device_data", record=point)
```

## Database Access

### Connection Strings

**SQLite:**
```python
import sqlite3
conn = sqlite3.connect('/app/data/kasa_monitor.db')
```

**InfluxDB:**
```python
from influxdb_client import InfluxDBClient
client = InfluxDBClient(
    url="http://localhost:8086",
    token="your-token",
    org="kasa-monitor"
)
```

### API Endpoints

```bash
# SQLite via API
curl http://localhost:8000/api/devices

# InfluxDB direct
curl -G http://localhost:8086/query \
  --data-urlencode "q=SELECT * FROM power WHERE time > now() - 1h"
```

## Related Pages

- [API Documentation](API-Documentation) - Database access via API
- [Backup & Recovery](Backup-Recovery) - Database backup procedures
- [Performance Tuning](Performance-Tuning) - Database optimization
- [Installation](Installation) - Initial database setup

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added