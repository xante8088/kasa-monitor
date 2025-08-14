# API Documentation

Complete REST API reference for Kasa Monitor.

## Base URL
```
http://localhost:8000/api
```

## Authentication

Most endpoints require JWT authentication.

### Get Token
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
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "permissions": ["all"]
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

### Permissions

#### Get All Permissions
```http
GET /api/permissions
Authorization: Bearer {token}
```

#### Get Role Permissions
```http
GET /api/roles/permissions
Authorization: Bearer {token}
```

#### Update Role Permissions
```http
POST /api/roles/{role}/permissions
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "permission": "devices.control",
  "action": "add"  // or "remove"
}
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

## WebSocket Events

Connect to WebSocket for real-time updates:
```javascript
const socket = io('ws://localhost:8000');

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

## Examples

### Python
```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login', json={
    'username': 'admin',
    'password': 'password123'
})
token = response.json()['access_token']

# Get devices
headers = {'Authorization': f'Bearer {token}'}
devices = requests.get('http://localhost:8000/api/devices', headers=headers)
print(devices.json())
```

### JavaScript
```javascript
// Login
const loginRes = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'password123'
  })
});
const { access_token } = await loginRes.json();

// Get devices
const devicesRes = await fetch('http://localhost:8000/api/devices', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const devices = await devicesRes.json();
```

### cURL
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}' \
  | jq -r .access_token)

# Get devices
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/devices
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