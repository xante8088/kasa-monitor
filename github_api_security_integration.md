# GitHub Code Scanning API - Security Integration Guide

## Executive Summary

GitHub's Code Scanning API provides programmatic access to security vulnerability data detected through static analysis. While direct access requires authentication, the API offers comprehensive capabilities for integrating security findings into code review processes.

## API Access Status

### Current Limitations
- **Authentication Required**: The API endpoint requires a Personal Access Token with `security_events` scope
- **Repository Settings**: Code scanning must be enabled in the repository settings
- **Access Level**: Read access to the repository and security alerts is required

### Available Endpoints

```bash
# Primary Code Scanning Endpoints
GET  /repos/{owner}/{repo}/code-scanning/alerts
GET  /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}
PATCH /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}
GET  /repos/{owner}/{repo}/code-scanning/analyses
GET  /repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}
POST /repos/{owner}/{repo}/code-scanning/sarif
```

## Security Capabilities

### 1. **Vulnerability Detection**
- SQL injection vulnerabilities
- Cross-site scripting (XSS)
- Path traversal attacks
- Command injection
- Buffer overflows
- Cryptographic weaknesses
- Authentication bypasses
- Information disclosure

### 2. **Alert Management**
- **States**: open, closed, dismissed, fixed
- **Severities**: error, warning, note
- **Security Levels**: critical, high, medium, low
- **Dismissal Reasons**: false positive, won't fix, used in tests

### 3. **Integration Features**
- SARIF format support for third-party tools
- Webhook notifications for new alerts
- Pull request annotations
- Branch protection integration

## Implementation Guide

### Step 1: Enable Authentication

```bash
# Set GitHub Personal Access Token
export GITHUB_TOKEN="ghp_your_token_here"

# Required token scope: security_events
```

### Step 2: Enable Code Scanning

1. Navigate to repository Settings → Security → Code scanning
2. Set up CodeQL analysis or third-party tools
3. Configure scanning triggers (push, pull request, schedule)

### Step 3: Use the Security Scanner Tool

```bash
# Make the script executable
chmod +x github_security_scanner.py

# Run security analysis
python github_security_scanner.py xante8088 kasa-monitor
```

### Step 4: Integrate into CI/CD Pipeline

```yaml
# GitHub Actions example
name: Security Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run CodeQL Analysis
        uses: github/codeql-action/analyze@v2
      
      - name: Check Security Alerts
        run: |
          python github_security_scanner.py ${{ github.repository_owner }} ${{ github.event.repository.name }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Security Review Process Integration

### Automated Review Workflow

1. **Pre-commit Scanning**
   - Run local security checks before pushing
   - Validate against security policies
   - Check for hardcoded secrets

2. **Pull Request Analysis**
   - Automatic code scanning on PR creation
   - Security alert annotations in PR
   - Block merge if critical issues found

3. **Continuous Monitoring**
   - Scheduled security scans
   - Alert notifications to security team
   - Trend analysis and reporting

### Manual Review Enhancement

The API data enhances manual reviews by:
- Providing context for security decisions
- Highlighting high-risk code areas
- Tracking remediation progress
- Maintaining audit trails

## API Response Examples

### Successful Alert Retrieval
```json
[
  {
    "number": 1,
    "created_at": "2024-01-15T08:23:45Z",
    "url": "https://api.github.com/repos/owner/repo/code-scanning/alerts/1",
    "html_url": "https://github.com/owner/repo/security/code-scanning/1",
    "state": "open",
    "dismissed_by": null,
    "dismissed_at": null,
    "dismissed_reason": null,
    "rule": {
      "id": "js/sql-injection",
      "severity": "error",
      "description": "Database query built from user-controlled sources",
      "name": "SQL injection",
      "security_severity_level": "high"
    },
    "tool": {
      "name": "CodeQL",
      "version": "2.15.3"
    },
    "most_recent_instance": {
      "location": {
        "path": "src/database/queries.js",
        "start_line": 42,
        "end_line": 45
      }
    }
  }
]
```

### Authentication Error
```json
{
  "message": "You are not authorized to read code scanning alerts.",
  "documentation_url": "https://docs.github.com/rest/code-scanning",
  "status": "403"
}
```

## Security Findings Classification

### Priority Levels

| Level | Severity | Response Time | Action Required |
|-------|----------|---------------|-----------------|
| CRITICAL | CVE with CVSS > 9.0 | Immediate | Block deployment |
| HIGH | Security vulnerability | 24 hours | Fix before merge |
| MEDIUM | Best practice violation | 1 week | Plan remediation |
| LOW | Code quality issue | Sprint cycle | Track for improvement |

## Limitations and Considerations

1. **API Rate Limits**
   - 5,000 requests/hour for authenticated requests
   - 60 requests/hour for unauthenticated

2. **Data Availability**
   - Alerts retained for 90 days after fix
   - Maximum 1000 alerts per query
   - SARIF uploads limited to 10MB

3. **Access Requirements**
   - Repository must have code scanning enabled
   - Token needs appropriate scopes
   - Private repos require additional permissions

## Recommendations

### For kasa-monitor Repository

1. **Enable Code Scanning**
   - Set up CodeQL analysis for JavaScript/TypeScript
   - Configure security policy file
   - Enable Dependabot alerts

2. **Implement Security Gates**
   - Require security review for PRs
   - Block merge on critical findings
   - Automate security testing

3. **Establish Review Process**
   - Weekly security alert review
   - Monthly trend analysis
   - Quarterly security audits

## Conclusion

While direct API access to the kasa-monitor repository's code scanning results requires proper authentication, the GitHub Code Scanning API provides robust capabilities for:

✅ **Retrieving** security vulnerability data
✅ **Analyzing** code security issues systematically  
✅ **Integrating** findings into review processes
✅ **Automating** security gates and controls

The provided `github_security_scanner.py` tool demonstrates how to properly authenticate and leverage these APIs for comprehensive security reviews once appropriate access is configured.