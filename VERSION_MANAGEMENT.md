# Version Management Guide

This document explains how version numbers are managed in Kasa Monitor to ensure consistency between the application UI, GitHub releases, and package.json.

## Version Locations

Version numbers need to be kept synchronized across these locations:

1. **`package.json`** - Main project version
2. **`src/lib/version.ts`** - Frontend display version
3. **Git tags** - Release tags (e.g., `v0.3.19`)
4. **GitHub Releases** - Published releases

## Current Version Sync Status

- **Package.json**: `0.3.19`
- **Frontend Display**: `v0.3.19`
- **Latest Git Tag**: `v0.3.19`
- **Status**: ✅ All synchronized

## How to Update Versions

### Method 1: Automatic Sync (Recommended)

Use the sync script to update all locations:

```bash
# Update package.json version first
npm version patch  # or minor/major
# or manually edit package.json

# Run sync script to update frontend
npm run sync-version
```

### Method 2: Manual Update

1. Update `package.json` version:
   ```json
   {
     "version": "0.4.0"
   }
   ```

2. Run the sync script:
   ```bash
   npm run sync-version
   ```

3. Create Git tag:
   ```bash
   git tag v0.4.0
   git push origin v0.4.0
   ```

## Version Display in UI

The version appears in two places:

### Admin Panel
- **Location**: Left navigation sidebar (bottom)
- **Format**: "Kasa Monitor v0.3.19"
- **Source**: `getVersionString()` from `src/lib/version.ts`

### Main App
- **Location**: Bottom-right corner
- **Format**: "v0.3.19"
- **Source**: `getShortVersion()` from `src/lib/version.ts`

## Version Sync Script

The `scripts/sync-version.js` script:

- ✅ Reads version from `package.json`
- ✅ Updates `src/lib/version.ts` automatically
- ✅ Checks Git tag alignment
- ✅ Shows warnings for mismatched versions
- ✅ Can be run via `npm run sync-version`

## Release Process

When creating a new release:

1. **Update version**:
   ```bash
   npm version patch  # 0.3.19 → 0.3.20
   npm run sync-version
   ```

2. **Commit changes**:
   ```bash
   git add .
   git commit -m "Bump version to v0.3.20"
   ```

3. **Create tag and push**:
   ```bash
   git tag v0.3.20
   git push origin main
   git push origin v0.3.20
   ```

4. **Create GitHub Release** (optional):
   - Go to GitHub → Releases → Create new release
   - Select tag `v0.3.20`
   - Add release notes

## Verification

To verify version sync:

```bash
# Check all versions
npm run sync-version

# Should show:
# 📦 Package.json version: 0.3.20
# ✅ Updated src/lib/version.ts to version 0.3.20
# 🏷️ Latest Git tag: v0.3.20 (0.3.20)
# ✅ Version is in sync with Git tag
```

## Future Enhancements

Potential improvements for version management:

1. **Automatic Update Checking**: Check GitHub API for newer releases
2. **Build-time Version Injection**: Read package.json at build time
3. **CI/CD Integration**: Automatic version bumping in release pipeline
4. **Update Notifications**: Show users when updates are available

## Troubleshooting

### Version Mismatch Warning

If you see:
```
⚠️ WARNING: Version mismatch detected!
   Package version: 0.4.0
   Latest Git tag: 0.3.19
```

**Solution**: Create a new Git tag:
```bash
git tag v0.4.0
git push origin v0.4.0
```

### Frontend Shows Wrong Version

**Solution**: Run the sync script:
```bash
npm run sync-version
```

### Cannot Access GitHub API

The version checking functions are designed to gracefully handle network failures and will default to showing the current version as latest if GitHub API is unavailable.