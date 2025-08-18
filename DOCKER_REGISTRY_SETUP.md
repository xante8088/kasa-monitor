# Docker Registry Setup for CI/CD

This document explains the Docker registry configuration for automated image builds and publishing.

## Current Configuration

- **Registry**: Docker Hub (`docker.io`)
- **Repository**: `xante8088/kasa-monitor`
- **CI/CD**: Pushes to Docker Hub on main/develop branch commits

## Required GitHub Secrets

For the CI/CD pipeline to push Docker images, these secrets must be configured in the GitHub repository settings:

### 1. DOCKER_USERNAME
- **Value**: Docker Hub username (e.g., `xante8088`)
- **Purpose**: Authenticate with Docker Hub

### 2. DOCKER_PASSWORD
- **Value**: Docker Hub access token (NOT your password)
- **Purpose**: Secure authentication with Docker Hub

## Setting Up Docker Hub Access Token

1. **Login to Docker Hub**: https://hub.docker.com/
2. **Go to Account Settings** → **Security** → **Access Tokens**
3. **Create New Access Token**:
   - Name: `kasa-monitor-ci`
   - Permissions: `Read, Write, Delete`
4. **Copy the token** (you won't be able to see it again)

## Adding Secrets to GitHub

1. Go to repository: https://github.com/xante8088/kasa-monitor
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add both secrets:
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: The access token from Docker Hub

## Build Triggers

Docker images are built and pushed when:

- ✅ Commits are pushed to `main` branch
- ✅ Commits are pushed to `develop` branch  
- ✅ All prerequisite jobs pass (lint, security, tests)

## Image Tags

The CI/CD pipeline creates these tags:

```bash
# Branch-based tags
xante8088/kasa-monitor:main
xante8088/kasa-monitor:develop

# Version tags (for releases)
xante8088/kasa-monitor:v0.3.19
xante8088/kasa-monitor:0.3.19
xante8088/kasa-monitor:0.3
xante8088/kasa-monitor:0

# Special tags
xante8088/kasa-monitor:latest    # Latest stable release
xante8088/kasa-monitor:pi5       # Raspberry Pi optimized

# Tracking tags
xante8088/kasa-monitor:abc1234   # Git commit SHA
xante8088/kasa-monitor:2025-08-18-1430  # Build timestamp
```

## Verification

After setting up credentials, check that builds are working:

1. **Make a commit** to the main branch
2. **Check Actions tab** for build status
3. **Verify images** on Docker Hub: https://hub.docker.com/r/xante8088/kasa-monitor/tags

## Troubleshooting

### Build Job Not Running
- Check if prerequisite jobs (lint, security, test-backend, test-frontend) are passing
- Verify commit is on `main` or `develop` branch
- Check if build condition is met: `github.event_name == 'push'`

### Authentication Errors
- Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are set correctly
- Ensure Docker Hub access token has write permissions
- Check if Docker Hub account has access to the repository

### Missing Tags
- Docker images are only pushed after successful builds
- Check workflow logs for push confirmation
- Verify all tests are passing before build job runs

## Registry Migration Notes

**Previous**: GitHub Container Registry (`ghcr.io/xante8088/kasa-monitor`)  
**Current**: Docker Hub (`xante8088/kasa-monitor`)

This change was made to:
- Match existing documentation and references
- Simplify access (Docker Hub is more commonly used)
- Align with current image distribution strategy

## Future Considerations

- **Multi-registry**: Could push to both Docker Hub and GitHub Container Registry
- **Harbor/Private**: For enterprise deployments
- **Image scanning**: Integrate security scanning before publication