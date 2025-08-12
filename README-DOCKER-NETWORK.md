# Docker Network Auto-Detection for Kasa Monitor

This directory contains tools to automatically configure Docker networks without conflicts.

## Files Included

- **`docker-network-helper.sh`** - Automatic network detection script
- **`docker-compose.dynamic.yml`** - Template for dynamic network configuration  
- **`DOCKER-NETWORK-GUIDE.md`** - Complete documentation

## Quick Start

### Option 1: Automatic (Recommended)

```bash
# Generate docker-compose.yml with available network
./docker-network-helper.sh --generate

# Start containers
docker-compose up -d
```

### Option 2: Check First, Then Configure

```bash
# Check what networks are in use
./docker-network-helper.sh --list

# Find an available subnet
./docker-network-helper.sh

# Generate configuration
./docker-network-helper.sh --generate
```

## Why Use This?

Docker can encounter network conflicts when:
- Running multiple Docker Compose projects
- Default subnets overlap with existing containers
- Teams share the same development environment
- CI/CD pipelines run parallel builds

This tool prevents the error:
```
ERROR: Pool overlaps with other one on this address space
```

## Features

✅ **Automatic Detection** - Finds available subnets automatically
✅ **No Conflicts** - Prevents network overlap errors
✅ **Simple Usage** - One command setup
✅ **Cross-Platform** - Works on Linux, macOS, Windows (with Docker)
✅ **Team Friendly** - Each developer gets unique network
✅ **CI/CD Ready** - Automate deployments without conflicts

## How It Works

1. Scans all Docker networks
2. Identifies used subnets
3. Finds available private IP range
4. Generates docker-compose.yml
5. Configures unique network

## Example Output

```bash
$ ./docker-network-helper.sh --generate

Searching for available Docker network subnet...
✓ Found available subnet: 172.21.0.0/16
Generating docker-compose.yml with subnet 172.21.0.0/16...
✓ Generated docker-compose.yml with network configuration:
  Subnet: 172.21.0.0/16
  Gateway: 172.21.0.1

You can now run: docker-compose up -d
```

## Integration

### Add to Your Project

```bash
# Copy the network helper to your project
cp docker-network-helper.sh /path/to/your/project/
chmod +x /path/to/your/project/docker-network-helper.sh

# Use in your deployment
cd /path/to/your/project
./docker-network-helper.sh --generate
docker-compose up -d
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
steps:
  - name: Setup Docker Network
    run: |
      chmod +x docker-network-helper.sh
      ./docker-network-helper.sh --generate
      
  - name: Deploy
    run: docker-compose up -d
```

### Makefile Integration

```makefile
# Makefile
.PHONY: deploy
deploy:
	@echo "Setting up Docker network..."
	@./docker-network-helper.sh --generate
	@docker-compose up -d
	@echo "Deployment complete!"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No available subnet found" | Run `docker network prune` to clean up |
| "Docker is not running" | Start Docker Desktop or Docker daemon |
| "Permission denied" | Run `chmod +x docker-network-helper.sh` |
| Network still conflicts | Check with `./docker-network-helper.sh --list` |

## Advanced Usage

### Custom Subnet Ranges

```bash
# Check specific subnet range
./docker-network-helper.sh --subnet 10.50

# Use environment variable
export DOCKER_SUBNET_BASE=192.168
./docker-network-helper.sh --generate
```

### Multiple Environments

```bash
# Development
./docker-network-helper.sh --generate
mv docker-compose.yml docker-compose.dev.yml

# Staging
./docker-network-helper.sh --generate  
mv docker-compose.yml docker-compose.staging.yml

# Production
./docker-network-helper.sh --generate
mv docker-compose.yml docker-compose.prod.yml
```

## Benefits

### For Developers
- No manual network configuration
- Avoid conflicts with other projects
- Quick project setup

### For DevOps
- Automated deployments
- Consistent environments
- Reduced configuration errors

### For Teams
- Each member gets unique network
- No "works on my machine" issues
- Simplified onboarding

## Support

For issues or questions:
1. Check `DOCKER-NETWORK-GUIDE.md` for detailed documentation
2. Run `./docker-network-helper.sh --help` for usage information
3. Report issues at [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)

## License

These network helper tools are part of the Kasa Monitor project and follow the same license terms.