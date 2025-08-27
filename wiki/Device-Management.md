# Device Management

Complete guide for adding, configuring, and managing your Kasa smart devices.

## Adding Devices

### Automatic Discovery

**Requirements**: Host or Macvlan network mode

1. Click **Discover Devices** button (🔍)
2. Wait for scan (typically 5-10 seconds)
3. Found devices appear automatically
4. Devices are saved to database

**Discovery Process**:
```
Broadcast UDP → Port 9999 → Device responds → Add to list
```

### Manual Entry

**Works in any network mode**

1. Click Settings (⚙️) → **Device Management**
2. Click **Add Device Manually**
3. Enter device information:
   - **IP Address**: Required (e.g., `192.168.1.100`)
   - **Device Name**: Optional custom name
4. Click **Add**

**Finding Device IPs**:

#### Method 1: Router Admin Panel
```
1. Access router (usually 192.168.1.1)
2. Find "Connected Devices" or "DHCP Clients"
3. Look for devices starting with "HS", "KL", or "KP"
4. Note the IP addresses
```

#### Method 2: Kasa Mobile App
```
1. Open Kasa app
2. Tap device → Settings
3. Select "Device Info"
4. Find "IP Address"
```

#### Method 3: Network Scan
```bash
# Linux/Mac
nmap -sn 192.168.1.0/24 | grep -B2 "TP-LINK"

# Windows (PowerShell)
arp -a | findstr "TP-LINK"

# Using fing (mobile app)
Scan network → Filter by manufacturer
```

### Cloud-Connected Devices

For devices only accessible via cloud:

1. Go to Settings → **TP-Link Cloud**
2. Enter credentials:
   - Email/Username
   - Password
3. Click **Connect**
4. Cloud devices sync automatically

**Note**: Local connection preferred for lower latency.

## Device Configuration

### Basic Settings

Access via device card → **Details** → **Settings**:

- **Device Name**: Custom alias
- **Location**: Room/zone assignment
- **Icon**: Visual identifier
- **Notes**: Additional information

### Network Settings

- **IP Address**: Static recommended
- **Connection Type**: Local/Cloud
- **Polling Interval**: Update frequency
- **Timeout**: Connection timeout

### Energy Settings

For devices with power monitoring:

- **Calibration Factor**: Adjust accuracy
- **Standby Threshold**: Define "off" wattage
- **Cost Override**: Device-specific rates
- **Reset Schedule**: Monthly/weekly reset

## Managing Devices

### Device List View

The device management interface shows:

| Status | Name | Model | IP | Power | Last Seen | Actions |
|--------|------|-------|-----|-------|-----------|---------|
| 🟢 | Living Room | HS110 | 192.168.1.100 | 45W | Just now | View/Edit/Export/Delete |
| 🟢 | Kitchen | KP115 | 192.168.1.101 | 0W | 1 min ago | View/Edit/Export/Delete |
| 🔴 | Bedroom | HS105 | 192.168.1.102 | - | 1 hour ago | View/Edit/Export/Delete |

### Device Details View (Enhanced v1.2.1)

**Time Period Selection:**
Each chart in the device details view now includes individual time period selectors:
- Power consumption chart with 24h/7d/30d/3m/6m/1y/custom options
- Energy usage chart with intelligent aggregation
- Cost analysis chart with period-based calculations

**Chart Features:**
- Automatic data aggregation based on selected period
- Responsive design for mobile devices
- Export data for selected period
- Print-friendly view option

### Editing Devices

1. Click **Edit** (✏️) button
2. Modify settings:
   - Device name
   - IP address (if changed)
   - Room assignment
   - Custom notes
3. Click **Save**

### Removing Devices

1. Click **Delete** (🗑️) button
2. Confirm removal
3. Choose data handling:
   - **Keep History**: Preserve historical data
   - **Delete All**: Remove all associated data

### Bulk Operations

Select multiple devices:
- **Turn All On/Off**
- **Group Assignment**
- **Export Configuration**
- **Bulk Delete**

## Device Groups

### Creating Groups

1. Go to **Device Management**
2. Click **Create Group**
3. Configure:
   - Group name
   - Select devices
   - Set permissions
4. Save group

### Group Examples

- **Living Room**: All living room devices
- **Lights**: All smart bulbs
- **High Power**: Devices > 100W
- **Night Mode**: Bedroom devices

### Group Actions

- Toggle all devices
- Schedule operations
- Apply settings
- Monitor as unit

## Device Types

### Smart Plugs

**Models**: HS103, HS105, HS110, KP115, KP125, EP10, EP25

Features:
- On/off control
- Energy monitoring (select models)
- Schedule support
- Away mode

Configuration:
- Default state on power loss
- LED indicator settings
- Child lock

### Smart Switches

**Models**: HS200, HS210, HS220, KS200M, KS220M

Features:
- Wall switch replacement
- Dimming (HS220)
- 3-way support (HS210)
- Motion sensing (KS200M)

Configuration:
- Fade on/off
- Double-tap actions
- Minimum brightness
- Motion sensitivity

### Smart Bulbs

**Models**: KL110, KL120, KL130, LB100, LB110, LB130

Features:
- Brightness control
- Color temperature (select)
- RGB color (KL130, LB130)
- Scenes

Configuration:
- Default power-on state
- Transition time
- Circadian rhythm
- Color presets

### Power Strips

**Models**: HS300, KP303, KP400, HS107

Features:
- Individual outlet control
- USB port control
- Energy monitoring per outlet
- Master/slave outlets

Configuration:
- Outlet naming
- Power sequencing
- USB always-on
- Safety shutoff

## Advanced Features

### Scheduling

Create schedules per device:

```yaml
Schedule: "Morning Coffee"
Device: Kitchen Coffee Maker
Actions:
  - Time: 6:30 AM
    Action: Turn On
  - Time: 7:30 AM
    Action: Turn Off
Days: Mon-Fri
```

### Scenes

Combine multiple devices:

```yaml
Scene: "Movie Time"
Devices:
  - Living Room TV: On
  - Living Room Lamp: 20% brightness
  - Kitchen Lights: Off
Trigger: Manual or scheduled
```

### Automation Rules

Set up conditional triggers:

```yaml
Rule: "High Power Alert"
Condition: Total power > 3000W
Action: 
  - Send notification
  - Turn off non-essential devices
```

### Firmware Updates

1. Check device details for version
2. Compare with latest on TP-Link site
3. Update via Kasa mobile app
4. Verify functionality after update

## Monitoring & Alerts

### Device Health

Monitor device status:
- **Response Time**: Network latency
- **Uptime**: Since last restart
- **Error Rate**: Failed commands
- **Signal Strength**: WiFi RSSI

### Alert Configuration

Set up notifications for:
- Device offline > 5 minutes
- High power consumption
- Unusual usage patterns
- Firmware updates available

### Logging

View device logs:
```
2024-01-15 10:30:15 - Device online
2024-01-15 10:30:20 - State changed: ON
2024-01-15 10:30:20 - Power reading: 45.2W
2024-01-15 11:45:30 - State changed: OFF
```

## Troubleshooting

### Device Not Responding

1. **Check Power**: Ensure device is plugged in
2. **Network Test**: Ping device IP
3. **Restart Device**: Power cycle
4. **Re-add**: Remove and add again
5. **Factory Reset**: Last resort

### Discovery Not Working

1. **Network Mode**: Verify using host/macvlan
2. **Firewall**: Allow UDP port 9999
3. **Same Network**: Confirm same subnet
4. **Manual Add**: Use IP address

### Incorrect Readings

1. **Calibrate**: Adjust calibration factor
2. **Firmware**: Update device firmware
3. **Reset Stats**: Clear and restart
4. **Replace**: Device may be faulty

### Connection Issues

```bash
# Test connectivity
ping 192.168.1.100

# Check port
nc -zv 192.168.1.100 9999

# View network config
ip addr show

# Check firewall
sudo iptables -L
```

## Best Practices

### Network Configuration

1. **Use Static IPs**: Prevent IP changes
2. **Separate VLAN**: Isolate IoT devices
3. **Strong WiFi**: Ensure good signal
4. **Regular Reboots**: Monthly router restart

### Security

1. **Change Default Names**: Don't use "Smart Plug 1"
2. **Firmware Updates**: Keep current
3. **Network Isolation**: IoT VLAN
4. **Access Control**: Limit who can control

### Organization

1. **Logical Naming**: "Kitchen Coffee Maker"
2. **Room Groups**: Organize by location
3. **Document IPs**: Keep spreadsheet
4. **Label Physical**: Mark devices

### Maintenance

1. **Regular Checks**: Weekly status review
2. **Clean Database**: Remove old devices
3. **Backup Config**: Export settings
4. **Test Schedules**: Verify automation

## API Integration

### List Devices
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5272/api/devices
```

### Add Device
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip":"192.168.1.100","alias":"New Device"}' \
  http://localhost:5272/api/devices/manual
```

### Control Device
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"toggle"}' \
  http://localhost:5272/api/device/192.168.1.100/control
```

## Related Pages

- [Network Configuration](Network-Configuration) - Network setup guide
- [Energy Monitoring](Energy-Monitoring) - Track consumption
- [Dashboard Overview](Dashboard-Overview) - Main interface
- [API Documentation](API-Documentation) - Developer reference

## Getting Help

- Check [FAQ](FAQ) first
- Review [Common Issues](Common-Issues)
- Search [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)
- Ask in [Discussions](https://github.com/xante8088/kasa-monitor/discussions)

---

**Document Version:** 1.1.0  
**Last Updated:** 2025-08-27  
**Review Status:** Current  
**Change Summary:** Updated for v1.2.1 with enhanced device details view featuring time period selectors and improved chart capabilities