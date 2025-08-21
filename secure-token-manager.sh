#!/bin/bash

# Secure GitHub Token Manager
# Provides secure storage and retrieval of GitHub tokens

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
KEYCHAIN_SERVICE="github-api-token"
TOKEN_AGE_FILE="$HOME/.github_token_age"
MAX_TOKEN_AGE_DAYS=90

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

# Function to validate token format
validate_token() {
    local token="$1"
    
    if [[ "$token" =~ ^ghp_[a-zA-Z0-9]{36}$ ]]; then
        print_color "$GREEN" "✓ Valid classic token format"
        return 0
    elif [[ "$token" =~ ^github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}$ ]]; then
        print_color "$GREEN" "✓ Valid fine-grained token format"
        return 0
    else
        print_color "$RED" "✗ Invalid token format"
        return 1
    fi
}

# Function to store token securely
store_token() {
    print_color "$YELLOW" "=== Store GitHub Token Securely ==="
    
    # Prompt for token
    echo -n "Enter your GitHub token: "
    read -rs token
    echo
    
    # Validate token
    if ! validate_token "$token"; then
        print_color "$RED" "Error: Invalid token format"
        exit 1
    fi
    
    # Store in macOS Keychain
    if command -v security &> /dev/null; then
        security add-generic-password \
            -a "$USER" \
            -s "$KEYCHAIN_SERVICE" \
            -w "$token" \
            -U \
            2>/dev/null || {
                print_color "$RED" "Failed to store token in keychain"
                exit 1
            }
        print_color "$GREEN" "✓ Token stored securely in macOS Keychain"
        
        # Record token creation time
        date +%s > "$TOKEN_AGE_FILE"
        
        # Test token
        test_token "$token"
    else
        print_color "$RED" "macOS Keychain not available"
        print_color "$YELLOW" "Alternative: Store as environment variable"
        echo "export GITHUB_TOKEN='$token'" > "$HOME/.github_token"
        chmod 600 "$HOME/.github_token"
        print_color "$GREEN" "✓ Token saved to ~/.github_token (encrypted file)"
    fi
}

# Function to retrieve token
retrieve_token() {
    local silent="${1:-false}"
    
    # Try macOS Keychain first
    if command -v security &> /dev/null; then
        token=$(security find-generic-password \
            -a "$USER" \
            -s "$KEYCHAIN_SERVICE" \
            -w 2>/dev/null) || {
                if [ "$silent" != "true" ]; then
                    print_color "$RED" "No token found in keychain"
                fi
                return 1
            }
        echo "$token"
        return 0
    fi
    
    # Try environment variable
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        echo "$GITHUB_TOKEN"
        return 0
    fi
    
    # Try file
    if [ -f "$HOME/.github_token" ]; then
        source "$HOME/.github_token"
        echo "$GITHUB_TOKEN"
        return 0
    fi
    
    if [ "$silent" != "true" ]; then
        print_color "$RED" "No token found"
    fi
    return 1
}

# Function to test token
test_token() {
    local token="${1:-$(retrieve_token true)}"
    
    if [ -z "$token" ]; then
        print_color "$RED" "No token to test"
        return 1
    fi
    
    print_color "$YELLOW" "Testing token..."
    
    # Test API access
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/user")
    
    if [ "$response" = "200" ]; then
        # Get user info
        user_info=$(curl -s \
            -H "Authorization: Bearer $token" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/user")
        
        username=$(echo "$user_info" | grep -o '"login":"[^"]*' | cut -d'"' -f4)
        
        print_color "$GREEN" "✓ Token is valid"
        print_color "$GREEN" "  Authenticated as: $username"
        
        # Check scopes
        scopes=$(curl -sI \
            -H "Authorization: Bearer $token" \
            "https://api.github.com/user" | \
            grep -i "x-oauth-scopes:" | \
            cut -d: -f2- | tr -d '\r')
        
        if [ -n "$scopes" ]; then
            print_color "$GREEN" "  Scopes:$scopes"
        fi
        
        # Check rate limit
        rate_limit=$(curl -s \
            -H "Authorization: Bearer $token" \
            "https://api.github.com/rate_limit")
        
        remaining=$(echo "$rate_limit" | grep -o '"remaining":[0-9]*' | head -1 | cut -d: -f2)
        limit=$(echo "$rate_limit" | grep -o '"limit":[0-9]*' | head -1 | cut -d: -f2)
        
        print_color "$GREEN" "  API Rate Limit: $remaining/$limit"
        
        return 0
    elif [ "$response" = "401" ]; then
        print_color "$RED" "✗ Token is invalid or expired"
        return 1
    else
        print_color "$RED" "✗ API test failed (HTTP $response)"
        return 1
    fi
}

# Function to check token age
check_token_age() {
    if [ -f "$TOKEN_AGE_FILE" ]; then
        created=$(cat "$TOKEN_AGE_FILE")
        now=$(date +%s)
        age_days=$(( (now - created) / 86400 ))
        
        if [ $age_days -gt $MAX_TOKEN_AGE_DAYS ]; then
            print_color "$RED" "⚠ WARNING: Token is $age_days days old (max recommended: $MAX_TOKEN_AGE_DAYS)"
            print_color "$YELLOW" "Consider rotating your token for security"
        else
            print_color "$GREEN" "✓ Token age: $age_days days"
        fi
    else
        print_color "$YELLOW" "Token age unknown (consider rotating regularly)"
    fi
}

# Function to delete token
delete_token() {
    print_color "$YELLOW" "=== Delete Stored Token ==="
    
    echo -n "Are you sure you want to delete the stored token? (y/N): "
    read -r confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_color "$YELLOW" "Cancelled"
        return
    fi
    
    # Delete from keychain
    if command -v security &> /dev/null; then
        security delete-generic-password \
            -a "$USER" \
            -s "$KEYCHAIN_SERVICE" \
            2>/dev/null && \
            print_color "$GREEN" "✓ Token deleted from keychain"
    fi
    
    # Delete token file
    [ -f "$HOME/.github_token" ] && rm "$HOME/.github_token"
    [ -f "$TOKEN_AGE_FILE" ] && rm "$TOKEN_AGE_FILE"
    
    print_color "$GREEN" "✓ Token deleted successfully"
}

# Function to rotate token
rotate_token() {
    print_color "$YELLOW" "=== Rotate GitHub Token ==="
    
    # Check if old token exists
    old_token=$(retrieve_token true)
    if [ -n "$old_token" ]; then
        print_color "$YELLOW" "Current token found. Testing..."
        if test_token "$old_token"; then
            print_color "$GREEN" "Current token is still valid"
        fi
    fi
    
    print_color "$YELLOW" "\nTo rotate your token:"
    print_color "$YELLOW" "1. Go to GitHub Settings → Developer settings → Personal access tokens"
    print_color "$YELLOW" "2. Create a new token with required permissions"
    print_color "$YELLOW" "3. Copy the new token"
    echo
    
    # Store new token
    store_token
    
    if [ -n "$old_token" ]; then
        print_color "$YELLOW" "\nDon't forget to revoke the old token on GitHub!"
    fi
}

# Function to export token
export_token() {
    token=$(retrieve_token)
    if [ -n "$token" ]; then
        echo "export GITHUB_TOKEN='$token'"
        print_color "$GREEN" "✓ Token exported to GITHUB_TOKEN environment variable"
        print_color "$YELLOW" "Run: eval \$(./secure-token-manager.sh export)"
    fi
}

# Function to show permissions guide
show_permissions() {
    print_color "$YELLOW" "=== Required GitHub Token Permissions ==="
    echo
    print_color "$GREEN" "For Code Scanning API (Fine-grained token):"
    echo "  • Repository permissions:"
    echo "    - Actions: Read"
    echo "    - Code scanning alerts: Read/Write"
    echo "    - Contents: Read"
    echo "    - Metadata: Read (always required)"
    echo "    - Pull requests: Read"
    echo "    - Security events: Read"
    echo
    print_color "$GREEN" "For Code Scanning API (Classic token):"
    echo "  • repo (full control) OR"
    echo "  • public_repo (for public repositories)"
    echo "  • security_events"
    echo
    print_color "$YELLOW" "Best Practice: Use fine-grained tokens with minimal permissions"
}

# Function to setup automation
setup_automation() {
    print_color "$YELLOW" "=== Setup Automated Security Scanning ==="
    
    # Create launch agent for macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        PLIST_FILE="$HOME/Library/LaunchAgents/com.github.security.scanner.plist"
        
        cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.github.security.scanner</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$PWD/github_security_scanner.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/github-security-scanner.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/github-security-scanner-error.log</string>
</dict>
</plist>
EOF
        
        launchctl load "$PLIST_FILE" 2>/dev/null || true
        print_color "$GREEN" "✓ Daily security scan scheduled (9:00 AM)"
    else
        # Create cron job for Linux
        (crontab -l 2>/dev/null; echo "0 9 * * * /usr/bin/python3 $PWD/github_security_scanner.py") | crontab -
        print_color "$GREEN" "✓ Daily security scan scheduled via cron (9:00 AM)"
    fi
}

# Main menu
show_menu() {
    print_color "$YELLOW" "==================================="
    print_color "$YELLOW" "   GitHub Token Security Manager   "
    print_color "$YELLOW" "==================================="
    echo
    echo "1. Store token securely"
    echo "2. Test token"
    echo "3. Check token age"
    echo "4. Rotate token"
    echo "5. Export token to environment"
    echo "6. Delete stored token"
    echo "7. Show required permissions"
    echo "8. Setup automation"
    echo "9. Exit"
    echo
    echo -n "Select option: "
}

# Main execution
main() {
    case "${1:-}" in
        store)
            store_token
            ;;
        test)
            test_token
            check_token_age
            ;;
        retrieve)
            token=$(retrieve_token)
            [ -n "$token" ] && echo "$token"
            ;;
        export)
            export_token
            ;;
        delete)
            delete_token
            ;;
        rotate)
            rotate_token
            ;;
        permissions)
            show_permissions
            ;;
        setup)
            setup_automation
            ;;
        *)
            while true; do
                show_menu
                read -r choice
                
                case $choice in
                    1) store_token ;;
                    2) test_token; check_token_age ;;
                    3) check_token_age ;;
                    4) rotate_token ;;
                    5) export_token ;;
                    6) delete_token ;;
                    7) show_permissions ;;
                    8) setup_automation ;;
                    9) exit 0 ;;
                    *) print_color "$RED" "Invalid option" ;;
                esac
                
                echo
                echo -n "Press Enter to continue..."
                read -r
                clear
            done
            ;;
    esac
}

# Run main function
main "$@"