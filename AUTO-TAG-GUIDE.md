# Auto-Tagging System Guide

## Overview

The Kasa Monitor repository now includes an automated version tagging system that creates semantic version tags on every push to the main branch.

## How It Works

### Automatic Version Bumping

The system automatically determines how to increment the version based on commit messages:

| Commit Message Contains | Version Bump | Example |
|------------------------|--------------|---------|
| `BREAKING CHANGE` or `major:` | Major (X.0.0) | v1.0.0 → v2.0.0 |
| `feat:` or `feature:` or `minor:` | Minor (0.X.0) | v1.0.0 → v1.1.0 |
| Any other commit | Patch (0.0.X) | v1.0.0 → v1.0.1 |

### Workflow Process

1. **Push to Main** → Triggers auto-tag workflow
2. **Analyze Commit** → Determines version bump type
3. **Calculate Version** → Increments from latest tag
4. **Create Tag** → Pushes new version tag
5. **Create Release** → GitHub release with changelog
6. **Trigger Docker Build** → Builds Docker image with version tag

## Commit Message Conventions

### Major Version (Breaking Changes)
```bash
git commit -m "BREAKING CHANGE: Redesigned API structure"
git commit -m "major: Complete rewrite of backend"
```

### Minor Version (New Features)
```bash
git commit -m "feat: Add user management system"
git commit -m "feature: Implement real-time monitoring"
git commit -m "minor: Add Docker support"
```

### Patch Version (Bug Fixes & Small Changes)
```bash
git commit -m "fix: Resolve login issue"
git commit -m "docs: Update README"
git commit -m "chore: Update dependencies"
```

## Tag Format

Tags follow semantic versioning: `vMAJOR.MINOR.PATCH`

Examples:
- `v1.0.0` - First stable release
- `v1.1.0` - New feature added
- `v1.1.1` - Bug fix
- `v2.0.0` - Breaking change

## Docker Image Tags

When a version tag is created, Docker images are built with multiple tags:

| Git Tag | Docker Tags |
|---------|-------------|
| `v1.2.3` | `1.2.3`, `1.2`, `1`, `latest` |
| `v2.0.0` | `2.0.0`, `2.0`, `2`, `latest` |

### Pulling Specific Versions
```bash
# Latest version
docker pull xante8088/kasa-monitor:latest

# Specific version
docker pull xante8088/kasa-monitor:1.2.3

# Major version (gets latest minor/patch)
docker pull xante8088/kasa-monitor:1

# Minor version (gets latest patch)
docker pull xante8088/kasa-monitor:1.2
```

## GitHub Releases

Each tag automatically creates a GitHub release with:
- Version number
- Commit details
- Changelog (list of commits since last tag)
- Docker pull commands
- Installation instructions

## Manual Override

### Skip Auto-Tagging
Add `[skip tag]` to commit message:
```bash
git commit -m "docs: Update README [skip tag]"
```

### Manual Tagging
You can still create tags manually:
```bash
git tag -a v1.2.3 -m "Manual release v1.2.3"
git push origin v1.2.3
```

### Force Version Type
Use specific keywords to force version bump:
```bash
# Force major
git commit -m "major: Small fix but incrementing major version"

# Force minor
git commit -m "minor: Documentation update with version bump"

# Force patch (default)
git commit -m "patch: Any regular commit"
```

## Workflow Files

### 1. `auto-tag.yml`
- Triggers on push to main
- Calculates new version
- Creates and pushes tag
- Creates GitHub release

### 2. `docker-build.yml`
- Triggers on new tags (v*.*.*)
- Builds multi-arch Docker images
- Pushes with version tags

## First Release

If no tags exist, the first tag will be `v0.0.1` (or `v0.1.0` / `v1.0.0` based on commit message).

## Version History

View all tags:
```bash
# List all tags
git tag -l

# Show tag details
git show v1.0.0

# View releases on GitHub
https://github.com/xante8088/kasa-monitor/releases
```

## Troubleshooting

### Tag Not Created
Check if:
- Workflow ran successfully in Actions tab
- Commit was to main branch
- No `[skip tag]` in commit message

### Wrong Version Bump
- Check commit message format
- Use proper prefixes (feat:, fix:, major:)
- Review workflow logs in GitHub Actions

### Docker Build Not Triggered
- Ensure tag was created successfully
- Check Docker build workflow is enabled
- Verify Docker Hub credentials are set

## Best Practices

1. **Use Conventional Commits**
   ```
   type(scope): description
   
   feat(auth): Add OAuth support
   fix(api): Resolve timeout issue
   docs(readme): Update installation steps
   ```

2. **Group Related Changes**
   - Make feature complete before pushing
   - Avoid many small commits for one feature

3. **Document Breaking Changes**
   ```bash
   git commit -m "BREAKING CHANGE: Remove deprecated API endpoints
   
   The following endpoints have been removed:
   - /api/old-endpoint
   - /api/legacy-endpoint
   
   Use the new endpoints instead:
   - /api/v2/endpoint"
   ```

4. **Review Before Pushing**
   - Check commit messages
   - Ensure proper version bump
   - Verify all tests pass

## Examples

### Example 1: Bug Fix
```bash
git add .
git commit -m "fix: Resolve device discovery timeout"
git push
# Creates: v1.0.1 (patch bump)
```

### Example 2: New Feature
```bash
git add .
git commit -m "feat: Add export to CSV functionality"
git push
# Creates: v1.1.0 (minor bump)
```

### Example 3: Breaking Change
```bash
git add .
git commit -m "BREAKING CHANGE: Migrate to new database schema"
git push
# Creates: v2.0.0 (major bump)
```

## CI/CD Integration

The auto-tagging system integrates with:
- **Docker Hub**: Images tagged with version
- **GitHub Releases**: Automatic release notes
- **GitHub Actions**: Triggered workflows
- **Deployment**: Can trigger deployments on new tags

## Security

- Tags are signed by GitHub Actions bot
- Protected branch rules apply to tags
- Release notes are auto-generated
- No manual intervention needed

## Monitoring

Track versioning at:
- **GitHub Actions**: Check workflow runs
- **Releases Page**: View all releases
- **Docker Hub**: See all image tags
- **Git Tags**: Local and remote tags

## Summary

The auto-tagging system provides:
- ✅ Automatic semantic versioning
- ✅ Consistent version numbers
- ✅ Docker image versioning
- ✅ Release note generation
- ✅ Changelog creation
- ✅ No manual version management

Just write good commit messages and the system handles the rest!