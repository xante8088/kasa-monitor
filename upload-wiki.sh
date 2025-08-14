#!/bin/bash

# Upload Wiki Script for Kasa Monitor
# This script uploads all wiki documentation to GitHub

set -e

echo "📚 Kasa Monitor Wiki Upload Script"
echo "=================================="

# Configuration
REPO="xante8088/kasa-monitor"
WIKI_DIR="wiki"
TEMP_DIR="temp-wiki-upload"

# Check if wiki directory exists
if [ ! -d "$WIKI_DIR" ]; then
    echo "❌ Wiki directory not found!"
    echo "Please run this script from the kasa-monitor root directory."
    exit 1
fi

# Count wiki files
FILE_COUNT=$(ls -1 $WIKI_DIR/*.md 2>/dev/null | wc -l)
echo "📄 Found $FILE_COUNT wiki pages to upload"

# Clone the wiki repository
echo -e "\n📥 Cloning wiki repository..."
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

git clone "https://github.com/${REPO}.wiki.git" "$TEMP_DIR" 2>/dev/null || {
    echo "⚠️  Wiki repository doesn't exist yet."
    echo "Please enable Wiki in your GitHub repository settings first:"
    echo "  1. Go to https://github.com/${REPO}/settings"
    echo "  2. Check the 'Wikis' checkbox under Features"
    echo "  3. Create the first page through the web interface"
    echo "  4. Run this script again"
    exit 1
}

cd "$TEMP_DIR"

# Copy all markdown files
echo "📋 Copying wiki files..."
cp ../${WIKI_DIR}/*.md .

# Create sidebar for navigation
echo "📝 Creating sidebar navigation..."
cat > _Sidebar.md << 'EOF'
## 🏠 Navigation

**Getting Started**
* [Home](Home)
* [Quick Start](Quick-Start)
* [Installation](Installation)
* [FAQ](FAQ)

**User Guides**
* [Dashboard Overview](Dashboard-Overview)
* [Device Management](Device-Management)
* [Energy Monitoring](Energy-Monitoring)
* [Cost Analysis](Cost-Analysis)
* [Electricity Rates](Electricity-Rates)

**Configuration**
* [Network Setup](Network-Configuration)
* [User Management](User-Management)
* [System Settings](System-Configuration)

**Technical**
* [API Documentation](API-Documentation)
* [Security Guide](Security-Guide)
* [Database Schema](Database-Schema)
* [Architecture](Architecture)

**Troubleshooting**
* [Common Issues](Common-Issues)
* [Docker Issues](Docker-Issues)
* [Device Discovery](Device-Discovery-Issues)

**Development**
* [Contributing](Contributing)
* [Development Setup](Development-Setup)

**Resources**
* [GitHub Repo](https://github.com/xante8088/kasa-monitor)
* [Docker Hub](https://hub.docker.com/r/xante8088/kasa-monitor)
* [Report Issue](https://github.com/xante8088/kasa-monitor/issues)
EOF

# Create footer
echo "📝 Creating footer..."
cat > _Footer.md << 'EOF'
---
[Home](Home) | [Quick Start](Quick-Start) | [API Docs](API-Documentation) | [FAQ](FAQ) | [GitHub](https://github.com/xante8088/kasa-monitor)

© 2025 Kasa Monitor Contributors - [GPL-3.0 License](https://github.com/xante8088/kasa-monitor/blob/main/LICENSE)
EOF

# Check for changes
if git diff --quiet && git diff --staged --quiet; then
    echo "✅ Wiki is already up to date!"
else
    # Commit and push
    echo -e "\n📤 Uploading to GitHub Wiki..."
    git add .
    git commit -m "Update wiki documentation - $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Push to wiki
    if git push origin master; then
        echo "✅ Wiki uploaded successfully!"
    else
        echo "❌ Failed to push to wiki. You may need to authenticate."
        echo "Try running: git push origin master"
        exit 1
    fi
fi

# Cleanup
cd ..
rm -rf "$TEMP_DIR"

echo -e "\n🎉 Wiki upload complete!"
echo "=================================="
echo "View your wiki at:"
echo "https://github.com/${REPO}/wiki"
echo ""
echo "Next steps:"
echo "1. Review the wiki pages online"
echo "2. Customize the sidebar if needed"
echo "3. Add images through the web interface"
echo "4. Share the wiki link with users"