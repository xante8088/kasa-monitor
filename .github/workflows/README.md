# GitHub Actions Workflows

## Overview

This repository uses GitHub Actions to automate Docker image builds and deployments. There are two workflows configured for different scenarios.

## Workflows

### 1. `docker-build.yml` - Automatic Builds on Code Changes

**Triggers:**
- ✅ Source code changes in main branch
- ✅ New releases
- ✅ Manual trigger via GitHub UI

**When it runs automatically:**
- Changes to backend Python files (`backend/**/*.py`)
- Changes to frontend TypeScript/JavaScript files (`src/**/*.ts`, `src/**/*.tsx`, etc.)
- Changes to build configuration (`package.json`, `requirements.txt`, etc.)
- Changes to Docker configuration (`Dockerfile`, `docker-entrypoint.sh`)

**When it does NOT run:**
- Documentation changes (`.md` files)
- Docker Compose file changes (unless Dockerfile is also changed)
- GitHub workflow changes (except the workflow itself)
- Configuration file changes that don't affect the build

### 2. `docker-build-manual.yml` - Manual Builds Only

**Triggers:**
- ✅ Manual trigger via GitHub UI only

**Use cases:**
- Force a rebuild without code changes
- Build with custom tags
- Build for specific platforms
- Testing and debugging

## How to Trigger Manual Builds

### Via GitHub UI:

1. Go to the **Actions** tab in the repository
2. Select either workflow:
   - **"Build and Push Docker Image"** for standard builds
   - **"Docker Build (Manual)"** for manual-only builds
3. Click **"Run workflow"**
4. Fill in the optional parameters:
   - **Tag**: Docker image tag (default: `latest`)
   - **Platforms**: Target platforms (default: `linux/amd64,linux/arm64`)
   - **Reason**: Description of why manual build is needed
5. Click **"Run workflow"** button

### Via GitHub CLI:

```bash
# Trigger manual build with default settings
gh workflow run docker-build.yml

# Trigger with custom tag
gh workflow run docker-build.yml -f tag=v1.2.3

# Trigger manual-only workflow with reason
gh workflow run docker-build-manual.yml \
  -f tag=testing \
  -f reason="Testing new feature" \
  -f platforms=linux/arm64
```

## Workflow Configuration

### Paths that Trigger Automatic Builds

```yaml
paths:
  # Docker configuration
  - 'Dockerfile'
  - 'docker-entrypoint.sh'
  - '.dockerignore'
  
  # Backend source code
  - 'backend/**/*.py'
  - 'requirements.txt'
  
  # Frontend source code
  - 'src/**/*.ts'
  - 'src/**/*.tsx'
  - 'src/**/*.js'
  - 'src/**/*.jsx'
  - 'src/**/*.css'
  - 'public/**'
  
  # Build configuration
  - 'package.json'
  - 'package-lock.json'
  - 'next.config.js'
  - 'tsconfig.json'
  - 'tailwind.config.js'
  - 'postcss.config.js'
```

### Paths that DO NOT Trigger Builds

- `*.md` - Documentation files
- `docker-compose*.yml` - Docker Compose files
- `.env*` - Environment files
- `tests/**` - Test files (if any)
- `.github/**` - GitHub configuration (except workflows)
- `docs/**` - Documentation directory
- `scripts/**` - Utility scripts

## Docker Image Tags

### Automatic Tags (on code changes):
- `latest` - Always points to the most recent build from main branch
- `pi5` - Optimized for Raspberry Pi 5 (same as latest)
- `main-<sha>` - Git commit SHA for tracking
- `v*.*.*` - Semantic version on releases

### Manual Build Tags:
- Custom tag specified in workflow input
- `manual-<sha>` - Prefixed with "manual" for tracking
- `YYYYMMDD-HHmmss` - Timestamp of manual build

## Build Platforms

Both workflows support multi-architecture builds:
- `linux/amd64` - Standard x86_64 architecture
- `linux/arm64` - ARM64 for Raspberry Pi and Apple Silicon

## Environment Variables

Required GitHub Secrets:
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub access token (not password)

## Monitoring Builds

### Check Build Status:

1. Go to **Actions** tab
2. Click on a workflow run to see details
3. View logs for each step

### Build Summary:

Each successful build generates a summary with:
- Build trigger type (automatic/manual)
- Reason for build (if manual)
- Docker tags created
- Pull commands
- Build actor (who triggered it)

## Best Practices

1. **Avoid Unnecessary Builds**: Only trigger manual builds when needed
2. **Use Descriptive Tags**: For manual builds, use meaningful tags
3. **Document Manual Builds**: Always provide a reason for manual builds
4. **Monitor Failed Builds**: Check Actions tab for failed builds
5. **Cache Management**: Workflows use GitHub Actions cache for faster builds

## Troubleshooting

### Build Not Triggering Automatically

Check if your changes match the path filters:
```bash
# See what files changed
git diff --name-only HEAD~1

# Check if they match workflow paths
cat .github/workflows/docker-build.yml | grep -A 20 "paths:"
```

### Manual Build Failing

1. Check Docker Hub credentials are set correctly
2. Verify Dockerfile builds locally:
   ```bash
   docker build -t test .
   ```
3. Check workflow logs in Actions tab

### Multi-arch Build Issues

For local testing of multi-arch builds:
```bash
# Setup buildx
docker buildx create --use

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t test .
```

## Examples

### Example 1: Deploy After Feature Development

```bash
# After developing a new feature
git add src/
git commit -m "Add new device monitoring feature"
git push origin main
# Workflow automatically triggers and builds new image
```

### Example 2: Emergency Hotfix

```bash
# Quick manual build for hotfix
# 1. Go to Actions tab
# 2. Run "Docker Build (Manual)"
# 3. Set tag: "hotfix-critical"
# 4. Set reason: "Critical bug fix for production"
# 5. Run workflow
```

### Example 3: Testing ARM64 Build

```bash
# Manual build for ARM64 only
gh workflow run docker-build-manual.yml \
  -f tag=arm-test \
  -f platforms=linux/arm64 \
  -f reason="Testing ARM64 compatibility"
```

## Workflow Logs

All workflow runs are retained for 90 days. You can:
- Download logs from the Actions tab
- Re-run failed workflows
- View detailed execution times
- See resource usage

## Security Notes

- Never commit Docker Hub credentials
- Use access tokens, not passwords
- Regularly rotate access tokens
- Monitor for unauthorized workflow runs
- Review workflow changes in PRs