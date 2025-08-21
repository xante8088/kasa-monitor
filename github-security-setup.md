# GitHub Code Scanning API Security Setup Guide

## 1. GitHub Personal Access Token (PAT) Configuration

### Creating a Secure PAT

1. Navigate to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic) or Fine-grained tokens
2. Choose **Fine-grained personal access tokens** for better security (recommended)
3. Set an expiration date (90 days or less recommended)
4. Select repository access: `xante8088/kasa-monitor`

### Required Permissions/Scopes

For code scanning API access, you need:

#### Fine-grained Token Permissions:
- **Repository permissions:**
  - `Actions`: Read (for workflow runs)
  - `Code scanning alerts`: Read/Write
  - `Contents`: Read (to view code)
  - `Metadata`: Read (always required)
  - `Pull requests`: Read (if reviewing PR scanning)
  - `Security events`: Read

#### Classic Token Scopes (if using classic tokens):
- `repo` (full control - use sparingly)
- OR more granular:
  - `repo:status`
  - `repo_deployment`
  - `public_repo` (if public)
  - `security_events`

## 2. Secure Token Storage Best Practices

### Never Store Tokens In:
- Source code files
- Configuration files in repositories
- Plain text files
- Version control systems
- Client-side code

### Secure Storage Options:

#### Environment Variables
```bash
# Add to ~/.bashrc or ~/.zshrc (but not in repo)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
```

#### Using Secret Management Tools
```bash
# macOS Keychain
security add-generic-password -a "$USER" -s "github-token" -w "your-token-here"

# Retrieve token
security find-generic-password -a "$USER" -s "github-token" -w
```

#### GitHub Secrets (for GitHub Actions)
- Store in Settings → Secrets and variables → Actions
- Reference as `${{ secrets.GITHUB_TOKEN }}`

## 3. Security Alert Retrieval Scripts

### Python Implementation
```python
#!/usr/bin/env python3
"""
Secure GitHub Code Scanning API Client
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubSecurityScanner:
    """Secure client for GitHub Code Scanning API"""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize with token from environment or parameter"""
        self.token = token or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token not found. Set GITHUB_TOKEN environment variable.")
        
        # Validate token format (basic check)
        if not self._validate_token_format():
            raise ValueError("Invalid token format detected")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        # Setup session with retry strategy
        self.session = self._create_session()
    
    def _validate_token_format(self) -> bool:
        """Basic token format validation"""
        # GitHub tokens start with ghp_ (classic) or github_pat_ (fine-grained)
        return (self.token.startswith('ghp_') or 
                self.token.startswith('github_pat_'))
    
    def _create_session(self) -> requests.Session:
        """Create session with retry strategy"""
        session = requests.Session()
        retry = Retry(
            total=3,
            read=3,
            connect=3,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504)
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def get_code_scanning_alerts(self, owner: str, repo: str, 
                                 state: str = 'open') -> List[Dict]:
        """
        Retrieve code scanning alerts for a repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Alert state ('open', 'closed', 'dismissed', 'fixed')
        
        Returns:
            List of code scanning alerts
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/code-scanning/alerts"
        params = {'state': state, 'per_page': 100}
        
        try:
            alerts = []
            page = 1
            
            while True:
                params['page'] = page
                response = self.session.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                page_alerts = response.json()
                if not page_alerts:
                    break
                
                alerts.extend(page_alerts)
                
                # Check for pagination
                if 'Link' in response.headers:
                    if 'rel="next"' not in response.headers['Link']:
                        break
                    page += 1
                else:
                    break
            
            logger.info(f"Retrieved {len(alerts)} {state} alerts")
            return alerts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve alerts: {e}")
            raise
    
    def get_alert_details(self, owner: str, repo: str, alert_number: int) -> Dict:
        """Get detailed information about a specific alert"""
        url = f"{self.base_url}/repos/{owner}/{repo}/code-scanning/alerts/{alert_number}"
        
        try:
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve alert {alert_number}: {e}")
            raise
    
    def analyze_security_alerts(self, alerts: List[Dict]) -> Dict:
        """
        Analyze and categorize security alerts
        
        Returns:
            Dictionary with categorized alerts by severity and rule
        """
        analysis = {
            'summary': {
                'total': len(alerts),
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'warning': 0,
                'note': 0
            },
            'by_rule': {},
            'by_tool': {},
            'critical_alerts': [],
            'high_priority_alerts': []
        }
        
        for alert in alerts:
            # Categorize by severity
            severity = alert.get('rule', {}).get('severity', 'unknown').lower()
            if severity in analysis['summary']:
                analysis['summary'][severity] += 1
            
            # Track critical and high priority
            if severity in ['critical', 'error']:
                analysis['critical_alerts'].append({
                    'number': alert['number'],
                    'rule': alert['rule']['id'],
                    'description': alert['rule']['description'],
                    'path': alert['most_recent_instance']['location']['path'],
                    'line': alert['most_recent_instance']['location'].get('start_line')
                })
            elif severity in ['high', 'warning']:
                analysis['high_priority_alerts'].append({
                    'number': alert['number'],
                    'rule': alert['rule']['id'],
                    'description': alert['rule']['description']
                })
            
            # Group by rule
            rule_id = alert['rule']['id']
            if rule_id not in analysis['by_rule']:
                analysis['by_rule'][rule_id] = {
                    'count': 0,
                    'severity': alert['rule']['severity'],
                    'description': alert['rule']['description']
                }
            analysis['by_rule'][rule_id]['count'] += 1
            
            # Group by tool
            tool = alert['tool']['name']
            if tool not in analysis['by_tool']:
                analysis['by_tool'][tool] = 0
            analysis['by_tool'][tool] += 1
        
        return analysis
    
    def generate_security_report(self, owner: str, repo: str) -> str:
        """Generate comprehensive security report"""
        report_lines = [
            f"# Security Report for {owner}/{repo}",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Executive Summary"
        ]
        
        # Get all alerts
        open_alerts = self.get_code_scanning_alerts(owner, repo, 'open')
        closed_alerts = self.get_code_scanning_alerts(owner, repo, 'closed')
        
        # Analyze open alerts
        if open_alerts:
            analysis = self.analyze_security_alerts(open_alerts)
            
            report_lines.extend([
                f"- Total Open Alerts: {analysis['summary']['total']}",
                f"- Critical: {analysis['summary']['critical']}",
                f"- High: {analysis['summary']['high']}",
                f"- Medium: {analysis['summary']['medium']}",
                f"- Low: {analysis['summary']['low']}",
                "",
                "## Critical Issues Requiring Immediate Attention"
            ])
            
            if analysis['critical_alerts']:
                for alert in analysis['critical_alerts']:
                    report_lines.extend([
                        f"### Alert #{alert['number']}: {alert['rule']}",
                        f"- **File**: {alert['path']}",
                        f"- **Line**: {alert.get('line', 'N/A')}",
                        f"- **Description**: {alert['description']}",
                        ""
                    ])
            else:
                report_lines.append("No critical issues found.")
            
            report_lines.extend([
                "",
                "## Alerts by Security Rule"
            ])
            
            for rule_id, rule_info in sorted(analysis['by_rule'].items(), 
                                            key=lambda x: x[1]['count'], 
                                            reverse=True):
                report_lines.append(
                    f"- **{rule_id}** ({rule_info['severity']}): "
                    f"{rule_info['count']} instances - {rule_info['description']}"
                )
        else:
            report_lines.append("No open security alerts found.")
        
        report_lines.extend([
            "",
            "## Resolution History",
            f"- Closed/Fixed Alerts: {len(closed_alerts)}",
            "",
            "## Recommendations",
            "1. Address all critical and high severity issues immediately",
            "2. Review and update dependencies regularly",
            "3. Enable automated security scanning on all pull requests",
            "4. Implement security training for development team",
            "5. Establish a security review process for all code changes"
        ])
        
        return "\n".join(report_lines)

def main():
    """Main execution function"""
    # Example usage
    scanner = GitHubSecurityScanner()
    
    # Repository details
    owner = "xante8088"
    repo = "kasa-monitor"
    
    try:
        # Generate security report
        report = scanner.generate_security_report(owner, repo)
        
        # Save report
        report_file = f"security-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"Security report generated: {report_file}")
        
        # Get detailed analysis
        alerts = scanner.get_code_scanning_alerts(owner, repo)
        if alerts:
            analysis = scanner.analyze_security_alerts(alerts)
            print(f"\nSecurity Summary:")
            print(f"Total Alerts: {analysis['summary']['total']}")
            print(f"Critical: {analysis['summary']['critical']}")
            print(f"High: {analysis['summary']['high']}")
            
            if analysis['critical_alerts']:
                print("\n⚠️  CRITICAL ALERTS DETECTED!")
                for alert in analysis['critical_alerts']:
                    print(f"  - {alert['rule']}: {alert['path']}")
        
    except Exception as e:
        logger.error(f"Security scan failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Bash Implementation
```bash
#!/bin/bash

# Secure GitHub Code Scanning Script
# Requires: jq, curl

set -euo pipefail

# Configuration
GITHUB_API="https://api.github.com"
OWNER="xante8088"
REPO="kasa-monitor"

# Secure token retrieval
get_github_token() {
    # Try environment variable first
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        echo "$GITHUB_TOKEN"
        return
    fi
    
    # Try macOS keychain
    if command -v security &> /dev/null; then
        security find-generic-password -a "$USER" -s "github-token" -w 2>/dev/null || true
    fi
}

# Validate token
validate_token() {
    local token="$1"
    if [[ ! "$token" =~ ^(ghp_|github_pat_) ]]; then
        echo "Error: Invalid token format" >&2
        return 1
    fi
}

# Get code scanning alerts
get_alerts() {
    local token="$1"
    local state="${2:-open}"
    
    curl -s -H "Authorization: Bearer $token" \
         -H "Accept: application/vnd.github.v3+json" \
         "${GITHUB_API}/repos/${OWNER}/${REPO}/code-scanning/alerts?state=${state}&per_page=100"
}

# Analyze alerts
analyze_alerts() {
    local alerts="$1"
    
    echo "=== Security Alert Analysis ==="
    echo "Total alerts: $(echo "$alerts" | jq '. | length')"
    
    # Count by severity
    echo ""
    echo "By Severity:"
    echo "$alerts" | jq -r '
        group_by(.rule.severity) | 
        map({severity: .[0].rule.severity, count: length}) | 
        .[] | "  \(.severity): \(.count)"'
    
    # Critical alerts
    echo ""
    echo "Critical Alerts:"
    echo "$alerts" | jq -r '
        .[] | 
        select(.rule.severity == "critical" or .rule.severity == "error") |
        "  Alert #\(.number): \(.rule.id) - \(.most_recent_instance.location.path)"'
}

# Main execution
main() {
    echo "GitHub Security Scanner"
    echo "======================"
    
    # Get token securely
    TOKEN=$(get_github_token)
    if [ -z "$TOKEN" ]; then
        echo "Error: No GitHub token found" >&2
        echo "Set GITHUB_TOKEN environment variable or add to keychain" >&2
        exit 1
    fi
    
    # Validate token
    if ! validate_token "$TOKEN"; then
        exit 1
    fi
    
    echo "Scanning repository: ${OWNER}/${REPO}"
    echo ""
    
    # Get alerts
    ALERTS=$(get_alerts "$TOKEN" "open")
    
    if [ "$ALERTS" = "[]" ]; then
        echo "✅ No open security alerts found"
    else
        analyze_alerts "$ALERTS"
        
        # Save detailed report
        REPORT_FILE="security-report-$(date +%Y%m%d-%H%M%S).json"
        echo "$ALERTS" | jq '.' > "$REPORT_FILE"
        echo ""
        echo "Detailed report saved to: $REPORT_FILE"
    fi
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
```

## 4. GitHub Actions Integration

### Automated Security Review Workflow
```yaml
name: Security Review

on:
  pull_request:
    types: [opened, synchronize, reopened]
  schedule:
    - cron: '0 0 * * *'  # Daily security scan
  workflow_dispatch:

permissions:
  contents: read
  security-events: write
  pull-requests: write

jobs:
  security-review:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Run CodeQL Analysis
      uses: github/codeql-action/analyze@v2
      
    - name: Get Code Scanning Alerts
      id: get-alerts
      uses: actions/github-script@v7
      with:
        github-token: ${{ secrets.GITHUB_TOKEN }}
        script: |
          const alerts = await github.rest.codeScanning.listAlertsForRepo({
            owner: context.repo.owner,
            repo: context.repo.repo,
            state: 'open'
          });
          
          const critical = alerts.data.filter(a => 
            a.rule.severity === 'critical' || a.rule.severity === 'error'
          );
          
          if (critical.length > 0) {
            core.setFailed(`Found ${critical.length} critical security issues`);
          }
          
          return alerts.data;
    
    - name: Comment on PR
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v7
      with:
        github-token: ${{ secrets.GITHUB_TOKEN }}
        script: |
          const alerts = ${{ steps.get-alerts.outputs.result }};
          
          let comment = '## 🔒 Security Review Results\n\n';
          
          if (alerts.length === 0) {
            comment += '✅ No security issues detected';
          } else {
            const summary = alerts.reduce((acc, alert) => {
              const severity = alert.rule.severity;
              acc[severity] = (acc[severity] || 0) + 1;
              return acc;
            }, {});
            
            comment += `Found ${alerts.length} security alerts:\n\n`;
            Object.entries(summary).forEach(([severity, count]) => {
              comment += `- **${severity}**: ${count}\n`;
            });
            
            comment += '\n### Required Actions:\n';
            comment += '1. Review all security alerts\n';
            comment += '2. Fix critical and high severity issues\n';
            comment += '3. Request re-review after fixes\n';
          }
          
          await github.rest.issues.createComment({
            owner: context.repo.owner,
            repo: context.repo.repo,
            issue_number: context.issue.number,
            body: comment
          });
```

## 5. Security Best Practices

### Token Rotation
```bash
#!/bin/bash
# Token rotation reminder script

TOKEN_AGE_DAYS=60
TOKEN_CREATION_FILE="$HOME/.github_token_created"

if [ -f "$TOKEN_CREATION_FILE" ]; then
    CREATED=$(cat "$TOKEN_CREATION_FILE")
    NOW=$(date +%s)
    AGE_DAYS=$(( (NOW - CREATED) / 86400 ))
    
    if [ $AGE_DAYS -gt $TOKEN_AGE_DAYS ]; then
        echo "⚠️  WARNING: GitHub token is $AGE_DAYS days old"
        echo "Please rotate your token for security"
    fi
else
    date +%s > "$TOKEN_CREATION_FILE"
fi
```

### Secure Configuration File
```python
# config_secure.py
import os
from cryptography.fernet import Fernet

class SecureConfig:
    """Secure configuration manager"""
    
    @staticmethod
    def get_encrypted_token():
        """Retrieve and decrypt token"""
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            raise ValueError("Encryption key not found")
        
        cipher = Fernet(key.encode())
        
        # Read encrypted token from file
        with open('.token.enc', 'rb') as f:
            encrypted_token = f.read()
        
        return cipher.decrypt(encrypted_token).decode()
    
    @staticmethod
    def store_encrypted_token(token):
        """Encrypt and store token"""
        key = Fernet.generate_key()
        cipher = Fernet(key)
        
        encrypted = cipher.encrypt(token.encode())
        
        with open('.token.enc', 'wb') as f:
            f.write(encrypted)
        
        print(f"Store this key securely: {key.decode()}")
        print("Export as: export ENCRYPTION_KEY='<key>'")
```

## 6. Integration Patterns

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: security-scan
        name: GitHub Security Scan
        entry: python3 github_security_scanner.py
        language: system
        pass_filenames: false
        always_run: true
```

### CI/CD Pipeline Integration
```yaml
# Example for various CI/CD platforms

# Jenkins Pipeline
pipeline {
    agent any
    
    environment {
        GITHUB_TOKEN = credentials('github-token')
    }
    
    stages {
        stage('Security Scan') {
            steps {
                sh 'python3 github_security_scanner.py'
            }
        }
    }
    
    post {
        always {
            publishHTML([
                reportDir: '.',
                reportFiles: 'security-report-*.md',
                reportName: 'Security Report'
            ])
        }
    }
}

# GitLab CI
security-scan:
  stage: test
  script:
    - python3 github_security_scanner.py
  artifacts:
    reports:
      security: security-report.json
  only:
    - merge_requests
    - master
```

## 7. Monitoring and Alerting

### Webhook Integration
```python
# webhook_handler.py
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

@app.route('/github-webhook', methods=['POST'])
def handle_webhook():
    # Verify webhook signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    event = request.headers.get('X-GitHub-Event')
    
    if event == 'code_scanning_alert':
        payload = request.json
        alert = payload['alert']
        
        if alert['rule']['severity'] in ['critical', 'high']:
            # Send immediate notification
            send_security_alert(alert)
    
    return jsonify({'status': 'processed'}), 200

def verify_signature(payload, signature):
    secret = os.environ.get('WEBHOOK_SECRET')
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## 8. Security Checklist

### Before Deployment
- [ ] Token stored securely (environment variable or secret manager)
- [ ] Token has minimal required permissions
- [ ] Token expiration date set (< 90 days)
- [ ] Encryption keys properly managed
- [ ] Audit logging enabled
- [ ] Error handling doesn't expose sensitive data
- [ ] HTTPS enforced for all API calls
- [ ] Rate limiting implemented
- [ ] Webhook signatures verified
- [ ] Regular token rotation scheduled

### Operational Security
- [ ] Monitor for unusual API activity
- [ ] Review access logs regularly
- [ ] Alert on critical security findings
- [ ] Automated remediation for common issues
- [ ] Security reports archived securely
- [ ] Incident response plan in place

## Support Resources

- [GitHub Code Scanning API Docs](https://docs.github.com/en/rest/code-scanning)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)