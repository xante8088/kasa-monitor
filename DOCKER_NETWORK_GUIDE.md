# Docker Network Configuration Guide

This guide explains the different network configurations available for Kasa Monitor when running in Docker.

## Quick Start

Choose the network mode that best fits your needs:

| Mode | Discovery | Isolation | Complexity | Best For |
|------|-----------|-----------|------------|----------|
| **Host** | ✅ Full | ❌ None | Easy | Home servers, Raspberry Pi |
| **Macvlan** | ✅ Full | ✅ Good | Medium | Advanced users, production |
| **Bridge** | ❌ Manual only | ✅ Best | Easy | Security-focused, testing |

## Network Modes

### 1. Host Network Mode (Recommended for Raspberry Pi)

**File:** `docker-compose.host.yml`

```bash
docker-compose -f docker-compose.host.yml up -d
```

**Pros:**
- ✅ Automatic device discovery works perfectly
- ✅ Simple setup, no configuration needed
- ✅ Can still use manual IP entry as backup
- ✅ Best performance, no network overhead

**Cons:**
- ❌ No network isolation (container uses host network)
- ❌ Port conflicts possible with host services
- ❌ Only works on Linux (not Docker Desktop for Mac/Windows)

**When to use:**
- Running on Raspberry Pi or dedicated Linux server
- You want the simplest setup that "just works"
- Network isolation is not a concern

### 2. Macvlan Network Mode (Advanced)

**File:** `docker-compose.macvlan.yml`

**Setup Required:**
1. Find your network interface:
   ```bash
   ip link show
   # Look for eth0 (ethernet) or wlan0 (wifi)
   ```

2. Edit `docker-compose.macvlan.yml`:
   ```yaml
   networks:
     macvlan_net:
       driver_opts:
         parent: eth0  # Change to your interface
       ipam:
         config:
           - subnet: 192.168.1.0/24    # Your network subnet
             gateway: 192.168.1.1       # Your router IP
   ```

3. Run:
   ```bash
   docker-compose -f docker-compose.macvlan.yml up -d
   ```

4. Find container IP:
   ```bash
   docker inspect kasa-monitor | grep IPAddress
   ```

5. Access via: `http://CONTAINER_IP:3000` (Frontend) or `http://CONTAINER_IP:5272` (API)

**Pros:**
- ✅ Automatic device discovery works
- ✅ Good network isolation
- ✅ Container gets real LAN IP address
- ✅ Can communicate with all network devices

**Cons:**
- ❌ More complex setup
- ❌ Requires network configuration knowledge
- ❌ Container IP may change on restart

**When to use:**
- You need both discovery and isolation
- Running multiple containers that need LAN access
- Production environments

### 3. Bridge Network Mode (Default)

**File:** `docker-compose.yml` (default)

```bash
docker-compose up -d
```

**Access:** `http://localhost:3000` (Frontend) or `http://localhost:5272` (API)

**Pros:**
- ✅ Best security and isolation
- ✅ Standard Docker networking
- ✅ Works on all platforms
- ✅ Predictable port mapping

**Cons:**
- ❌ No automatic device discovery
- ❌ Must manually add devices by IP
- ❌ Cannot see UDP broadcasts

**When to use:**
- Security is top priority
- You know your device IP addresses
- Testing or development
- Running on Docker Desktop (Mac/Windows)

## Manual Device Entry

All network modes support manual device entry. This is especially useful for:
- Bridge mode (where discovery doesn't work)
- Adding devices on different subnets
- Troubleshooting discovery issues

### How to add devices manually:

1. Open Kasa Monitor web interface
2. Click the settings icon → "Device Management"
3. Click "Add Device Manually"
4. Enter the device IP address (e.g., `192.168.1.100`)
5. Optionally add a custom name
6. Click "Add"

### Finding device IP addresses:

**Option 1: Check your router**
- Login to router admin panel
- Look for connected devices/DHCP clients
- Find devices named "HS" or "KL" (Kasa devices)

**Option 2: Use Kasa mobile app**
- Open device settings in Kasa app
- Look for "Device Info" → "IP Address"

**Option 3: Network scan** (Linux/Mac)
```bash
# Scan local network
nmap -sn 192.168.1.0/24

# Or use arp
arp -a | grep -i "TP-LINK"
```

## Environment Variables

All modes support these environment variables:

```yaml
environment:
  # Network configuration
  - NETWORK_MODE=bridge          # bridge, host, or macvlan
  - DISCOVERY_ENABLED=false       # Enable/disable auto-discovery
  - MANUAL_DEVICES_ENABLED=true   # Enable/disable manual IP entry
  
  # Optional: TP-Link Cloud (works in all modes)
  - TPLINK_USERNAME=your@email.com
  - TPLINK_PASSWORD=yourpassword
```

## Troubleshooting

### Devices not discovered (Host/Macvlan mode)

1. Check firewall isn't blocking UDP port 9999:
   ```bash
   sudo ufw allow 9999/udp
   ```

2. Verify container can ping devices:
   ```bash
   docker exec kasa-monitor ping 192.168.1.100
   ```

3. Check container logs:
   ```bash
   docker logs kasa-monitor
   ```

### Cannot connect to manually added device

1. Verify device IP is correct
2. Ensure device is on same network/VLAN
3. Check device is powered on and connected to WiFi
4. Try pinging from container:
   ```bash
   docker exec kasa-monitor ping DEVICE_IP
   ```

### Bridge mode: Want discovery but have to use bridge

Consider these workarounds:
1. Use manual IP entry for all devices
2. Set up a UDP relay service (advanced)
3. Use TP-Link cloud credentials (if devices are cloud-connected)
4. Switch to host or macvlan mode if possible

## Security Considerations

- **Host mode:** Container has full network access. Only use on trusted networks.
- **Macvlan:** Good balance of functionality and isolation.
- **Bridge:** Most secure but requires manual configuration.

Always use strong passwords and consider enabling HTTPS in production.

## Performance Tips

- Host mode has best performance (no NAT overhead)
- Macvlan has minimal overhead
- Bridge mode adds slight latency due to NAT

For Raspberry Pi, use these environment variables:
```yaml
environment:
  - NODE_OPTIONS=--max-old-space-size=1024
  - PYTHONUNBUFFERED=1
```

## Need Help?

Check the logs:
```bash
docker logs kasa-monitor
```

Restart the container:
```bash
docker-compose -f docker-compose.[mode].yml restart
```

For more help, see the main README or open an issue on GitHub.