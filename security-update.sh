#!/bin/bash
# Security Update Script for Kasa Monitor
# Run this to update dependencies and scan for vulnerabilities

set -e

echo "🔒 Kasa Monitor Security Update Script"
echo "======================================"

# Check for required tools
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        return 1
    fi
    echo "✅ $1 found"
    return 0
}

echo -e "\n📋 Checking required tools..."
check_tool npm
check_tool python3
check_tool pip3

# Update Node dependencies
echo -e "\n📦 Updating Node.js dependencies..."
npm audit fix --force 2>/dev/null || true
npm update

echo -e "\n🔍 Node.js vulnerability report:"
npm audit --production

# Update Python dependencies  
echo -e "\n🐍 Updating Python dependencies..."
pip3 install --upgrade pip

# Create updated requirements
cat > requirements-updated.txt << EOF
fastapi==0.115.5
uvicorn==0.32.1
python-kasa>=0.7.0
aiosqlite>=0.19.0
influxdb-client>=1.38.0
apscheduler>=3.10.0
python-socketio>=5.10.0
bcrypt==4.3.0
pyjwt==2.10.1
python-multipart>=0.0.6
cryptography==45.0.0
pydantic>=2.5.0
EOF

echo "📝 Updated requirements.txt created"

# Check for Python vulnerabilities
if command -v pip-audit &> /dev/null; then
    echo -e "\n🔍 Python vulnerability scan:"
    pip-audit -r requirements-updated.txt
else
    echo "ℹ️  Install pip-audit for Python vulnerability scanning:"
    echo "   pip3 install pip-audit"
fi

# Docker scan if available
if command -v docker &> /dev/null; then
    echo -e "\n🐋 Docker security scan:"
    
    # Build with secure Dockerfile if it exists
    if [ -f "Dockerfile.secure" ]; then
        echo "Building with secure Dockerfile..."
        docker build -f Dockerfile.secure -t kasa-monitor:secure .
        
        # Run scout if available
        if docker scout version &> /dev/null 2>&1; then
            docker scout cves kasa-monitor:secure
        else
            echo "ℹ️  Install Docker Scout for vulnerability scanning"
        fi
    fi
fi

# Summary
echo -e "\n✨ Security Update Complete!"
echo "======================================"
echo "Next steps:"
echo "1. Review requirements-updated.txt and update requirements.txt if safe"
echo "2. Test application with updated dependencies"
echo "3. Rebuild Docker image with Dockerfile.secure"
echo "4. Run: docker scout cves kasa-monitor:secure"
echo ""
echo "For detailed security info, see SECURITY.md"