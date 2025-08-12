# Docker Network Auto-Detection Guide

## Overview

The Docker Network Helper automatically finds available network subnets to prevent conflicts with existing Docker containers. This is especially useful when running multiple Docker Compose projects on the same host.

## Quick Start

### Automatic Setup (Recommended)

```bash
# Make the script executable
chmod +x docker-network-helper.sh

# Generate docker-compose.yml with an available network
./docker-network-helper.sh --generate

# Start your containers
docker-compose up -d
```

That's it! The script automatically:
- Scans for used Docker network subnets
- Finds an available subnet
- Creates a docker-compose.yml with the correct network configuration

## Manual Setup

### Step 1: Check for Available Subnet

```bash
# Find an available subnet
./docker-network-helper.sh

# Example output:
# ✓ Found available subnet: 172.21.0.0/16
```

### Step 2: Use the Subnet

Update your `docker-compose.yml`:

```yaml
networks:
  kasa-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16  # Use the subnet from step 1
          gateway: 172.21.0.1
```

## Script Options

### List All Docker Networks

See what networks are currently in use:

```bash
./docker-network-helper.sh --list

# Output:
# Current Docker networks:
# ----------------------------------------
# NAME                DRIVER    SUBNET
# bridge              bridge    172.17.0.0/16
# host                host      N/A
# my-app_network      bridge    172.20.0.0/16
# ----------------------------------------
```

### Check Specific Subnet Range

Test if a specific subnet range is available:

```bash
# Check subnets starting with 10.20
./docker-network-helper.sh --subnet 10.20

# Check subnets starting with 192.168
./docker-network-helper.sh --subnet 192.168
```

### Generate Docker Compose File

Create a new docker-compose.yml with available network:

```bash
./docker-network-helper.sh --generate

# Creates docker-compose.yml (or docker-compose.auto.yml if file exists)
```

## How It Works

1. **Network Scanning**: The script queries all Docker networks using `docker network inspect`
2. **Subnet Detection**: Extracts subnet information from each network
3. **Availability Check**: Tests common private IP ranges against used subnets
4. **Configuration**: Generates docker-compose.yml with the first available subnet

### Subnet Search Order

The script checks these ranges in order:
- `172.20.0.0/16` through `172.30.0.0/16`
- `10.10.0.0/16` through `10.12.0.0/16`
- `192.168.100.0/24` and `192.168.200.0/24`

## Use Cases

### Multiple Projects on Same Host

When running multiple Docker Compose projects:

```bash
# Project 1
cd ~/project1
./docker-network-helper.sh --generate
docker-compose up -d

# Project 2 (will get different subnet automatically)
cd ~/project2
./docker-network-helper.sh --generate
docker-compose up -d
```

### CI/CD Environments

In automated deployments:

```bash
#!/bin/bash
# deployment.sh

# Auto-detect available network
./docker-network-helper.sh --generate

# Deploy with confidence
docker-compose up -d
```

### Development Teams

Share the same script across team:

```bash
# Each developer gets a non-conflicting network
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor
./docker-network-helper.sh --generate
docker-compose up -d
```

## Troubleshooting

### "No available subnet found"

All common subnets are in use. Solutions:

1. **Remove unused networks**:
   ```bash
   docker network prune
   ```

2. **Specify different range**:
   ```bash
   ./docker-network-helper.sh --subnet 10.50
   ```

3. **Manually set uncommon subnet**:
   ```yaml
   networks:
     kasa-network:
       ipam:
         config:
           - subnet: 10.99.0.0/16
   ```

### "Docker is not running"

Ensure Docker daemon is started:

```bash
# macOS/Windows
# Start Docker Desktop

# Linux
sudo systemctl start docker
```

### Permission Denied

Make script executable:

```bash
chmod +x docker-network-helper.sh
```

### Network Still Conflicts

Check for conflicting networks:

```bash
# List all networks with details
docker network ls
docker network inspect <network-name>

# Remove specific network
docker network rm <network-name>
```

## Advanced Usage

### Custom Network Configuration

Edit `docker-compose.dynamic.yml` for advanced setups:

```yaml
networks:
  kasa-network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: br-kasa
      com.docker.network.bridge.enable_icc: "true"
      com.docker.network.bridge.enable_ip_masquerade: "true"
    ipam:
      driver: default
      config:
        - subnet: SUBNET_PLACEHOLDER
          ip_range: SUBNET_PLACEHOLDER
          gateway: GATEWAY_PLACEHOLDER
      options:
        foo: bar
```

### Integration with Scripts

Use in automation:

```bash
#!/bin/bash
# auto-deploy.sh

# Get available subnet
SUBNET=$(./docker-network-helper.sh | grep "Found available" | awk '{print $NF}')

if [ -z "$SUBNET" ]; then
    echo "No subnet available"
    exit 1
fi

# Use subnet in docker-compose
export DOCKER_SUBNET=$SUBNET
docker-compose up -d
```

### Environment Variable Override

Set network via environment:

```bash
# .env file
DOCKER_SUBNET=172.25.0.0/16
DOCKER_GATEWAY=172.25.0.1

# docker-compose.yml
networks:
  kasa-network:
    ipam:
      config:
        - subnet: ${DOCKER_SUBNET}
          gateway: ${DOCKER_GATEWAY}
```

## Best Practices

1. **Always Check First**: Run the helper before `docker-compose up`
2. **Use in CI/CD**: Include network detection in deployment scripts
3. **Document Subnets**: Keep track of assigned subnets per project
4. **Clean Up**: Remove unused networks periodically with `docker network prune`
5. **Version Control**: Don't commit generated docker-compose.yml with hardcoded subnets

## Network Isolation

For enhanced security, use separate networks per environment:

```yaml
# Production
networks:
  kasa-prod:
    ipam:
      config:
        - subnet: 10.10.0.0/16

# Staging  
networks:
  kasa-stage:
    ipam:
      config:
        - subnet: 10.11.0.0/16

# Development
networks:
  kasa-dev:
    ipam:
      config:
        - subnet: 10.12.0.0/16
```

## FAQ

**Q: Why do I need this?**
A: Docker defaults to specific subnets that can conflict when running multiple projects.

**Q: Is this required?**
A: No, but it prevents "network already exists" errors.

**Q: Can I use with Docker Swarm?**
A: Yes, but you may need to adjust for overlay networks.

**Q: What about IPv6?**
A: Currently supports IPv4 only. IPv6 support can be added if needed.

**Q: Can I exclude certain subnets?**
A: Modify the `subnets` array in the script to skip specific ranges.

## Support

- **Issues**: [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)
- **Script Location**: `docker-network-helper.sh`
- **Manual Network Config**: Edit `docker-compose.yml` directly