#!/bin/bash

# Setup script for semantic-release
# This script helps initialize semantic-release and catch up with missing versions

set -e

echo "🚀 Setting up semantic-release for Kasa Monitor"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the project root."
    exit 1
fi

# Install semantic-release dependencies
echo "📦 Installing semantic-release dependencies..."
npm install --save-dev \
    semantic-release \
    @semantic-release/changelog \
    @semantic-release/git \
    @semantic-release/github \
    @semantic-release/npm \
    @semantic-release/exec \
    @semantic-release/commit-analyzer \
    @semantic-release/release-notes-generator \
    conventional-changelog-conventionalcommits

echo "✅ Dependencies installed"

# Add to .gitignore if not already there
echo "📝 Updating .gitignore..."
if ! grep -q ".semantic-release-version" .gitignore 2>/dev/null; then
    echo -e "\n# Semantic Release\n.semantic-release-version" >> .gitignore
    echo "✅ Added .semantic-release-version to .gitignore"
fi

# Check current version status
echo ""
echo "📊 Current Version Status:"
echo "=========================="
PACKAGE_VERSION=$(node -p "require('./package.json').version")
echo "📦 Package.json version: $PACKAGE_VERSION"

LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
echo "🏷️  Latest Git tag: $LATEST_TAG"

if [ "$LATEST_TAG" != "none" ]; then
    TAG_VERSION=${LATEST_TAG#v}
    COMMITS_SINCE=$(git rev-list ${LATEST_TAG}..HEAD --count)
    echo "📈 Commits since last tag: $COMMITS_SINCE"
    
    if [ "$COMMITS_SINCE" -gt 0 ]; then
        echo ""
        echo "📋 Recent semantic commits that will trigger version bumps:"
        git log ${LATEST_TAG}..HEAD --oneline | grep -E "^[a-f0-9]+ (feat|fix|perf|security|BREAKING)" | head -10 || true
    fi
fi

echo ""
echo "🔧 Setup Options:"
echo "================="
echo "1. Run semantic-release in dry-run mode (recommended first)"
echo "2. Create a catch-up release for all unreleased commits"
echo "3. Skip and configure manually"
echo ""
read -p "Select option (1-3): " option

case $option in
    1)
        echo ""
        echo "🧪 Running semantic-release in dry-run mode..."
        echo "This will show what version would be created without actually releasing."
        echo ""
        npx semantic-release --dry-run
        echo ""
        echo "✅ Dry run complete. Review the output above."
        echo "To perform an actual release, run: npx semantic-release"
        ;;
    2)
        echo ""
        echo "📦 Creating catch-up release..."
        echo "This will analyze all commits since the last tag and create an appropriate version."
        read -p "Are you sure you want to create a release? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            npx semantic-release
            echo "✅ Release created!"
        else
            echo "❌ Release cancelled"
        fi
        ;;
    3)
        echo "ℹ️  Skipping automatic setup. You can run semantic-release manually with:"
        echo "    npx semantic-release --dry-run  # For testing"
        echo "    npx semantic-release             # For actual release"
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "📚 Next Steps:"
echo "=============="
echo "1. The semantic-release workflow will run automatically on pushes to main branch"
echo "2. Use conventional commit messages for automatic versioning:"
echo "   - feat: New feature (minor version bump)"
echo "   - fix: Bug fix (patch version bump)"
echo "   - feat!: or BREAKING CHANGE: Breaking change (major version bump)"
echo "3. Version will be automatically updated in:"
echo "   - package.json"
echo "   - src/lib/version.ts"
echo "   - Git tags"
echo "   - GitHub releases"
echo "   - Docker image tags"
echo ""
echo "🎉 Setup complete!"