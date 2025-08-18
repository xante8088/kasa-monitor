#!/bin/bash

# Pre-push validation script for Kasa Monitor
# Ensures code quality before pushing to remote repository

set -e

echo "🔍 Running code quality checks..."
echo "========================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're in the backend directory or navigate to it
if [ ! -f "server.py" ]; then
    if [ -d "backend" ]; then
        cd backend
        print_status "info" "Navigated to backend directory"
    else
        print_status "error" "Cannot find backend directory or server.py"
        exit 1
    fi
fi

# Initialize error tracking
ERRORS=0

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_status "error" "Python 3 is required but not installed"
    exit 1
fi

# 1. Check imports with isort
print_status "info" "Checking import sorting with isort..."
if python3 -m isort . --check-only --diff; then
    print_status "success" "Import sorting is correct"
else
    print_status "warning" "Import sorting issues found"
    print_status "info" "Auto-fixing import sorting..."
    python3 -m isort .
    print_status "success" "Import sorting fixed"
fi

# 1.5. Check code formatting with black
print_status "info" "Checking code formatting with black..."
if command -v black &> /dev/null; then
    if black --check --diff . 2>/dev/null; then
        print_status "success" "Code formatting is correct"
    else
        print_status "warning" "Code formatting issues found"
        print_status "info" "Auto-fixing code formatting..."
        black . 2>/dev/null
        print_status "success" "Code formatting fixed"
    fi
else
    print_status "warning" "Black formatter not installed, skipping formatting check"
fi

# 2. Run flake8 linting
print_status "info" "Running flake8 linting..."
FLAKE8_OUTPUT=$(python3 -m flake8 . --max-line-length=88 --extend-ignore=E203,W503,F401,F841,E501 --count --statistics 2>&1 || true)

if echo "$FLAKE8_OUTPUT" | grep -q "0$"; then
    print_status "success" "No critical linting errors found"
else
    # Count different types of errors
    CRITICAL_ERRORS=$(echo "$FLAKE8_OUTPUT" | grep -E "E9|F63|F7|F82" | wc -l || echo "0")
    
    if [ "$CRITICAL_ERRORS" -gt 0 ]; then
        print_status "error" "Found $CRITICAL_ERRORS critical linting errors"
        ERRORS=$((ERRORS + CRITICAL_ERRORS))
    else
        print_status "warning" "Found non-critical linting issues (ignored for now)"
    fi
fi

# 3. Check for common security issues
print_status "info" "Checking for common security issues..."
SECURITY_ISSUES=0

# Check for hardcoded passwords or API keys
if grep -r -i "password.*=" . --include="*.py" | grep -v "password_policy\|test_\|PASSWORD_HASH" | head -5; then
    print_status "warning" "Potential hardcoded passwords found"
    SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
fi

# Check for SQL injection vulnerabilities
if grep -r "f\".*{.*}.*\"" . --include="*.py" | grep -i "select\|insert\|update\|delete" | head -3; then
    print_status "warning" "Potential SQL injection vulnerabilities found"
    SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
fi

if [ "$SECURITY_ISSUES" -eq 0 ]; then
    print_status "success" "No obvious security issues found"
fi

# 4. Check for TODO and FIXME comments
print_status "info" "Checking for unresolved TODO/FIXME comments..."
TODO_COUNT=$(grep -r -i "TODO\|FIXME" . --include="*.py" | wc -l || echo "0")
if [ "$TODO_COUNT" -gt 0 ]; then
    print_status "warning" "Found $TODO_COUNT TODO/FIXME comments"
else
    print_status "success" "No unresolved TODO/FIXME comments"
fi

# 5. Check file permissions
print_status "info" "Checking file permissions..."
if find . -name "*.py" -perm -o+w | head -1; then
    print_status "warning" "Found world-writable Python files"
else
    print_status "success" "File permissions are secure"
fi

# Summary
echo ""
echo "========================================"
if [ "$ERRORS" -eq 0 ]; then
    print_status "success" "All critical checks passed! ✨"
    echo ""
    print_status "info" "Code is ready for pushing to remote repository"
    exit 0
else
    print_status "error" "Found $ERRORS critical issues that must be fixed"
    echo ""
    print_status "info" "Please fix the issues above before pushing to remote"
    exit 1
fi