# Audit Logging

Comprehensive audit logging system for security, compliance, and operational monitoring in Kasa Monitor.

## Overview

Kasa Monitor includes a robust audit logging system that tracks all security events, system operations, and user activities. This system provides detailed logs for compliance, security monitoring, and troubleshooting.

```
┌─────────────────────────────────────┐
│         Audit Logging System       │
├─────────────────────────────────────┤
│  1. Security Events                 │
│  2. System Operations               │
│  3. User Activities                 │
│  4. Performance Monitoring          │
│  5. Error Tracking                  │
└─────────────────────────────────────┘
```

## Features

### ✅ **Implemented**
- **Security Event Logging** - Login, logout, authentication failures
- **System Operation Logging** - Backup operations, configuration changes
- **User Activity Tracking** - Device control, permission changes
- **Performance Monitoring** - API response times, threshold alerts
- **Error Logging** - System errors with detailed context
- **Database Storage** - SQLite-based audit log storage
- **File-based Logging** - Dual destination logging
- **Integrity Protection** - Checksums for log entries

## Configuration

### Basic Setup

```python
# Environment variables
AUDIT_LOGGING_ENABLED=true
AUDIT_LOG_LEVEL=INFO
AUDIT_LOG_DIR=./logs/audit
AUDIT_DB_PATH=./logs/audit/audit.db
```

### Database Configuration

```python
# Audit logger initialization
from audit_logging import AuditLogger, AuditSeverity

audit_logger = AuditLogger(
    db_path="audit.db",
    log_dir="./logs/audit"
)
```

## Event Types

### Security Events

```python
class AuditEventType(Enum):
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_TIMEOUT = "session_timeout"
    
    # Authorization
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGED = "role_changed"
    
    # Security
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    PASSWORD_CHANGED = "password_changed"
```

### System Operations

```python
    # System Events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"
    
    # Backup Operations
    SYSTEM_BACKUP_CREATED = "system_backup_created"
    SYSTEM_BACKUP_RESTORED = "system_backup_restored"
    
    # Configuration
    CONFIG_CHANGED = "config_changed"
```

### User Activities

```python
    # Device Management
    DEVICE_ADDED = "device_added"
    DEVICE_REMOVED = "device_removed"
    DEVICE_CONTROLLED = "device_controlled"
    
    # Data Operations
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
```

## Severity Levels

```python
class AuditSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

## API Endpoints

### Get Audit Logs

```http
GET /api/audit/logs?start_date=2024-01-01&end_date=2024-01-31&severity=ERROR
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "event_type": "login_failure",
      "severity": "warning",
      "user_id": null,
      "username": "unknown",
      "ip_address": "192.168.1.100",
      "action": "Failed login attempt",
      "details": {
        "username_attempted": "admin",
        "failure_reason": "invalid_password"
      },
      "success": false
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

### Export Audit Logs

```http
GET /api/audit/export?format=csv&start_date=2024-01-01
Authorization: Bearer {admin_token}
```

**Supported Formats:**
- CSV
- JSON
- PDF (summary report)

## Security Features

### Integrity Protection

```python
# Each log entry includes integrity checksum
log_entry = {
    "id": 123,
    "timestamp": "2024-01-15T10:30:00Z",
    "event_type": "login_success",
    # ... other fields
    "checksum": "sha256:abc123..."
}
```

### Tamper Detection

```python
# Verify log integrity
@router.get("/api/audit/verify")
async def verify_audit_logs():
    """Verify audit log integrity."""
    results = await audit_logger.verify_integrity()
    return {
        "verified": results["all_valid"],
        "total_entries": results["total"],
        "invalid_entries": results["invalid"],
        "corruption_detected": len(results["invalid"]) > 0
    }
```

## Event Examples

### Login Success

```json
{
  "event_type": "login_success",
  "severity": "info",
  "user_id": 1,
  "username": "admin",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "action": "User logged in successfully",
  "details": {
    "login_method": "password",
    "session_id": "sess_abc123",
    "two_factor_used": false
  },
  "success": true
}
```

### Device Control

```json
{
  "event_type": "device_controlled",
  "severity": "info",
  "user_id": 1,
  "username": "admin",
  "ip_address": "192.168.1.100",
  "resource_type": "device",
  "resource_id": "192.168.1.105",
  "action": "Device toggled",
  "details": {
    "device_ip": "192.168.1.105",
    "device_name": "Living Room Lamp",
    "previous_state": "off",
    "new_state": "on",
    "method": "manual"
  },
  "success": true
}
```

### System Error

```json
{
  "event_type": "system_error",
  "severity": "error",
  "action": "Database connection failed",
  "details": {
    "error_type": "ConnectionError",
    "error_message": "Unable to connect to database",
    "component": "database",
    "retry_count": 3,
    "duration_ms": 5000
  },
  "success": false
}
```

## Monitoring & Alerting

### Log Analysis Queries

```sql
-- Failed login attempts
SELECT username, ip_address, COUNT(*) as attempts
FROM audit_logs 
WHERE event_type = 'login_failure' 
  AND timestamp > datetime('now', '-1 hour')
GROUP BY username, ip_address
HAVING attempts > 5;

-- Privilege escalation attempts
SELECT * FROM audit_logs 
WHERE event_type = 'permission_denied'
  AND timestamp > datetime('now', '-24 hours')
ORDER BY timestamp DESC;

-- System errors
SELECT action, COUNT(*) as error_count
FROM audit_logs 
WHERE severity = 'error'
  AND timestamp > datetime('now', '-1 day')
GROUP BY action
ORDER BY error_count DESC;
```

### Performance Monitoring

```python
# Track API performance
@router.middleware("http")
async def audit_api_performance(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    
    # Log slow requests
    if duration_ms > 2000:
        await audit_logger.log_event_async(AuditEvent(
            event_type=AuditEventType.PERFORMANCE_ISSUE,
            severity=AuditSeverity.WARNING,
            action="Slow API response",
            details={
                "endpoint": str(request.url.path),
                "method": request.method,
                "duration_ms": duration_ms,
                "status_code": response.status_code
            }
        ))
    
    return response
```

## Compliance Features

### GDPR Compliance

```python
# Right to erasure (GDPR Article 17)
@router.delete("/api/audit/user/{user_id}")
async def erase_user_audit_logs(user_id: int):
    """Erase user audit logs for GDPR compliance."""
    await audit_logger.erase_user_logs(user_id)
    return {"message": "User audit logs erased"}

# Data export (GDPR Article 20)
@router.get("/api/audit/user/{user_id}/export")
async def export_user_audit_logs(user_id: int):
    """Export user audit logs for GDPR compliance."""
    logs = await audit_logger.get_user_logs(user_id)
    return {"logs": logs}
```

### Retention Policies

```python
# Automatic log cleanup
async def cleanup_old_logs():
    """Remove logs older than retention period."""
    retention_days = 365  # Configurable
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    deleted_count = await audit_logger.cleanup_logs(cutoff_date)
    
    # Log the cleanup operation
    await audit_logger.log_event_async(AuditEvent(
        event_type=AuditEventType.SYSTEM_MAINTENANCE,
        severity=AuditSeverity.INFO,
        action="Audit log cleanup performed",
        details={
            "retention_days": retention_days,
            "logs_deleted": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
    ))
```

## Best Practices

### Security Considerations

1. **Log Storage Security**
   - Separate audit log database
   - Read-only access for most users
   - Regular backup of audit logs

2. **Access Control**
   - Admin-only access to audit logs
   - Role-based log viewing
   - Audit log access logging

3. **Integrity Protection**
   - Cryptographic checksums
   - Regular integrity verification
   - Tamper detection alerts

### Performance Optimization

1. **Async Logging**
   ```python
   # Non-blocking audit logging
   await audit_logger.log_event_async(event)
   ```

2. **Batch Processing**
   ```python
   # Batch multiple events
   await audit_logger.log_events_batch(events)
   ```

3. **Log Rotation**
   ```python
   # Automatic log file rotation
   logging.handlers.RotatingFileHandler(
       filename="audit.log",
       maxBytes=10485760,  # 10MB
       backupCount=5
   )
   ```

## Troubleshooting

### Common Issues

**Audit logging not working:**
```bash
# Check audit logger initialization
docker logs kasa-monitor | grep "audit"

# Verify database permissions
docker exec kasa-monitor ls -la /app/logs/audit/
```

**High disk usage:**
```bash
# Check log file sizes
du -sh /app/logs/audit/*

# Configure log rotation
echo "AUDIT_LOG_MAX_SIZE=10MB" >> .env
echo "AUDIT_LOG_BACKUP_COUNT=5" >> .env
```

**Performance impact:**
```bash
# Monitor audit logging performance
grep "audit.*slow" /app/logs/app.log

# Enable async logging only
echo "AUDIT_ASYNC_ONLY=true" >> .env
```

## Related Pages

- [Security Guide](Security-Guide) - Overall security practices
- [User Management](User-Management) - User activity tracking
- [API Documentation](API-Documentation) - Audit API endpoints
- [Database Schema](Database-Schema) - Audit log schema

## Implementation Details

The audit logging system was implemented as part of a comprehensive security enhancement and includes:

- **Priority 1**: Security event logging (authentication, authorization)
- **Priority 2**: System operations logging (backup, configuration, errors)
- **Priority 3**: Enhanced coverage (device management, API performance, user activities)

All audit events are stored with integrity checksums and support both database and file-based logging for redundancy and compliance requirements.