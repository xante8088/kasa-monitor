# Quick Start Guide

Get Kasa Monitor up and running in 5 minutes!

## 🚀 Fastest Setup (Docker)

### Step 1: Run the Container

```bash
docker run -d \
  --name kasa-monitor \
  --network host \
  -v kasa_data:/app/data \
  xante8088/kasa-monitor:latest
```

**Note**: Use `--network host` for automatic device discovery (Linux only).

### Step 2: Access the Application

Open your browser and navigate to:
```
Frontend: http://localhost:3000
Backend API: http://localhost:5272
```

**Note**: The frontend (React app) runs on port 3000, while the backend API runs on port 5272. For most users, you'll primarily use the frontend interface.

### Step 3: Create Admin Account

1. You'll be redirected to `/setup`
2. Enter your admin credentials:
   - Username
   - Email
   - Password
3. Click "Create Admin Account"

### Step 4: Configure Electricity Rates

1. Click Settings (⚙️) → "Electricity Rates"
2. Enter your rate information:
   - **Simple Rate**: Single $/kWh rate
   - **Time-of-Use**: Different rates by time
   - **Tiered**: Different rates by usage level
3. Save your configuration

### Step 5: Add Your Devices

#### Automatic Discovery (Host/Macvlan network)
1. Click "Discover Devices" (🔍)
2. Wait for scan to complete
3. Your devices appear automatically

#### Manual Entry (Any network mode)
1. Click Settings (⚙️) → "Device Management"
2. Click "Add Device Manually"
3. Enter device IP address (e.g., `192.168.1.100`)
4. Click "Add"

## 📱 Using the Dashboard

### Main View
- **Device Grid**: See all your devices at a glance
- **Power Status**: Green = On, Gray = Off
- **Current Usage**: Real-time power consumption
- **Daily Cost**: Today's electricity cost

### Device Details
Click any device to see:
- 24-hour power graph
- Current consumption
- Daily/monthly statistics
- Cost breakdown
- On/off control

### Cost Summary
Top of dashboard shows:
- Total daily cost
- Monthly projection
- Peak usage times
- Device rankings by cost

## 🎯 Common Tasks

### Finding Device IP Addresses

**Option 1: Router Admin Panel**
1. Log into your router (usually `192.168.1.1`)
2. Look for "Connected Devices" or "DHCP Clients"
3. Find devices starting with "HS" or "KL"

**Option 2: Kasa Mobile App**
1. Open the Kasa app
2. Tap on a device
3. Go to Settings → Device Info
4. Note the IP address

**Option 3: Network Scan**
```bash
# Linux/Mac
nmap -sn 192.168.1.0/24 | grep -B2 "TP-LINK"

# Or use arp
arp -a | grep -i "tp-link"
```

### Controlling Devices

1. **From Dashboard**: Click power button on device card
2. **From Detail View**: Use large power toggle
3. **Bulk Actions**: Select multiple devices → Apply action

### Viewing Historical Data

1. Click on any device
2. Use time range selector:
   - Last 24 hours
   - Last 7 days
   - Last 30 days
   - Custom range
3. Export data as CSV for analysis

## 🐳 Docker Compose Setup

For more control, use Docker Compose:

1. **Create `docker-compose.yml`**:
```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    container_name: kasa-monitor
    network_mode: host  # For discovery
    volumes:
      - kasa_data:/app/data
    environment:
      - TZ=America/New_York  # Your timezone
    restart: unless-stopped

volumes:
  kasa_data:
```

2. **Start the stack**:
```bash
docker-compose up -d
```

3. **View logs**:
```bash
docker-compose logs -f
```

## 🔧 Environment Options

### Basic Configuration
```yaml
environment:
  - TZ=America/New_York           # Your timezone
  - DISCOVERY_ENABLED=true         # Auto-discovery
  - MANUAL_DEVICES_ENABLED=true    # Manual IP entry
```

### With TP-Link Cloud
```yaml
environment:
  - TPLINK_USERNAME=your@email.com
  - TPLINK_PASSWORD=yourpassword
```

### With InfluxDB (Advanced)
```yaml
environment:
  - INFLUXDB_URL=http://localhost:8086
  - INFLUXDB_TOKEN=your-token
  - INFLUXDB_ORG=kasa-monitor
  - INFLUXDB_BUCKET=device-data
```

## ❓ Quick Troubleshooting

### Can't Find Devices?

1. **Check network mode**:
   - Bridge mode = No discovery (use manual entry)
   - Host mode = Full discovery
   - See [Network Configuration](Network-Configuration)

2. **Verify device connectivity**:
```bash
ping 192.168.1.100  # Your device IP
```

3. **Add manually**:
   - Settings → Device Management → Add Device Manually

### Can't Access Web Interface?

1. **Check container is running**:
```bash
docker ps
```

2. **Check logs**:
```bash
docker logs kasa-monitor
```

3. **Verify ports**:
```bash
curl http://localhost:3000
curl http://localhost:8000/api/devices
```

### Forgot Admin Password?

1. **Stop the container**:
```bash
docker stop kasa-monitor
```

2. **Reset database**:
```bash
docker run --rm -v kasa_data:/data alpine \
  rm /data/kasa_monitor.db
```

3. **Restart and setup again**:
```bash
docker start kasa-monitor
```

## 📚 Next Steps

Now that you're up and running:

1. **Explore Features**:
   - [Energy Monitoring](Energy-Monitoring) - Track consumption patterns
   - [Cost Analysis](Cost-Analysis) - Understand your bills
   - [User Management](User-Management) - Add family members

2. **Optimize Setup**:
   - [Security Guide](Security-Guide) - Secure your installation
   - [Backup & Recovery](Backup-Recovery) - Protect your data
   - [Performance Tuning](Performance-Tuning) - Optimize for your hardware

3. **Get Help**:
   - [FAQ](FAQ) - Common questions
   - [Common Issues](Common-Issues) - Troubleshooting
   - [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues) - Report bugs

## 🎉 Success Checklist

- [ ] Container running
- [ ] Web interface accessible
- [ ] Admin account created
- [ ] Electricity rates configured
- [ ] At least one device added
- [ ] Real-time data visible
- [ ] Cost calculations working

## 🔧 Quick Troubleshooting

### Can't Access the Application?
- **Check ports**: Frontend (3000) and Backend (5272) should be accessible
- **Firewall**: Make sure Docker ports aren't blocked
- **Container status**: Run `docker ps` to verify the container is running

### Devices Not Found?
- **Network**: Ensure devices are on the same subnet as the Docker host
- **Discovery**: Try manual device addition using IP addresses
- **Permissions**: On Linux, ensure Docker has network access

### Performance Issues?
- **Resources**: Check Docker container has sufficient memory (512MB+ recommended)
- **Database**: Large amounts of historical data may slow queries
- **Network**: Reduce polling frequency in settings if needed

Need more help? Check the [Common Issues](Common-Issues.md) guide.

Congratulations! You're now monitoring your smart home energy usage! 🏠⚡

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Added port clarification, troubleshooting section, and improved setup instructions