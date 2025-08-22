# Version Management Guide

This document explains how automatic version management works in Kasa Monitor using semantic-release.

## Overview

Kasa Monitor uses **semantic-release** to automatically manage versions based on conventional commit messages. This ensures consistent versioning and eliminates manual version management errors.

## How It Works

### Commit Message Format
Use [Conventional Commits](https://conventionalcommits.org/) format:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Version Bumping Rules

| Commit Type | Version Bump | Example |
|-------------|--------------|---------|
| `feat:` | Minor (0.3.19 → 0.4.0) | New features |
| `fix:` | Patch (0.3.19 → 0.3.20) | Bug fixes |
| `security:` | Patch (0.3.19 → 0.3.20) | Security fixes |
| `perf:` | Patch (0.3.19 → 0.3.20) | Performance improvements |
| `refactor:` | Patch (0.3.19 → 0.3.20) | Code refactoring |
| `build:` | Patch (0.3.19 → 0.3.20) | Build system changes |
| `BREAKING CHANGE:` | Major (0.3.19 → 1.0.0) | Breaking changes |

### Non-version Bumping Types
These don't trigger releases:
- `docs:` - Documentation changes
- `style:` - Code style changes
- `test:` - Test additions/modifications
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks

## Automatic Process

When you push to `main` branch:

1. **Analysis**: Semantic-release analyzes commits since last release
2. **Version Calculation**: Determines next version based on commit types
3. **File Updates**: Updates `package.json` and `src/lib/version.ts`
4. **Changelog**: Generates `CHANGELOG.md` with release notes
5. **Git Tag**: Creates and pushes git tag (e.g., `v0.4.0`)
6. **GitHub Release**: Creates GitHub release with notes
7. **Docker Images**: Triggers Docker build with new version tag

## Manual Commands

```bash
# Dry run to see what would happen
npm run release:dry

# Manual release (usually done by CI)
npm run release

# Sync version files manually
npm run sync-version
```

## Configuration Files

- **`.releaserc.json`** - Semantic-release configuration
- **`.github/workflows/semantic-release.yml`** - GitHub Actions workflow
- **`scripts/sync-version.js`** - Version synchronization script

## Examples

### Good Commit Messages
```bash
feat: add user notification preferences
fix: resolve Docker health check timeout issues
security: update dependencies to patch CVE-2024-1234
perf: optimize device discovery performance
```

### Release Notes Generation
Commit messages become release notes:

```markdown
## 🚀 Features
- Add user notification preferences

## 🐛 Bug Fixes  
- Resolve Docker health check timeout issues

## 🔒 Security
- Update dependencies to patch CVE-2024-1234

## ⚡ Performance
- Optimize device discovery performance
```

## Troubleshooting

### No Release Created
- Check commit messages follow conventional format
- Ensure changes are on `main` branch
- Look at GitHub Actions logs for errors

### Version Conflicts
- Run `npm run sync-version` to sync files
- Check `package.json` and `src/lib/version.ts` match

### Missing Dependencies
```bash
npm install --save-dev semantic-release @semantic-release/changelog @semantic-release/git @semantic-release/github @semantic-release/npm @semantic-release/exec @semantic-release/commit-analyzer @semantic-release/release-notes-generator conventional-changelog-conventionalcommits
```

## Best Practices

1. **Write Clear Commit Messages**: Describe the "why" not just the "what"
2. **Use Proper Types**: Choose the most specific type for your change
3. **Group Related Changes**: One logical change per commit
4. **Review Before Push**: Check commit messages before pushing to `main`
5. **Test Changes**: Ensure changes work before committing

## Integration with CI/CD

The semantic-release workflow runs automatically on:
- Push to `main` branch
- Manual trigger via GitHub Actions

It integrates with:
- **Docker builds** - New versions trigger image builds
- **Documentation** - Updates version references
- **Releases** - Creates GitHub releases with notes
- **Changelog** - Maintains project history