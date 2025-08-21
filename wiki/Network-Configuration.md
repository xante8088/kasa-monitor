# Network Configuration

Complete guide to Docker network modes and device discovery configuration.

## Network Mode Overview

| Mode | Discovery | Security | Complexity | Best For |
|------|-----------|----------|------------|----------|
| **Host** | ✅ Full | ❌ Low | Easy | Home use, Raspberry Pi |
| **Macvlan** | ✅ Full | ✅ Good | Medium | Production, advanced users |
| **Bridge** | ❌ None | ✅ High | Easy | Security-focused, cloud |

## Host Network Mode

### Overview

Container shares host's network stack directly.

**Pros:**
- ✅ Full device discovery
- ✅ Simple setup
- ✅ Best performance
- ✅ No NAT overhead

**Cons:**
- ❌ No network isolation
- ❌ Port conflicts possible
- ❌ Linux only (no Docker Desktop)

### Configuration

**File:** `docker-compose.host.yml`

```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    container_name: kasa-monitor
    network_mode: host  # Key setting
    volumes:
      - kasa_data:/app/data
    environment:
      - NETWORK_MODE=host
      - DISCOVERY_ENABLED=true
    restart: unless-stopped
```

### Deployment

```bash
# Download configuration
curl -O https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.host.yml

# Start container
docker-compose -f docker-compose.host.yml up -d

# Access application
http://localhost:3000
```

### Verification

```bash
# Check network mode
docker inspect kasa-monitor | grep NetworkMode
# Should show: "NetworkMode": "host"

# Test discovery
docker exec kasa-monitor python3 -c "
from kasa import Discover
import asyncio
devices = asyncio.run(Discover.discover())
print(f'Found {len(devices)} devices')
"
```

## Macvlan Network Mode

### Overview

Container gets its own MAC address and IP on the LAN.

**Pros:**
- ✅ Full discovery support
- ✅ Network isolation
- ✅ Real LAN IP address
- ✅ Direct device communication

**Cons:**
- ❌ Complex setup
- ❌ Requires network knowledge
- ❌ Host cannot access container directly

### Configuration

**File:** `docker-compose.macvlan.yml`

```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    container_name: kasa-monitor
    networks:
      macvlan_net:
        ipv4_address: 192.168.1.100  # Optional static IP
    volumes:
      - kasa_data:/app/data
    environment:
      - NETWORK_MODE=macvlan
      - DISCOVERY_ENABLED=true

networks:
  macvlan_net:
    driver: macvlan
    driver_opts:
      parent: eth0  # Your network interface
    ipam:
      config:
        - subnet: 192.168.1.0/24    # Your network
          gateway: 192.168.1.1       # Your router
          ip_range: 192.168.1.128/25 # Container IP range
```

### Setup Steps

#### 1. Find Network Interface

```bash
# List interfaces
ip link show

# Common names:
# eth0 - Ethernet
# wlan0 - WiFi
# ens33 - VMware
# enp0s3 - VirtualBox
```

#### 2. Get Network Details

```bash
# Get subnet and gateway
ip route | grep default
# Shows: default via 192.168.1.1 dev eth0

# Get current IP range
ip addr show eth0
# Shows: inet 192.168.1.50/24
```

#### 3. Create Macvlan Network

```bash
# Create network manually
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  --ip-range=192.168.1.128/25 \
  -o parent=eth0 \
  macvlan_net
```

#### 4. Deploy Container

```bash
# Start with macvlan
docker-compose -f docker-compose.macvlan.yml up -d

# Find container IP
docker inspect kasa-monitor | grep IPAddress
```

#### 5. Enable Host Communication

```bash
# Create macvlan interface on host
sudo ip link add macvlan-host link eth0 type macvlan mode bridge
sudo ip addr add 192.168.1.200/32 dev macvlan-host
sudo ip link set macvlan-host up
sudo ip route add 192.168.1.100 dev macvlan-host
```

### Access Application

```
http://192.168.1.100:3000  # Container's IP
```

## Bridge Network Mode

### Overview

Default Docker networking with NAT.

**Pros:**
- ✅ Maximum isolation
- ✅ Simple port mapping
- ✅ Works everywhere
- ✅ Most secure

**Cons:**
- ❌ No automatic discovery
- ❌ Requires manual device entry
- ❌ Cannot see UDP broadcasts

### Configuration

**File:** `docker-compose.bridge.yml` (or default `docker-compose.yml`)

```yaml
version: '3.8'

services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    container_name: kasa-monitor
    ports:
      - "3000:3000"  # Frontend
      - "5272:5272"  # API
    networks:
      - kasa-network
    volumes:
      - kasa_data:/app/data
    environment:
      - NETWORK_MODE=bridge
      - DISCOVERY_ENABLED=false  # Won't work
      - MANUAL_DEVICES_ENABLED=true  # Required
    extra_hosts:
      - "host.docker.internal:host-gateway"

networks:
  kasa-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Manual Device Entry

Since discovery doesn't work in bridge mode:

1. **Find device IPs** (from host machine):
```bash
# Scan network
nmap -sn 192.168.1.0/24

# Or use arp
arp -a | grep -i "tp-link"
```

2. **Add devices manually**:
   - Open web interface
   - Settings → Device Management
   - Click "Add Device Manually"
   - Enter IP address
   - Save

### Bridge Mode Workarounds

#### Option 1: UDP Proxy

Run a proxy on the host:

```python
# udp_proxy.py - Run on host
import socket
import docker

# Forward UDP broadcasts from host to container
host_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
host_sock.bind(('0.0.0.0', 9999))

client = docker.from_env()
container = client.containers.get('kasa-monitor')
container_ip = container.attrs['NetworkSettings']['IPAddress']

while True:
    data, addr = host_sock.recvfrom(1024)
    # Forward to container
    container_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    container_sock.sendto(data, (container_ip, 9999))
```

#### Option 2: Host Network Sidecar

Run discovery in separate container:

```yaml
services:
  discovery:
    image: xante8088/kasa-discovery
    network_mode: host
    volumes:
      - device_list:/data
  
  kasa-monitor:
    image: xante8088/kasa-monitor
    volumes:
      - device_list:/data:ro
```

## Network Security

### Firewall Rules

#### For Discovery

```bash
# Allow UDP broadcast
sudo ufw allow 9999/udp

# Allow API access
sudo ufw allow 5272/tcp

# Allow web interface
sudo ufw allow 3000/tcp
```

#### For Isolation

```bash
# Create IoT VLAN
sudo ip link add link eth0 name eth0.10 type vlan id 10
sudo ip addr add 192.168.10.1/24 dev eth0.10
sudo ip link set dev eth0.10 up

# Firewall rules
sudo iptables -A FORWARD -i eth0.10 -o eth0 -j DROP
sudo iptables -A FORWARD -i eth0 -o eth0.10 -m state --state ESTABLISHED,RELATED -j ACCEPT
```

### Network Segmentation

Best practice setup:

```
Main Network: 192.168.1.0/24
  - Computers
  - Phones
  - Kasa Monitor Server

IoT Network: 192.168.10.0/24
  - Smart plugs
  - Smart bulbs
  - Smart switches

Rules:
  - IoT cannot access main
  - Main can access IoT
  - IoT cannot access internet (optional)
```

## Troubleshooting

### Discovery Not Working

#### Host Mode

```bash
# Check network mode
docker inspect kasa-monitor | grep NetworkMode

# Test UDP port
nc -u -l 9999  # In container
echo "test" | nc -u localhost 9999  # From host

# Check firewall
sudo iptables -L | grep 9999
```

#### Macvlan Mode

```bash
# Verify network
docker network ls | grep macvlan

# Check container IP
docker exec kasa-monitor ip addr

# Ping test
docker exec kasa-monitor ping 192.168.1.1

# ARP check
docker exec kasa-monitor arp -a
```

#### Bridge Mode

```bash
# Verify manual mode
docker exec kasa-monitor env | grep MANUAL_DEVICES

# Test connectivity to device
docker exec kasa-monitor ping 192.168.1.100

# Check routing
docker exec kasa-monitor ip route
```

### Container Cannot Reach Devices

```bash
# Check network connectivity
docker exec kasa-monitor ping 8.8.8.8  # Internet
docker exec kasa-monitor ping 192.168.1.1  # Router
docker exec kasa-monitor ping 192.168.1.100  # Device

# Check DNS
docker exec kasa-monitor nslookup google.com

# View network config
docker network inspect bridge
```

### Performance Issues

```bash
# Check network latency
docker exec kasa-monitor ping -c 10 192.168.1.100

# Monitor bandwidth
docker stats kasa-monitor

# Check dropped packets
docker exec kasa-monitor netstat -s | grep -i drop
```

## Advanced Configurations

### Multiple Networks

```yaml
services:
  kasa-monitor:
    networks:
      frontend:
        ipv4_address: 172.20.0.2
      backend:
        ipv4_address: 172.21.0.2
      iot:
        ipv4_address: 192.168.10.2

networks:
  frontend:
    external: true
  backend:
    internal: true
  iot:
    driver: macvlan
    driver_opts:
      parent: eth0.10
```

### IPv6 Support

```yaml
networks:
  kasa-network:
    enable_ipv6: true
    ipam:
      config:
        - subnet: 2001:db8::/64
          gateway: 2001:db8::1
```

### Custom DNS

```yaml
services:
  kasa-monitor:
    dns:
      - 8.8.8.8
      - 8.8.4.4
    dns_search:
      - local.domain
    extra_hosts:
      - "device1:192.168.1.100"
      - "device2:192.168.1.101"
```

## Best Practices

### For Home Use

1. Use **host mode** for simplicity
2. Enable firewall
3. Regular updates
4. Monitor logs

### For Production

1. Use **macvlan** for isolation
2. Implement VLANs
3. Set up monitoring
4. Document IP assignments

### For Development

1. Use **bridge mode**
2. Manual device entry
3. Mock devices for testing
4. Version control configs

## Quick Decision Guide

```
Need automatic discovery?
  ├─ Yes
  │   ├─ Need isolation?
  │   │   ├─ Yes → Macvlan
  │   │   └─ No → Host
  │   └─ Linux?
  │       ├─ Yes → Host
  │       └─ No → Macvlan
  └─ No → Bridge (with manual entry)
```

## Related Pages

- [Installation](Installation) - Initial setup
- [Device Management](Device-Management) - Adding devices
- [Docker Deployment](Docker-Deployment) - Container management
- [Security Guide](Security-Guide) - Security best practices

## Resources

- [Docker Networking](https://docs.docker.com/network/)
- [Macvlan Documentation](https://docs.docker.com/network/macvlan/)
- [Network Troubleshooting](https://docs.docker.com/network/troubleshooting/)

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added