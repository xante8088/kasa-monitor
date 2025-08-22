# Version Management Quick Reference

## 🚀 Quick Start

### First Time Setup
```bash
# Run the setup script
./scripts/setup-semantic-release.sh

# Or manually install dependencies
npm install --save-dev semantic-release @semantic-release/changelog @semantic-release/git
```

### Creating Releases

Releases are **automatically created** when you push to the `main` branch with semantic commit messages.

```bash
# Feature - Minor version bump (0.3.19 → 0.4.0)
git commit -m "feat: add new feature"

# Bug fix - Patch version bump (0.3.19 → 0.3.20)
git commit -m "fix: resolve issue"

# Breaking change - Major version bump (0.3.19 → 1.0.0)
git commit -m "feat!: breaking change"
```

## 📊 Current Status

- **Current Version**: 0.3.19
- **Commits Since Last Release**: 79
- **Next Version (estimated)**: 0.4.0

### Recent Unreleased Changes
- ✨ 2 features (comprehensive security fixes)
- 🐛 4 bug fixes (Docker, Tailwind CSS, code formatting)
- 🔒 3 security updates (documentation cleanup, vulnerability fixes)

## 🔧 Manual Commands

```bash
# Test what version would be created (dry run)
npx semantic-release --dry-run

# Force a release (if automatic didn't trigger)
npx semantic-release

# Sync version files manually
npm run sync-version

# Check current version status
git describe --tags --abbrev=0
```

## 📝 Commit Message Examples

```bash
# Features (Minor: 0.3.19 → 0.4.0)
feat: add dark mode support
feat(ui): implement dashboard widgets
feat(api): add webhook notifications

# Fixes (Patch: 0.3.19 → 0.3.20)
fix: resolve memory leak
fix(auth): correct token expiration
fix(device): handle connection timeout

# Security (Patch: 0.3.19 → 0.3.20)
security: patch XSS vulnerability
security(auth): fix JWT validation
security: update dependencies

# Breaking (Major: 0.3.19 → 1.0.0)
feat!: new API structure
fix!: change database schema
feat(api): migrate to GraphQL

BREAKING CHANGE: REST API deprecated
```

## 🐳 Docker Tags Created

Each release automatically creates:
- `xante8088/kasa-monitor:latest`
- `xante8088/kasa-monitor:v0.4.0`
- `xante8088/kasa-monitor:0.4`
- `xante8088/kasa-monitor:0`

## ⚙️ Configuration Files

- `.releaserc.json` - Semantic-release configuration
- `.github/workflows/semantic-release.yml` - GitHub Actions workflow
- `scripts/sync-version.js` - Version synchronization
- `scripts/setup-semantic-release.sh` - Initial setup

## 🔍 Troubleshooting

### Version not incrementing?
1. Check commit message format
2. Ensure on `main` branch
3. Review GitHub Actions logs
4. Run `npx semantic-release --dry-run` locally

### Need to fix version manually?
```bash
# Update to specific version
npm version 0.4.0 --no-git-tag-version
npm run sync-version
git add -A
git commit -m "chore: set version to 0.4.0"
git tag v0.4.0
git push origin main --tags
```

## 📚 More Information

- [Full Documentation](docs/development/version-management.md)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)