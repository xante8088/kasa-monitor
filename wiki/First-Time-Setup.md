# First Time Setup

Complete walkthrough for initial configuration of Kasa Monitor after installation.

## Setup Wizard Overview

When you first access Kasa Monitor, you'll be guided through:

1. ✅ Admin account creation
2. ✅ Electricity rate configuration
3. ✅ Device discovery/addition
4. ✅ Basic preferences
5. ✅ Optional integrations

## Step 1: Admin Account Creation

### Accessing Setup

When no admin exists, you're automatically redirected to `/setup`

```
http://localhost:3000/setup
```

### Create Admin Account

Fill in the required fields:

```yaml
Username: admin          # Unique identifier
Email: admin@email.com   # For notifications
Password: ************   # Min 8 characters
Confirm: ************    # Must match
Full Name: Admin User    # Display name
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- Special characters recommended

### First Login

After creation:
1. Redirected to login page
2. Enter username and password
3. Access granted to dashboard

## Step 2: Electricity Rates

### Why Configure Rates?

Rates are essential for:
- Cost calculations
- Budget tracking
- ROI analysis
- Usage optimization

### Basic Configuration

**Simple Rate (Most Common):**

```
1. Click Settings → Electricity Rates
2. Select "Simple/Flat Rate"
3. Enter your rate: $0.12 per kWh
4. Select currency: USD
5. Save
```

**Finding Your Rate:**
```
Check your electricity bill:
- Look for "Energy Charge"
- Find $/kWh or ¢/kWh
- Include delivery charges
- Add taxes if not included
```

### Advanced Rates

**Time-of-Use (TOU):**
```yaml
Peak Hours (2-8 PM): $0.28/kWh
Off-Peak (8 PM-2 PM): $0.14/kWh
Super Off-Peak (12-6 AM): $0.10/kWh
```

**Tiered Rates:**
```yaml
Tier 1 (0-500 kWh): $0.10/kWh
Tier 2 (501-1000 kWh): $0.12/kWh
Tier 3 (1000+ kWh): $0.15/kWh
```

See [Electricity Rates](Electricity-Rates) for detailed configuration.

## Step 3: Adding Devices

### Method A: Automatic Discovery

**Requirements:** Host or Macvlan network mode

```
1. Click "Discover Devices" button
2. Wait 5-10 seconds
3. Found devices appear automatically
4. Click "Save All" to add
```

**Discovery Checklist:**
- ✅ Devices powered on
- ✅ Same network/VLAN
- ✅ UDP port 9999 open
- ✅ No firewall blocking

### Method B: Manual Entry

**Works in any network mode**

```
1. Settings → Device Management
2. Click "Add Device Manually"
3. Enter device IP: 192.168.1.100
4. Enter friendly name: "Living Room Lamp"
5. Click "Add"
```

**Finding Device IPs:**

1. **Kasa App Method:**
   ```
   Open Kasa app → Device → Settings → Device Info → IP Address
   ```

2. **Router Method:**
   ```
   Router admin panel → Connected devices → Look for HS/KL/KP devices
   ```

3. **Network Scan:**
   ```bash
   nmap -sn 192.168.1.0/24 | grep -B2 "TP-LINK"
   ```

### Method C: Cloud Connection

**For remote devices:**

```
1. Settings → TP-Link Cloud
2. Enter Kasa account credentials
3. Click "Connect"
4. Cloud devices sync automatically
```

## Step 4: Dashboard Configuration

### Layout Settings

Configure your dashboard view:

```yaml
Display Options:
  Grid Layout: Normal/Compact/Comfortable
  Cards per Row: Auto/2/3/4
  Show Offline: Yes/No
  Auto-Refresh: 60 seconds
```

### Device Organization

Organize devices logically:

1. **Rename Devices:**
   ```
   Default: "Smart Plug 1"
   Better: "Kitchen Coffee Maker"
   ```

2. **Create Groups:**
   ```
   Living Room: TV, Lamp, Fan
   Kitchen: Coffee, Microwave, Toaster
   Bedroom: Lights, Chargers, Clock
   ```

3. **Set Favorites:**
   - Star frequently used devices
   - They appear at top of dashboard

### Cost Display

Configure cost visibility:

```yaml
Show on Cards:
  ✅ Current Power
  ✅ Daily Cost
  ✅ Monthly Total
  ☐ Yearly Projection
```

## Step 5: User Preferences

### General Settings

```yaml
System:
  Time Zone: America/New_York
  Date Format: MM/DD/YYYY
  Currency: USD
  Temperature: Fahrenheit

Display:
  Theme: Light/Dark/Auto
  Language: English
  Animations: Enabled
```

### Notification Settings

```yaml
Alerts:
  ✅ Device Offline > 5 min
  ✅ High Power Alert > 3000W
  ✅ Daily Budget Exceeded
  ☐ Weekly Summary Email

Methods:
  ✅ In-App Notifications
  ☐ Email Alerts
  ☐ Push Notifications
```

### Data & Privacy

```yaml
Data Retention:
  Detailed Data: 30 days
  Daily Summaries: 1 year
  Monthly Reports: 5 years

Privacy:
  ☐ Share Anonymous Usage
  ✅ Local Storage Only
  ☐ Cloud Backup
```

## Step 6: Optional Integrations

### InfluxDB Setup

For advanced time-series storage:

```yaml
1. Enable InfluxDB in docker-compose
2. Configure connection:
   URL: http://influxdb:8086
   Token: [generated]
   Organization: kasa-monitor
   Bucket: device-data
3. Test connection
4. Enable data export
```

### Home Assistant

For smart home integration:

```yaml
1. Install Kasa Monitor integration
2. Configure API access:
   URL: http://kasa-monitor:8000
   Token: [API token]
3. Add entities to HA
```

### External Monitoring

For alerts and monitoring:

```yaml
Uptime Monitoring:
  - Uptime Kuma
  - Healthchecks.io

Metrics Export:
  - Prometheus endpoint
  - Grafana dashboards
```

## Setup Checklist

### Essential Tasks ✅

- [ ] Admin account created
- [ ] Logged in successfully
- [ ] Electricity rates configured
- [ ] At least one device added
- [ ] Device names customized
- [ ] Dashboard accessible

### Recommended Tasks 📋

- [ ] Additional users created
- [ ] Device groups organized
- [ ] Budget limits set
- [ ] Backup configured
- [ ] Notifications enabled
- [ ] Time zone verified

### Optional Tasks 🔧

- [ ] InfluxDB connected
- [ ] SSL/HTTPS enabled
- [ ] API tokens generated
- [ ] Automation rules created
- [ ] Custom reports configured

## Quick Setup Script

For automated setup:

```bash
#!/bin/bash
# Quick setup script

# Set variables
ADMIN_USER="admin"
ADMIN_PASS="SecurePass123!"
ADMIN_EMAIL="admin@example.com"
RATE="0.12"

# Create admin via API
curl -X POST http://localhost:8000/api/auth/setup \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$ADMIN_USER\",
    \"password\": \"$ADMIN_PASS\",
    \"email\": \"$ADMIN_EMAIL\",
    \"full_name\": \"Administrator\"
  }"

# Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" \
  | jq -r .access_token)

# Configure rates
curl -X POST http://localhost:8000/api/rates \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"rate_type\": \"simple\",
    \"currency\": \"USD\",
    \"rate_structure\": {
      \"rate_per_kwh\": $RATE
    }
  }"

# Discover devices
curl -X POST http://localhost:8000/api/discover \
  -H "Authorization: Bearer $TOKEN"

echo "Setup complete!"
```

## Troubleshooting Setup

### Cannot Access Setup Page

```bash
# Check if setup is required
curl http://localhost:8000/api/auth/setup-required

# Should return: {"setup_required": true}
```

### Setup Page Loops

```bash
# Clear database and restart
docker exec kasa-monitor rm /app/data/kasa_monitor.db
docker restart kasa-monitor
```

### Devices Not Found

1. Verify network mode (host/macvlan for discovery)
2. Check devices are on same network
3. Try manual IP entry instead

### Rates Not Saving

1. Check all required fields filled
2. Verify rate format (decimal, not percentage)
3. Check browser console for errors

## Post-Setup Tasks

### 1. Security Hardening

**Essential Security Configuration:**

```bash
# Generate secure JWT secret (REQUIRED for production)
export JWT_SECRET_KEY=$(openssl rand -base64 32)
echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}" >> .env

# Configure CORS for your domain
echo "CORS_ALLOWED_ORIGINS=https://yourdomain.com" >> .env

# Set file upload restrictions
echo "MAX_UPLOAD_SIZE_MB=10" >> .env
echo "REQUIRE_PLUGIN_SIGNATURES=true" >> .env

# Generate secure database credentials (if using InfluxDB)
export INFLUX_PASSWORD=$(openssl rand -base64 24)
export INFLUX_TOKEN=$(openssl rand -hex 32)
```

**Additional Security Steps:**
- Enable HTTPS with SSL certificates
- Configure firewall rules
- Set up fail2ban for brute force protection
- Implement network isolation

See [Security Guide](Security-Guide) for complete hardening instructions.

### 2. Backup Configuration

```bash
# Set up automated backups
# Test restore procedure
# Document configuration
```

See [Backup & Recovery](Backup-Recovery) for details.

### 3. Performance Tuning

```yaml
# Adjust polling intervals
# Configure data retention
# Optimize database
# Set resource limits
```

See [Performance Tuning](Performance-Tuning) for details.

## Next Steps

After completing setup:

1. **Explore the Dashboard**: [Dashboard Overview](Dashboard-Overview)
2. **Add More Devices**: [Device Management](Device-Management)
3. **Monitor Energy**: [Energy Monitoring](Energy-Monitoring)
4. **Analyze Costs**: [Cost Analysis](Cost-Analysis)
5. **Create Users**: [User Management](User-Management)

## Tips for Success

1. **Document Everything**: Keep notes of your configuration
2. **Regular Backups**: Set up automated backups early
3. **Monitor Regularly**: Check dashboard weekly
4. **Update Rates**: When utility rates change
5. **Optimize Usage**: Use insights to save money

## Getting Help

- [FAQ](FAQ) - Common questions
- [Common Issues](Common-Issues) - Troubleshooting
- [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues) - Bug reports
- [Discussions](https://github.com/xante8088/kasa-monitor/discussions) - Community help

---

**Document Version:** 1.1.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Added essential security configuration steps for JWT, CORS, file uploads, and database credentials