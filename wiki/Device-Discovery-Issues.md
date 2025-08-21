# Device Discovery Issues

Troubleshooting guide for common device discovery problems in Kasa Monitor.

## Discovery Overview

```
┌─────────────────────────────────────┐
│     Discovery Process Flow          │
├─────────────────────────────────────┤
│  1. Broadcast UDP packet            │
│  2. Listen for responses            │
│  3. Parse device information        │
│  4. Connect to device               │
│  5. Add to monitoring               │
└─────────────────────────────────────┘
```

## Common Issues

### No Devices Found

**Symptoms:**
- Discovery returns 0 devices
- "No devices discovered" message
- Empty device list

**Solutions:**

#### 1. Check Network Mode (Docker)

```bash
# Host network mode (recommended for discovery)
docker run --network host xante8088/kasa-monitor

# Or in docker-compose
services:
  kasa-monitor:
    network_mode: host
```

#### 2. Verify Network Connectivity

```bash
# Test broadcast capability
docker exec kasa-monitor python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.sendto(b'test', ('255.255.255.255', 9999))
print('Broadcast test successful')
"

# Check network interfaces
docker exec kasa-monitor ip addr show

# Test specific subnet
docker exec kasa-monitor ping -b 192.168.1.255
```

#### 3. Firewall Configuration

```bash
# Allow UDP port 9999
sudo ufw allow 9999/udp

# iptables rule
sudo iptables -A INPUT -p udp --dport 9999 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 9999 -j ACCEPT

# Check if port is open
sudo netstat -lutn | grep 9999
```

#### 4. Manual Device Addition

```python
# If discovery fails, add devices manually
curl -X POST http://localhost:5272/api/devices/manual \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "alias": "Living Room Plug"
  }'
```

### Devices Found but Not Connecting

**Symptoms:**
- Devices appear in discovery
- Connection fails
- "Device unreachable" errors

**Solutions:**

#### 1. Check Device Compatibility

```python
# Supported models
SUPPORTED_MODELS = [
    'HS100', 'HS103', 'HS105', 'HS107', 'HS110',
    'HS200', 'HS210', 'HS220',
    'HS300',
    'KP100', 'KP105', 'KP115', 'KP125',
    'KP200', 'KP303', 'KP400',
    'EP10', 'EP40',
    'KL110', 'KL120', 'KL125', 'KL130', 'KL135',
    'LB100', 'LB110', 'LB120', 'LB130'
]
```

#### 2. Verify Port Access

```bash
# Test TCP connection to device
docker exec kasa-monitor nc -zv 192.168.1.100 9999

# Test with Python
docker exec kasa-monitor python3 -c "
import socket
s = socket.socket()
s.settimeout(5)
try:
    s.connect(('192.168.1.100', 9999))
    print('Connection successful')
except:
    print('Connection failed')
"
```

#### 3. Check Device Firmware

```bash
# Get device info directly
docker exec kasa-monitor python3 -c "
from kasa import SmartPlug
import asyncio

async def check():
    plug = SmartPlug('192.168.1.100')
    await plug.update()
    print(f'Model: {plug.model}')
    print(f'Firmware: {plug.firmware_version}')
    print(f'Hardware: {plug.hardware_version}')

asyncio.run(check())
"
```

### Intermittent Discovery

**Symptoms:**
- Sometimes finds devices, sometimes doesn't
- Inconsistent device count
- Devices appear and disappear

**Solutions:**

#### 1. Increase Discovery Timeout

```python
# config/discovery.yml
discovery:
  timeout: 10  # Increase from default 5
  retries: 3
  broadcast_address: 255.255.255.255
```

#### 2. Multiple Discovery Attempts

```bash
# Run discovery multiple times
for i in {1..3}; do
  echo "Discovery attempt $i"
  curl http://localhost:5272/api/devices/discover
  sleep 2
done
```

#### 3. Network Stability

```bash
# Check for packet loss
ping -c 100 192.168.1.100

# Monitor network traffic
docker exec kasa-monitor tcpdump -i any -n port 9999

# Check ARP table
arp -a | grep -i "kasa\|tp-link"
```

## Docker-Specific Issues

### Container Network Isolation

**Problem:** Default bridge network prevents broadcast

**Solution 1: Host Network**
```yaml
# docker-compose.yml
services:
  kasa-monitor:
    network_mode: host
```

**Solution 2: Macvlan Network**
```bash
# Create macvlan network
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  kasa-macvlan

# Use in container
docker run --network kasa-macvlan \
  --ip 192.168.1.200 \
  xante8088/kasa-monitor
```

**Solution 3: Custom Bridge with Broadcast**
```yaml
# docker-compose.yml
services:
  kasa-monitor:
    cap_add:
      - NET_ADMIN
      - NET_RAW
    sysctls:
      - net.ipv4.conf.all.src_valid_mark=1
```

### Permission Issues

```bash
# Add necessary capabilities
docker run --cap-add=NET_ADMIN --cap-add=NET_RAW xante8088/kasa-monitor

# Or in docker-compose
cap_add:
  - NET_ADMIN
  - NET_RAW
  - NET_BROADCAST
```

## Network Configuration Issues

### VLAN Separation

**Problem:** Devices on different VLAN than monitor

**Solution:**
```bash
# Configure VLAN interface
sudo ip link add link eth0 name eth0.10 type vlan id 10
sudo ip addr add 192.168.10.2/24 dev eth0.10
sudo ip link set dev eth0.10 up

# Route between VLANs
sudo ip route add 192.168.10.0/24 via 192.168.1.1
```

### Multiple Network Interfaces

```python
# Specify interface for discovery
DISCOVERY_INTERFACE = "eth0"  # or "wlan0", "ens33", etc.

# Test specific interface
import socket
import struct

def discover_on_interface(interface):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, 
                    interface.encode())
    
    message = struct.pack('>I', 0x02000000)
    sock.sendto(message, ('255.255.255.255', 9999))
```

### Subnet Issues

```bash
# Wrong subnet configuration
# Devices: 192.168.1.x
# Monitor: 192.168.0.x

# Solution: Add route
sudo ip route add 192.168.1.0/24 via 192.168.0.1

# Or use specific broadcast
DISCOVERY_BROADCAST_ADDRESS=192.168.1.255
```

## Advanced Troubleshooting

### Packet Capture Analysis

```bash
# Capture discovery packets
docker exec kasa-monitor tcpdump -i any -w /tmp/discovery.pcap \
  -s 0 'udp port 9999'

# Copy and analyze
docker cp kasa-monitor:/tmp/discovery.pcap .
wireshark discovery.pcap

# Look for:
# - Outgoing broadcast packets
# - Incoming responses
# - Correct IP addresses
```

### Debug Mode Discovery

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

from kasa import Discover
import asyncio

async def debug_discover():
    logging.info("Starting discovery...")
    
    devices = await Discover.discover(
        target='255.255.255.255',
        timeout=10,
        discovery_packets=5
    )
    
    for ip, device in devices.items():
        logging.info(f"Found: {ip} - {device}")
    
    return devices

devices = asyncio.run(debug_discover())
```

### Manual Discovery Protocol

```python
import socket
import json
import struct

def manual_discover():
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5)
    
    # Discovery packet
    message = bytes.fromhex('020000010000000000000000463cb5c3')
    
    # Send broadcast
    sock.sendto(message, ('255.255.255.255', 9999))
    
    # Listen for responses
    devices = []
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            devices.append({
                'ip': addr[0],
                'data': data.hex()
            })
    except socket.timeout:
        pass
    
    return devices
```

## Device-Specific Issues

### Kasa Device Firmware Updates

Some devices may need firmware updates for discovery:

```bash
# Check current firmware
curl http://192.168.1.100/api/system

# Update through Kasa app
# 1. Open Kasa app
# 2. Select device
# 3. Settings → Device Info
# 4. Check for firmware updates
```

### Regional Variants

```python
# Some regions use different ports
REGIONAL_PORTS = {
    'US': 9999,
    'EU': 9999,
    'CN': 9999,  # May differ
}

# Try multiple ports
for port in [9999, 9998, 5272]:
    try:
        discover(port=port)
    except:
        continue
```

## Diagnostic Script

```bash
#!/bin/bash
# diagnose-discovery.sh

echo "=== Kasa Monitor Discovery Diagnostics ==="

# Check network mode
echo -n "Network mode: "
docker inspect kasa-monitor | grep -i networkmode

# Check IP configuration
echo "Container IP:"
docker exec kasa-monitor ip addr show

# Test broadcast
echo "Testing broadcast capability..."
docker exec kasa-monitor python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(b'test', ('255.255.255.255', 9999))
    print('✓ Broadcast capable')
except Exception as e:
    print('✗ Broadcast failed:', e)
"

# Check firewall
echo "Firewall status:"
sudo ufw status | grep 9999

# Try discovery
echo "Running discovery..."
curl -s http://localhost:5272/api/devices/discover | jq .

# Check logs
echo "Recent discovery logs:"
docker logs kasa-monitor 2>&1 | grep -i "discover" | tail -10
```

## Prevention Tips

1. **Use Host Network Mode** for Docker deployments
2. **Document Network Configuration** including VLANs and subnets
3. **Test Discovery After Updates** to catch breaking changes
4. **Maintain Device Inventory** with manual entries as backup
5. **Monitor Discovery Success Rate** with metrics
6. **Keep Firmware Updated** on both monitor and devices

## Related Pages

- [Network Configuration](Network-Configuration) - Network setup guide
- [Docker Deployment](Docker-Deployment) - Container networking
- [Common Issues](Common-Issues) - General troubleshooting
- [API Documentation](API-Documentation) - Discovery API endpoints

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added