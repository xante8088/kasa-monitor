#!/bin/bash

# Kasa Monitor Repository Security Script
# This script helps secure the repository before pushing to GitHub

echo "========================================="
echo "Kasa Monitor Repository Security Script"
echo "========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    if [ "$1" = "error" ]; then
        echo -e "${RED}[ERROR]${NC} $2"
    elif [ "$1" = "warning" ]; then
        echo -e "${YELLOW}[WARNING]${NC} $2"
    elif [ "$1" = "success" ]; then
        echo -e "${GREEN}[SUCCESS]${NC} $2"
    else
        echo "$2"
    fi
}

# Check if .sensitive directory exists
if [ ! -d ".sensitive" ]; then
    print_status "warning" ".sensitive directory not found. Creating it..."
    mkdir -p .sensitive
fi

# Check for sensitive files that shouldn't be committed
print_status "info" "Checking for sensitive files..."

SENSITIVE_FILES=(
    ".env"
    ".env.production"
    ".env.local"
    "backend/data/jwt_secrets.json"
    "backend/.auth_token"
)

for file in "${SENSITIVE_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_status "warning" "Found sensitive file: $file"
        echo "  Moving to .sensitive/..."
        mv "$file" ".sensitive/$(basename $file)" 2>/dev/null
    fi
done

# Check git status for tracked sensitive files
print_status "info" "Checking for tracked sensitive files in git..."
TRACKED_SENSITIVE=$(git ls-files 2>/dev/null | grep -E "\.(db|log|env|key|pem|crt|csr)$|jwt_secret|password|credential|token" || true)

if [ ! -z "$TRACKED_SENSITIVE" ]; then
    print_status "warning" "Found potentially sensitive files in git tracking:"
    echo "$TRACKED_SENSITIVE"
    echo ""
    read -p "Do you want to remove these from git tracking? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        while IFS= read -r file; do
            git rm --cached "$file" 2>/dev/null || true
        done <<< "$TRACKED_SENSITIVE"
        print_status "success" "Files removed from git tracking"
    fi
fi

# Check for default/weak secrets in files
print_status "info" "Scanning for default/weak secrets..."

# Check for default JWT secret
if grep -q "your-secure-256-bit-secret-key-here-replace-this-immediately" .sensitive/.env.production 2>/dev/null; then
    print_status "error" "Default JWT secret found in .env.production!"
    echo "  Generate a new one with: openssl rand -hex 32"
fi

if grep -q "change-this-to-a-secure-random-key-in-production" .sensitive/.env.production 2>/dev/null; then
    print_status "error" "Example JWT secret found in .env.production!"
    echo "  Generate a new one with: openssl rand -hex 32"
fi

# Check .gitignore
print_status "info" "Verifying .gitignore coverage..."

REQUIRED_GITIGNORE=(
    ".sensitive/"
    "*.db"
    "*.log"
    ".env*"
    "*.key"
    "*.pem"
    "*.crt"
)

for pattern in "${REQUIRED_GITIGNORE[@]}"; do
    if ! grep -q "$pattern" .gitignore 2>/dev/null; then
        print_status "warning" ".gitignore missing pattern: $pattern"
    fi
done

# Generate secure values
print_status "info" "Generating secure values for reference..."
echo ""
echo "Secure JWT Secret:"
echo "  $(openssl rand -hex 32)"
echo ""
echo "Secure Password:"
echo "  $(openssl rand -base64 24)"
echo ""

# Final checklist
echo "========================================="
echo "SECURITY CHECKLIST:"
echo "========================================="
echo ""
echo "Before pushing to GitHub, ensure:"
echo ""
echo "[ ] All sensitive files are in .sensitive/ directory"
echo "[ ] .sensitive/ is in .gitignore"
echo "[ ] No default/example secrets in configuration"
echo "[ ] All keys and certificates are secured"
echo "[ ] Database files are not tracked"
echo "[ ] Log files are cleared/not tracked"
echo "[ ] Git history is clean (no previously committed secrets)"
echo ""
echo "To check git history for secrets:"
echo "  git log -p | grep -E 'password|secret|token|key' | head -20"
echo ""
echo "To clean git history (if needed):"
echo "  Use BFG Repo-Cleaner: https://rtyley.github.io/bfg-repo-cleaner/"
echo ""
echo "========================================="

# Check if repository is ready
ISSUES_FOUND=0

if [ -f ".env" ]; then
    print_status "error" ".env file still in repository root!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

if [ -f "backend/data/jwt_secrets.json" ]; then
    print_status "error" "jwt_secrets.json still in backend/data!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

if [ -d "ssl" ] && [ "$(ls -A ssl 2>/dev/null)" ]; then
    print_status "warning" "SSL directory still contains files!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

if [ -d "keys" ] && [ "$(ls -A keys 2>/dev/null)" ]; then
    print_status "warning" "Keys directory still contains files!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

echo ""
if [ $ISSUES_FOUND -eq 0 ]; then
    print_status "success" "No critical security issues found!"
    echo "Repository appears ready for GitHub (after verifying checklist above)"
else
    print_status "error" "Found $ISSUES_FOUND security issue(s) that need attention!"
    echo "Please resolve these issues before pushing to GitHub"
fi

echo ""
echo "For detailed security report, see: SECURITY_SCAN_REPORT.md"
echo ""