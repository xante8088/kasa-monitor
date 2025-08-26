# API Documentation

Complete REST API reference for Kasa Monitor.

## Base URL
```
http://localhost:5272/api
```

## Authentication (Enhanced v1.2.0)

Most endpoints require JWT authentication with dual-token system (access + refresh tokens). The application uses secure JWT secret management with rotation support.

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "permissions": ["all"]
  },
  "session": {
    "session_id": "sess_abc123",
    "created_at": "2024-01-01T10:00:00Z",
    "expires_at": "2024-01-01T10:30:00Z"
  }
}
```

### Refresh Token (New v1.2.0)
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### Using Token
Include in Authorization header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Endpoints

### Authentication

#### Check Setup Required
```http
GET /api/auth/setup-required
```
Returns whether initial admin setup is needed.

#### Create Admin (First Time)
```http
POST /api/auth/setup
Content-Type: application/json

{
  "username": "admin",
  "email": "admin@example.com",
  "password": "securepassword",
  "full_name": "Admin User"
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer {token}
```

#### Logout
```http
POST /api/auth/logout
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Logged out successfully",
  "sessions_terminated": 1
}
```

#### Get Active Sessions (New v1.2.0)
```http
GET /api/auth/sessions
Authorization: Bearer {token}
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2024-01-01T10:00:00Z",
      "last_activity": "2024-01-01T10:25:00Z",
      "expires_at": "2024-01-01T10:30:00Z",
      "is_current": true
    }
  ],
  "total": 2,
  "max_allowed": 3
}
```

#### Terminate Session (New v1.2.0)
```http
DELETE /api/auth/sessions/{session_id}
Authorization: Bearer {token}
```

#### Security Status (New v1.2.0)
```http
GET /api/auth/security-status
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "jwt_configuration": {
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7
  },
  "security_features": {
    "token_refresh_enabled": true,
    "session_management_available": true,
    "audit_logging_enabled": true,
    "structured_error_responses": true
  }
}
```

### Error Responses (New v1.2.0)

All authentication errors now return structured JSON:

**401 Unauthorized:**
```json
{
  "error": "authentication_expired",
  "message": "Your session has expired. Please log in again.",
  "error_code": "TOKEN_EXPIRED",
  "timestamp": "2024-01-01T10:00:00Z",
  "redirect_to": "/login"
}
```

**403 Forbidden:**
```json
{
  "error": "authorization_failed",
  "message": "You don't have permission to access this resource",
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "required_permission": "ADMIN_ACCESS"
}
```

**429 Rate Limited:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60,
  "limit": "10 per hour"
}
```

### Device Management

#### List All Devices
```http
GET /api/devices
```

**Response:**
```json
[
  {
    "device_ip": "192.168.1.100",
    "alias": "Living Room Lamp",
    "model": "HS110",
    "device_type": "plug",
    "is_on": true,
    "current_power_w": 45.2,
    "today_energy_kwh": 0.361,
    "month_energy_kwh": 10.45,
    "voltage": 120.1,
    "current": 0.38,
    "signal_strength": -45,
    "last_seen": "2024-01-15T10:30:00Z"
  }
]
```

#### Discover Devices
```http
POST /api/discover
Content-Type: application/json

{
  "username": "tplink@email.com",  // Optional
  "password": "tplinkpassword"      // Optional
}
```

**Response:**
```json
{
  "discovered": 5
}
```

#### Add Manual Device
```http
POST /api/devices/manual
Content-Type: application/json

{
  "ip": "192.168.1.100",
  "alias": "Kitchen Plug"  // Optional
}
```

#### Get Device Details
```http
GET /api/device/{device_ip}
```

#### Get Device History
```http
GET /api/device/{device_ip}/history?start_time=2024-01-01&end_time=2024-01-31&interval=1h
```

**Query Parameters:**
- `start_time`: ISO 8601 datetime (optional)
- `end_time`: ISO 8601 datetime (optional)
- `interval`: Data aggregation interval (1h, 6h, 1d)

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T10:00:00Z",
    "power_w": 45.2,
    "energy_kwh": 0.045,
    "cost": 0.005
  }
]
```

#### Get Device Statistics
```http
GET /api/device/{device_ip}/stats
```

**Response:**
```json
{
  "daily_usage_kwh": 0.86,
  "weekly_usage_kwh": 6.02,
  "monthly_usage_kwh": 25.8,
  "daily_cost": 0.10,
  "weekly_cost": 0.72,
  "monthly_cost": 3.09,
  "average_power_w": 35.8,
  "peak_power_w": 125.0,
  "total_on_time_hours": 18.5
}
```

#### Control Device
```http
POST /api/device/{device_ip}/control
Content-Type: application/json

{
  "action": "on"  // or "off", "toggle"
}
```

#### Remove Device
```http
DELETE /api/devices/{device_ip}
```

### Electricity Rates

#### Get Current Rates
```http
GET /api/rates
```

**Response:**
```json
{
  "rate_type": "tiered",
  "currency": "USD",
  "rate_structure": {
    "tier1_limit": 500,
    "tier1_rate": 0.10,
    "tier2_limit": 1000,
    "tier2_rate": 0.12,
    "tier3_rate": 0.15
  },
  "time_of_use_rates": [
    {
      "start_hour": 0,
      "end_hour": 6,
      "rate": 0.08,
      "label": "Off-Peak"
    },
    {
      "start_hour": 6,
      "end_hour": 22,
      "rate": 0.12,
      "label": "Peak"
    }
  ]
}
```

#### Update Rates
```http
POST /api/rates
Content-Type: application/json

{
  "rate_type": "simple",
  "currency": "USD",
  "rate_structure": {
    "rate_per_kwh": 0.12
  }
}
```

### Cost Analysis

#### Calculate Costs
```http
GET /api/costs?start_date=2024-01-01&end_date=2024-01-31
```

**Response:**
```json
{
  "total_cost": 45.67,
  "total_kwh": 380.5,
  "average_daily_cost": 1.47,
  "devices": [
    {
      "device_ip": "192.168.1.100",
      "device_name": "Living Room",
      "total_kwh": 125.3,
      "total_cost": 15.04,
      "percentage": 32.9
    }
  ],
  "daily_breakdown": [
    {
      "date": "2024-01-15",
      "kwh": 12.5,
      "cost": 1.50
    }
  ]
}
```

### User Management

#### List Users
```http
GET /api/users
Authorization: Bearer {admin_token}
```

#### Create User
```http
POST /api/users
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "username": "john",
  "email": "john@example.com",
  "password": "password123",
  "full_name": "John Doe",
  "role": "viewer"
}
```

#### Update User
```http
PATCH /api/users/{user_id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "role": "operator",
  "is_active": true
}
```

#### Delete User
```http
DELETE /api/users/{user_id}
Authorization: Bearer {admin_token}
```

### Two-Factor Authentication

#### Check 2FA Status
```http
GET /api/auth/2fa/status
Authorization: Bearer {token}
```

**Response:**
```json
{
  "enabled": false
}
```

#### Setup 2FA
```http
POST /api/auth/2fa/setup
Authorization: Bearer {token}
```

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,...",
  "backup_codes": [
    "ABC123",
    "DEF456",
    "GHI789"
  ]
}
```

#### Verify 2FA
```http
POST /api/auth/2fa/verify
Authorization: Bearer {token}
Content-Type: application/json

{
  "token": "123456"
}
```

#### Disable 2FA
```http
POST /api/auth/2fa/disable
Authorization: Bearer {token}
```

### System Configuration

#### Get System Config
```http
GET /api/system/config
Authorization: Bearer {admin_token}
```

#### Update System Config
```http
PUT /api/system/config
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "polling_interval": 60,
  "data_retention_days": 365,
  "allow_device_control": true,
  "require_https": false
}
```

#### Get System Status
```http
GET /api/system/status
```

**Response:**
```json
{
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "devices_connected": 5,
  "database_size_mb": 45.2,
  "last_poll": "2024-01-15T10:30:00Z"
}
```

### Network Settings

#### Get Network Configuration
```http
GET /api/settings/network
```

**Response:**
```json
{
  "network_mode": "bridge",
  "discovery_enabled": false,
  "manual_devices_enabled": true,
  "host_ip": "172.17.0.1"
}
```

### Data Export (Enhanced Security v1.2.0)

**Required Permission:** `DATA_EXPORT`  
**Rate Limit:** 10 exports per hour per user  
**Audit Logging:** All operations logged for compliance  
**User Ownership:** Users can only access their own exports (admin override available)

#### Get Export Formats
```http
GET /api/exports/formats
Authorization: Bearer {token_with_data_export_permission}
```

**Response:**
```json
{
  "formats": [
    {
      "id": "csv",
      "name": "CSV",
      "description": "Comma-separated values",
      "mime_type": "text/csv",
      "extension": ".csv"
    },
    {
      "id": "json",
      "name": "JSON",
      "description": "JavaScript Object Notation",
      "mime_type": "application/json",
      "extension": ".json"
    },
    {
      "id": "excel",
      "name": "Excel",
      "description": "Microsoft Excel workbook",
      "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "extension": ".xlsx"
    }
  ]
}
```

#### Get Available Devices for Export
```http
GET /api/exports/devices
Authorization: Bearer {token_with_data_export_permission}
```

**Response:**
```json
{
  "devices": [
    {
      "device_ip": "192.168.1.100",
      "device_name": "Living Room Lamp",
      "device_type": "plug",
      "last_seen": "2024-01-15T10:30:00Z",
      "data_points": 8760
    }
  ]
}
```

#### Get Available Metrics
```http
GET /api/exports/metrics
Authorization: Bearer {token_with_data_export_permission}
```

**Response:**
```json
{
  "metrics": [
    {
      "field": "power_w",
      "name": "Power (Watts)",
      "description": "Instantaneous power consumption",
      "data_type": "float",
      "unit": "W"
    },
    {
      "field": "energy_kwh",
      "name": "Energy (kWh)",
      "description": "Cumulative energy consumption",
      "data_type": "float",
      "unit": "kWh"
    },
    {
      "field": "cost",
      "name": "Cost",
      "description": "Calculated energy cost",
      "data_type": "float",
      "unit": "currency"
    }
  ]
}
```

#### Create Export
```http
POST /api/exports/create
Authorization: Bearer {token_with_data_export_permission}
Content-Type: application/json

{
  "export_type": "device_data",
  "devices": ["192.168.1.100", "192.168.1.101"],
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  },
  "format": "csv",
  "fields": ["timestamp", "power_w", "energy_kwh", "cost"],
  "aggregation": "hourly",
  "options": {
    "include_headers": true,
    "timezone": "America/New_York"
  }
}
```

**Response:**
```json
{
  "export_id": "export_12345",
  "status": "queued",
  "created_at": "2024-01-15T10:30:00Z",
  "user_id": 1,
  "estimated_completion": "2024-01-15T10:32:00Z",
  "download_url": "/api/exports/download/export_12345"
}
```

#### Get Export Status
```http
GET /api/exports/{export_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "export_id": "export_12345",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:31:45Z",
  "user_id": 1,
  "file_size": 1024000,
  "record_count": 744,
  "download_url": "/api/exports/download/export_12345",
  "expires_at": "2024-01-22T10:31:45Z"
}
```

**Security Note:** Users can only access their own exports unless they have admin role.

#### Get Export History
```http
GET /api/exports/history?limit=50&offset=0
Authorization: Bearer {token}
```

**Response:**
```json
{
  "exports": [
    {
      "export_id": "export_12345",
      "export_type": "device_data",
      "format": "csv",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "user_id": 1,
      "username": "admin",
      "file_size": 1024000,
      "record_count": 744,
      "retention_days": 7,
      "expires_at": "2024-01-22T10:30:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 50
}
```

**Security Note:** Regular users only see their own exports.

#### Download Export
```http
GET /api/exports/download/{export_id}
Authorization: Bearer {token}
```

**Security:** Validates user ownership before download.

#### Delete Export
```http
DELETE /api/exports/{export_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Export deleted successfully",
  "export_id": "export_12345",
  "deleted_at": "2024-01-15T11:00:00Z"
}
```

**Security:** Users can only delete their own exports.

#### Preview Export Data
```http
GET /api/exports/preview?export_type=device_data&devices=192.168.1.100&limit=5
Authorization: Bearer {token_with_data_export_permission}
```

**Response:**
```json
{
  "preview": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "device_ip": "192.168.1.100",
      "device_name": "Living Room Lamp",
      "power_w": 45.2,
      "energy_kwh": 0.045,
      "cost": 0.005
    }
  ],
  "total_records": 8760,
  "estimated_file_size": "2.1 MB"
}
```

#### Get Export Statistics
```http
GET /api/exports/stats
Authorization: Bearer {token}
```

**Response:**
```json
{
  "total_exports": 156,
  "exports_this_month": 23,
  "total_data_exported": "450.2 MB",
  "most_popular_format": "csv",
  "user_exports_remaining": 7
}
```

### Export Error Responses

**Permission Denied (403):**
```json
{
  "detail": "Permission denied",
  "error_code": "PERMISSION_DENIED",
  "message": "You don't have permission to perform data exports",
  "required_permission": "DATA_EXPORT"
}
```

**Access Denied - Ownership (403):**
```json
{
  "detail": "Access denied to export",
  "error_code": "ACCESS_DENIED",
  "message": "You don't have access to this export",
  "export_owner": "other_user"
}
```

**Rate Limit Exceeded (429):**
```json
{
  "detail": "Export rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Export rate limit exceeded. Please try again later.",
  "limit": "10 per hour",
  "retry_after": "2024-01-15T11:30:00Z"
}
```

### SSL Certificate Management (Enhanced v1.2.0)

**New Features:**
- Persistent storage across Docker restarts
- Automatic certificate detection and loading
- Database path storage for persistence
- Cross-device link error fixed

#### Get SSL Files
```http
GET /api/ssl/files
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "cert_exists": true,
  "key_exists": true,
  "cert_info": {
    "subject": "CN=localhost",
    "issuer": "CN=localhost",
    "valid_from": "2024-01-01",
    "valid_until": "2025-01-01"
  }
}
```

#### Generate CSR
```http
POST /api/ssl/generate-csr
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "common_name": "kasa-monitor.local",
  "organization": "My Organization",
  "country": "US",
  "state": "CA",
  "locality": "San Francisco"
}
```

#### Download SSL Files
```http
GET /api/ssl/download/{filename}
Authorization: Bearer {admin_token}
```

Where filename can be:
- `cert.pem` - SSL certificate
- `key.pem` - Private key
- `csr.pem` - Certificate signing request

#### Upload SSL Certificate
```http
POST /api/system/ssl/upload-cert
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

Form Data:
  file: (certificate file)
```

**Security Notes:**
- File size limited by MAX_UPLOAD_SIZE_MB (default: 10MB)
- File type validation enforced
- Files are quarantined and validated before processing

#### Upload SSL Private Key
```http
POST /api/system/ssl/upload-key
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

Form Data:
  file: (private key file)
```

**Security Notes:**
- File size limited by MAX_UPLOAD_SIZE_MB (default: 10MB)
- File type validation enforced
- Files are quarantined and validated before processing

### Backup Management

#### List Backups
```http
GET /api/backups
Authorization: Bearer {admin_token}
```

**Response:**
```json
[
  {
    "filename": "kasa_backup_20240115_103000.7z",
    "size": 1048576,
    "created": "2024-01-15T10:30:00Z",
    "type": "manual",
    "includes": ["database", "config", "logs"]
  }
]
```

#### Create Backup
```http
POST /api/backups/create
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "type": "manual",
  "include_logs": true,
  "include_exports": false,
  "compression": "high"
}
```

#### Download Backup
```http
GET /api/backups/{filename}/download
Authorization: Bearer {admin_token}
```

#### Delete Backup
```http
DELETE /api/backups/{filename}
Authorization: Bearer {admin_token}
```

#### Restore Backup
```http
POST /api/backups/restore
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

Form Data:
  file: (backup file)
  options: {"restore_config": true, "restore_database": true}
```

#### Get Backup Progress
```http
GET /api/backups/progress
Authorization: Bearer {admin_token}
```

### Backup Schedules

#### Get Backup Schedules
```http
GET /api/backups/schedules
Authorization: Bearer {admin_token}
```

#### Create Backup Schedule
```http
POST /api/backups/schedules
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Daily Backup",
  "cron": "0 2 * * *",
  "enabled": true,
  "retention_days": 30,
  "options": {
    "include_logs": true,
    "compression": "normal"
  }
}
```

#### Update Backup Schedule
```http
PUT /api/backups/schedules/{schedule_id}
Authorization: Bearer {admin_token}
```

#### Delete Backup Schedule
```http
DELETE /api/backups/schedules/{schedule_id}
Authorization: Bearer {admin_token}
```

### Health Monitoring

#### Basic Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Detailed Health Check
```http
GET /api/health/detailed
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5,
      "details": {
        "size_mb": 45.2,
        "device_count": 10,
        "reading_count": 50000
      }
    },
    "device_manager": {
      "status": "healthy",
      "connected_devices": 8,
      "failed_devices": 2
    },
    "cache": {
      "status": "healthy",
      "hit_rate": 0.85,
      "memory_usage_mb": 128
    },
    "scheduler": {
      "status": "healthy",
      "jobs_pending": 3,
      "jobs_running": 1
    }
  },
  "uptime_seconds": 86400,
  "memory_usage_mb": 256,
  "cpu_usage_percent": 15.5
}
```

## WebSocket Events

Connect to WebSocket for real-time updates:
```javascript
const socket = io('ws://localhost:5272');

socket.on('connect', () => {
  console.log('Connected to WebSocket');
  
  // Subscribe to device updates
  socket.emit('subscribe_device', { device_ip: '192.168.1.100' });
});

socket.on('device_update', (data) => {
  console.log('Device updated:', data);
});
```

### Events

#### Device Update
```json
{
  "event": "device_update",
  "device_ip": "192.168.1.100",
  "data": {
    "is_on": true,
    "current_power_w": 45.2,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### Device Status Change
```json
{
  "event": "device_status",
  "device_ip": "192.168.1.100",
  "status": "online",  // or "offline"
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_code": "INVALID_REQUEST"
}
```

### Common Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `500` - Internal Server Error

## Rate Limiting

API requests are limited to:
- 100 requests per minute per IP
- 1000 requests per hour per user

Headers indicate rate limit status:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704456000
```

## CORS Policy

Cross-Origin Resource Sharing (CORS) is strictly enforced:
- Origins must be explicitly whitelisted via CORS_ALLOWED_ORIGINS
- No wildcard origins allowed in production
- Preflight requests are validated
- CORS violations are logged for security monitoring

## File Upload Security

All file uploads are subject to:
- Size limits (MAX_UPLOAD_SIZE_MB, default: 10MB)
- File type validation (extension and MIME type)
- Quarantine and validation before processing
- Plugin signature verification (when REQUIRE_PLUGIN_SIGNATURES=true)

## Examples

### Python
```python
import requests

# Login
response = requests.post('http://localhost:5272/api/auth/login', json={
    'username': 'admin',
    'password': 'password123'
})
token = response.json()['access_token']

# Get devices
headers = {'Authorization': f'Bearer {token}'}
devices = requests.get('http://localhost:5272/api/devices', headers=headers)
print(devices.json())
```

### JavaScript
```javascript
// Login
const loginRes = await fetch('http://localhost:5272/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'password123'
  })
});
const { access_token } = await loginRes.json();

// Get devices
const devicesRes = await fetch('http://localhost:5272/api/devices', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const devices = await devicesRes.json();
```

### cURL
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:5272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}' \
  | jq -r .access_token)

# Get devices
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5272/api/devices
```

## SDK Support

While there's no official SDK yet, the API is designed to be simple and RESTful. Community SDKs are welcome!

## API Versioning

The API uses URL versioning. Current version is v1 (implied in `/api/`).

Future versions will use `/api/v2/` format.

## Need Help?

- Check the [FAQ](FAQ)
- Open an [issue](https://github.com/xante8088/kasa-monitor/issues)
- See [examples](https://github.com/xante8088/kasa-monitor/tree/main/examples)

---

**Document Version:** 2.0.0  
**Last Updated:** 2025-08-26  
**Review Status:** Current  
**Change Summary:** Major update with v1.2.0 security enhancements including authentication improvements, data export security, SSL persistence, and structured error responses  
**Review Status:** Current  
**Change Summary:** Added security notes for file uploads, CORS policy, and JWT authentication updates