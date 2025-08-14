# User Management

Complete guide for managing users, roles, and permissions in Kasa Monitor.

## User System Overview

```
┌─────────────────────────────────────┐
│         User Hierarchy              │
├─────────────────────────────────────┤
│  Admin (Full Access)                │
│    ↓                                │
│  Operator (Device Control)          │
│    ↓                                │
│  Viewer (Read Only)                 │
│    ↓                                │
│  Guest (Limited Access)             │
└─────────────────────────────────────┘
```

## Role Definitions

### Admin Role

**Capabilities:**
- ✅ All permissions
- ✅ User management
- ✅ System configuration
- ✅ Rate configuration
- ✅ Full device control
- ✅ Database management
- ✅ Security settings

**Typical Users:**
- System administrators
- Homeowners
- IT staff

### Operator Role

**Capabilities:**
- ✅ View all devices
- ✅ Control devices (on/off)
- ✅ Edit device settings
- ✅ View/export data
- ✅ Configure schedules
- ❌ User management
- ❌ System settings

**Typical Users:**
- Family members
- Facility managers
- Trusted users

### Viewer Role

**Capabilities:**
- ✅ View device status
- ✅ View energy data
- ✅ View costs
- ✅ Export reports
- ❌ Control devices
- ❌ Change settings
- ❌ User management

**Typical Users:**
- Accountants
- Energy auditors
- Report viewers

### Guest Role

**Capabilities:**
- ✅ View dashboard
- ✅ Basic device info
- ❌ Detailed data
- ❌ Cost information
- ❌ Device control
- ❌ Settings access

**Typical Users:**
- Temporary visitors
- Demo accounts
- Public displays

## Managing Users

### Creating Users

#### Via Web Interface

1. **Navigate to User Management**
   ```
   Settings → Users → Add User
   ```

2. **Fill User Details**
   ```yaml
   Username: john.doe
   Email: john@example.com
   Full Name: John Doe
   Password: ********
   Confirm: ********
   Role: Operator
   ```

3. **Set Permissions**
   - Check additional permissions
   - Set access restrictions
   - Configure notifications

#### Via API

```bash
# Create user via API
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "role": "operator"
  }'
```

#### Via CLI

```bash
# Docker exec command
docker exec -it kasa-monitor python3 -c "
from backend.auth import create_user
create_user(
    username='john.doe',
    email='john@example.com',
    password='SecurePass123!',
    role='operator'
)
"
```

### Editing Users

#### Change Role

```bash
# Promote to admin
curl -X PATCH http://localhost:8000/api/users/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

#### Update Profile

```bash
# Update user details
curl -X PATCH http://localhost:8000/api/users/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Smith",
    "email": "john.smith@example.com"
  }'
```

#### Reset Password

```bash
# Admin resets user password
curl -X POST http://localhost:8000/api/users/2/reset-password \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "NewSecurePass456!"}'
```

### Deleting Users

#### Soft Delete (Deactivate)

```bash
# Deactivate user
curl -X PATCH http://localhost:8000/api/users/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

#### Hard Delete

```bash
# Permanently delete user
curl -X DELETE http://localhost:8000/api/users/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Permission System

### Permission Categories

```yaml
Device Permissions:
  - devices.view        # View device list
  - devices.discover    # Run discovery
  - devices.edit        # Edit device settings
  - devices.remove      # Delete devices
  - devices.control     # Turn on/off

Rate Permissions:
  - rates.view          # View electricity rates
  - rates.edit          # Modify rates
  - rates.delete        # Remove rate configs

Cost Permissions:
  - costs.view          # View cost data
  - costs.export        # Export reports

User Permissions:
  - users.view          # View user list
  - users.invite        # Create new users
  - users.edit          # Modify users
  - users.remove        # Delete users
  - users.permissions   # Change permissions

System Permissions:
  - system.config       # System settings
  - system.logs         # View logs
  - system.backup       # Backup/restore
```

### Custom Permissions

```python
# Grant specific permission
@app.post("/api/users/{user_id}/permissions")
async def grant_permission(
    user_id: int,
    permission: str,
    admin: User = Depends(require_admin)
):
    db.execute(
        "INSERT INTO user_permissions (user_id, permission) VALUES (?, ?)",
        (user_id, permission)
    )
    return {"status": "granted"}
```

### Permission Checking

```python
# Decorator for routes
@require_permission("devices.control")
async def control_device(device_ip: str):
    # Only users with permission can access
    pass

# Manual check
if user.has_permission("system.config"):
    # Allow system configuration
    pass
```

## Access Control

### IP Restrictions

```yaml
# User-specific IP whitelist
users:
  john.doe:
    allowed_ips:
      - 192.168.1.0/24
      - 10.0.0.5
    blocked_ips:
      - 192.168.1.666
```

### Time-Based Access

```yaml
# Restrict access hours
users:
  night_operator:
    access_hours:
      start: "18:00"
      end: "06:00"
    days: ["mon", "tue", "wed", "thu", "fri"]
```

### Device-Specific Access

```python
# Limit user to specific devices
user_device_access = {
    "john.doe": [
        "192.168.1.100",  # Living room
        "192.168.1.101",  # Bedroom
    ],
    "guest": [
        "192.168.1.102",  # Guest room only
    ]
}
```

## User Authentication

### Password Requirements

```python
# Password policy
PASSWORD_POLICY = {
    "min_length": 12,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_numbers": True,
    "require_special": True,
    "max_age_days": 90,
    "history_count": 5,  # Can't reuse last 5 passwords
    "max_attempts": 5,   # Lock after 5 failed attempts
}
```

### Two-Factor Authentication

```python
# Enable 2FA
@app.post("/api/users/2fa/enable")
async def enable_2fa(user: User = Depends(get_current_user)):
    secret = pyotp.random_base32()
    
    # Save secret
    db.execute(
        "UPDATE users SET totp_secret = ? WHERE id = ?",
        (secret, user.id)
    )
    
    # Generate QR code
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name='Kasa Monitor'
    )
    
    return {
        "secret": secret,
        "qr_code": generate_qr_code(provisioning_uri)
    }
```

### Session Management

```python
# Session configuration
SESSION_CONFIG = {
    "timeout_minutes": 30,
    "max_sessions": 3,  # Max concurrent sessions
    "remember_me_days": 30,
    "secure_cookie": True,
    "same_site": "strict"
}
```

## User Dashboard

### User Profile Page

```yaml
Profile Information:
  - Username: john.doe
  - Email: john@example.com
  - Full Name: John Doe
  - Role: Operator
  - Member Since: 2024-01-01
  - Last Login: 2024-01-15 10:30

Statistics:
  - Devices Managed: 12
  - Actions Today: 45
  - Data Exported: 3 reports
  - API Calls: 156

Settings:
  - Theme: Dark
  - Timezone: America/New_York
  - Notifications: Enabled
  - Language: English
```

### Activity Log

```sql
-- User activity query
SELECT 
    timestamp,
    action,
    resource,
    details
FROM audit_log
WHERE user_id = ?
ORDER BY timestamp DESC
LIMIT 100;
```

## Bulk User Operations

### Import Users

```python
# CSV import
import csv

def import_users(csv_file):
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            create_user(
                username=row['username'],
                email=row['email'],
                password=row['password'],
                role=row['role']
            )
```

**CSV Format:**
```csv
username,email,password,role
john.doe,john@example.com,TempPass123!,operator
jane.smith,jane@example.com,TempPass456!,viewer
bob.wilson,bob@example.com,TempPass789!,guest
```

### Export Users

```bash
# Export user list
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "SELECT username, email, role, created_at FROM users" \
  > users_export.csv
```

### Batch Operations

```python
# Deactivate multiple users
@app.post("/api/users/batch/deactivate")
async def batch_deactivate(
    user_ids: List[int],
    admin: User = Depends(require_admin)
):
    for user_id in user_ids:
        db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,)
        )
    return {"deactivated": len(user_ids)}
```

## User Notifications

### Email Notifications

```python
# Send user notification
async def notify_user(user_id: int, subject: str, message: str):
    user = get_user(user_id)
    
    await send_email(
        to=user.email,
        subject=subject,
        body=message,
        template="notification.html"
    )
```

### In-App Notifications

```python
# Create notification
async def create_notification(
    user_id: int,
    type: str,
    message: str
):
    db.execute("""
        INSERT INTO notifications 
        (user_id, type, message, created_at, is_read)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, 0)
    """, (user_id, type, message))
```

## Security Best Practices

### Account Security

1. **Strong Passwords**
   - Minimum 12 characters
   - Mix of characters
   - Regular rotation

2. **Account Lockout**
   ```python
   if failed_attempts >= 5:
       lock_account(user_id, duration=30)  # 30 minutes
   ```

3. **Session Security**
   - HTTPOnly cookies
   - Secure flag
   - CSRF protection

### Audit Trail

```python
# Log all user actions
def audit_log(user_id, action, resource, details=None):
    db.execute("""
        INSERT INTO audit_log 
        (user_id, action, resource, details, timestamp, ip_address)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    """, (user_id, action, resource, json.dumps(details), request.remote_addr))
```

### Regular Reviews

```bash
#!/bin/bash
# Monthly user audit

# Find inactive users
sqlite3 /app/data/kasa_monitor.db "
    SELECT username, last_login 
    FROM users 
    WHERE last_login < datetime('now', '-90 days')
"

# Check for privilege escalation
sqlite3 /app/data/kasa_monitor.db "
    SELECT username, role, updated_at 
    FROM users 
    WHERE role = 'admin' 
    ORDER BY updated_at DESC
"
```

## Troubleshooting

### Common Issues

**User can't log in**
```bash
# Check account status
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "SELECT username, is_active, failed_attempts FROM users WHERE username='john.doe'"

# Reset failed attempts
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "UPDATE users SET failed_attempts=0 WHERE username='john.doe'"
```

**Permission denied**
```bash
# Check user permissions
curl http://localhost:8000/api/users/me/permissions \
  -H "Authorization: Bearer $TOKEN"
```

**Forgot admin password**
```bash
# Reset admin password via Docker
docker exec -it kasa-monitor python3 -c "
from backend.auth import reset_admin_password
reset_admin_password('NewAdminPass123!')
"
```

## API Reference

### User Endpoints

```bash
GET    /api/users              # List all users
POST   /api/users              # Create user
GET    /api/users/{id}         # Get user details
PATCH  /api/users/{id}         # Update user
DELETE /api/users/{id}         # Delete user
GET    /api/users/me           # Current user
POST   /api/users/{id}/reset-password
GET    /api/users/{id}/permissions
POST   /api/users/{id}/permissions
DELETE /api/users/{id}/permissions/{permission}
```

## Related Pages

- [Security Guide](Security-Guide) - Security best practices
- [First Time Setup](First-Time-Setup) - Initial admin creation
- [API Documentation](API-Documentation) - User API endpoints
- [Database Schema](Database-Schema) - User tables structure