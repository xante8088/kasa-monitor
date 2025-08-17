#!/bin/bash

# Pre-commit check script for Kasa Monitor
# Run this manually before committing to ensure code quality

echo "🛠️  Pre-commit code quality check..."
echo "====================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2
    case $status in
        "error")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "success")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "info")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Navigate to backend if needed
if [ ! -f "server.py" ] && [ -d "backend" ]; then
    cd backend
fi

# Check for staged changes
if ! git diff --cached --quiet; then
    print_status "info" "Found staged changes - running quality checks..."
else
    print_status "info" "No staged changes found - checking working directory..."
fi

# Run the main validation
if ./scripts/validate-code.sh; then
    print_status "success" "All checks passed!"
    echo ""
    print_status "info" "Your code is ready for commit and push ✨"
else
    print_status "error" "Quality checks failed"
    echo ""
    print_status "info" "Please fix the issues above before committing"
    exit 1
fi

# Additional pre-commit specific checks
echo ""
print_status "info" "Running additional pre-commit checks..."

# Check commit message if committing
if [ -f ".git/COMMIT_EDITMSG" ]; then
    COMMIT_MSG=$(cat .git/COMMIT_EDITMSG)
    if [ ${#COMMIT_MSG} -lt 10 ]; then
        print_status "warning" "Commit message seems short (less than 10 characters)"
    else
        print_status "success" "Commit message length is good"
    fi
fi

# Check for large files
LARGE_FILES=$(find . -type f -size +1M 2>/dev/null | grep -v ".git" | head -5)
if [ -n "$LARGE_FILES" ]; then
    print_status "warning" "Found large files that might not belong in git:"
    echo "$LARGE_FILES"
fi

print_status "success" "Pre-commit checks completed! 🎉"