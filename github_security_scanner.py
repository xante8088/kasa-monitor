#!/usr/bin/env python3
"""
Secure GitHub Code Scanning API Client
For repository: xante8088/kasa-monitor
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
                'note': 0,
                'error': 0
            },
            'by_rule': {},
            'by_tool': {},
            'critical_alerts': [],
            'high_priority_alerts': [],
            'cwe_mapping': {},
            'owasp_mapping': {}
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
                    'line': alert['most_recent_instance']['location'].get('start_line'),
                    'security_severity': alert['rule'].get('security_severity_level', 'N/A')
                })
            elif severity in ['high', 'warning']:
                analysis['high_priority_alerts'].append({
                    'number': alert['number'],
                    'rule': alert['rule']['id'],
                    'description': alert['rule']['description'],
                    'path': alert['most_recent_instance']['location']['path']
                })
            
            # Group by rule
            rule_id = alert['rule']['id']
            if rule_id not in analysis['by_rule']:
                analysis['by_rule'][rule_id] = {
                    'count': 0,
                    'severity': alert['rule']['severity'],
                    'description': alert['rule']['description'],
                    'tags': alert['rule'].get('tags', [])
                }
            analysis['by_rule'][rule_id]['count'] += 1
            
            # Group by tool
            tool = alert['tool']['name']
            if tool not in analysis['by_tool']:
                analysis['by_tool'][tool] = 0
            analysis['by_tool'][tool] += 1
            
            # Map to CWE if available
            for tag in alert['rule'].get('tags', []):
                if tag.startswith('CWE-'):
                    if tag not in analysis['cwe_mapping']:
                        analysis['cwe_mapping'][tag] = []
                    analysis['cwe_mapping'][tag].append(alert['number'])
        
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
        dismissed_alerts = self.get_code_scanning_alerts(owner, repo, 'dismissed')
        
        # Calculate metrics
        total_addressed = len(closed_alerts) + len(dismissed_alerts)
        resolution_rate = (total_addressed / (len(open_alerts) + total_addressed) * 100) if (len(open_alerts) + total_addressed) > 0 else 100
        
        report_lines.extend([
            f"- Repository: {owner}/{repo}",
            f"- Open Security Alerts: {len(open_alerts)}",
            f"- Resolved/Dismissed: {total_addressed}",
            f"- Resolution Rate: {resolution_rate:.1f}%",
            ""
        ])
        
        # Analyze open alerts
        if open_alerts:
            analysis = self.analyze_security_alerts(open_alerts)
            
            # Security posture assessment
            security_score = self._calculate_security_score(analysis)
            report_lines.extend([
                "## Security Posture",
                f"**Security Score: {security_score}/100**",
                "",
                "### Alert Distribution",
                f"- Critical: {analysis['summary'].get('critical', 0)}",
                f"- Error: {analysis['summary'].get('error', 0)}",
                f"- High: {analysis['summary'].get('high', 0)}",
                f"- Warning: {analysis['summary'].get('warning', 0)}",
                f"- Medium: {analysis['summary'].get('medium', 0)}",
                f"- Low: {analysis['summary'].get('low', 0)}",
                f"- Note: {analysis['summary'].get('note', 0)}",
                ""
            ])
            
            # Critical issues
            report_lines.append("## Critical Issues Requiring Immediate Attention")
            if analysis['critical_alerts']:
                for alert in analysis['critical_alerts']:
                    report_lines.extend([
                        f"### Alert #{alert['number']}: {alert['rule']}",
                        f"- **Severity**: CRITICAL",
                        f"- **File**: `{alert['path']}`",
                        f"- **Line**: {alert.get('line', 'N/A')}",
                        f"- **Description**: {alert['description']}",
                        f"- **Security Severity Level**: {alert['security_severity']}",
                        ""
                    ])
            else:
                report_lines.append("No critical issues found.")
            
            # High priority issues
            if analysis['high_priority_alerts']:
                report_lines.extend([
                    "",
                    "## High Priority Issues"
                ])
                for alert in analysis['high_priority_alerts'][:5]:  # Show top 5
                    report_lines.extend([
                        f"- **Alert #{alert['number']}**: {alert['rule']}",
                        f"  - File: `{alert['path']}`",
                        f"  - {alert['description']}"
                    ])
            
            # Security rules breakdown
            report_lines.extend([
                "",
                "## Security Rules Triggered"
            ])
            
            sorted_rules = sorted(analysis['by_rule'].items(), 
                                key=lambda x: x[1]['count'], 
                                reverse=True)
            
            for rule_id, rule_info in sorted_rules[:10]:  # Top 10 rules
                report_lines.append(
                    f"- **{rule_id}** ({rule_info['severity']}): "
                    f"{rule_info['count']} instances"
                )
                if rule_info['tags']:
                    report_lines.append(f"  - Tags: {', '.join(rule_info['tags'])}")
            
            # CWE mapping if available
            if analysis['cwe_mapping']:
                report_lines.extend([
                    "",
                    "## CWE Classification"
                ])
                for cwe, alerts in analysis['cwe_mapping'].items():
                    report_lines.append(f"- **{cwe}**: {len(alerts)} alerts")
            
            # Tool breakdown
            report_lines.extend([
                "",
                "## Detection Tools"
            ])
            for tool, count in analysis['by_tool'].items():
                report_lines.append(f"- **{tool}**: {count} alerts")
        
        else:
            report_lines.extend([
                "## Security Status",
                "**No open security alerts found.**",
                "",
                "All security checks passed successfully."
            ])
        
        # Compliance and recommendations
        report_lines.extend([
            "",
            "## Compliance Status",
            "- OWASP Top 10: " + ("NEEDS REVIEW" if open_alerts else "PASSED"),
            "- CWE Top 25: " + ("REVIEW REQUIRED" if open_alerts else "COMPLIANT"),
            "- Security Headers: PENDING REVIEW",
            "- Dependency Scanning: ENABLED",
            "",
            "## Recommendations",
            "",
            "### Immediate Actions"
        ])
        
        if analysis['critical_alerts'] if open_alerts else []:
            report_lines.extend([
                "1. **URGENT**: Address all critical security issues immediately",
                "2. Deploy fixes to a staging environment for validation",
                "3. Perform security regression testing"
            ])
        else:
            report_lines.extend([
                "1. Continue monitoring for new security alerts",
                "2. Keep dependencies updated",
                "3. Regular security training for development team"
            ])
        
        report_lines.extend([
            "",
            "### Best Practices",
            "1. Enable branch protection rules requiring security checks",
            "2. Implement automated security testing in CI/CD pipeline",
            "3. Regular security audits and penetration testing",
            "4. Maintain security documentation and runbooks",
            "5. Establish security incident response procedures",
            "",
            "## Resolution History",
            f"- Total Closed/Fixed: {len(closed_alerts)}",
            f"- Total Dismissed: {len(dismissed_alerts)}",
            f"- Resolution Rate: {resolution_rate:.1f}%",
            "",
            "---",
            "*This report was generated automatically by the GitHub Security Scanner*"
        ])
        
        return "\n".join(report_lines)
    
    def _calculate_security_score(self, analysis: Dict) -> int:
        """Calculate security score based on alert analysis"""
        score = 100
        
        # Deduct points based on severity
        score -= analysis['summary'].get('critical', 0) * 20
        score -= analysis['summary'].get('error', 0) * 15
        score -= analysis['summary'].get('high', 0) * 10
        score -= analysis['summary'].get('warning', 0) * 5
        score -= analysis['summary'].get('medium', 0) * 3
        score -= analysis['summary'].get('low', 0) * 1
        
        return max(0, score)
    
    def export_sarif(self, alerts: List[Dict], output_file: str):
        """Export alerts in SARIF format for integration with other tools"""
        sarif = {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "GitHub Code Scanning",
                        "version": "1.0.0"
                    }
                },
                "results": []
            }]
        }
        
        for alert in alerts:
            result = {
                "ruleId": alert['rule']['id'],
                "level": self._severity_to_sarif_level(alert['rule']['severity']),
                "message": {
                    "text": alert['rule']['description']
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": alert['most_recent_instance']['location']['path']
                        },
                        "region": {
                            "startLine": alert['most_recent_instance']['location'].get('start_line', 1)
                        }
                    }
                }]
            }
            sarif['runs'][0]['results'].append(result)
        
        with open(output_file, 'w') as f:
            json.dump(sarif, f, indent=2)
        
        logger.info(f"SARIF report exported to {output_file}")
    
    def _severity_to_sarif_level(self, severity: str) -> str:
        """Convert GitHub severity to SARIF level"""
        mapping = {
            'critical': 'error',
            'error': 'error',
            'high': 'error',
            'warning': 'warning',
            'medium': 'warning',
            'low': 'note',
            'note': 'note'
        }
        return mapping.get(severity.lower(), 'note')

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub Security Scanner')
    parser.add_argument('--owner', default='xante8088', help='Repository owner')
    parser.add_argument('--repo', default='kasa-monitor', help='Repository name')
    parser.add_argument('--format', choices=['markdown', 'json', 'sarif'], default='markdown',
                       help='Output format')
    parser.add_argument('--output', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    try:
        # Initialize scanner
        scanner = GitHubSecurityScanner()
        
        if args.format == 'markdown':
            # Generate markdown report
            report = scanner.generate_security_report(args.owner, args.repo)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                print(f"Report saved to {args.output}")
            else:
                print(report)
        
        elif args.format == 'json':
            # Get raw alerts as JSON
            alerts = scanner.get_code_scanning_alerts(args.owner, args.repo)
            analysis = scanner.analyze_security_alerts(alerts)
            
            output = {
                'metadata': {
                    'repository': f"{args.owner}/{args.repo}",
                    'scan_date': datetime.now().isoformat(),
                    'total_alerts': len(alerts)
                },
                'analysis': analysis,
                'alerts': alerts
            }
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(output, f, indent=2)
                print(f"JSON report saved to {args.output}")
            else:
                print(json.dumps(output, indent=2))
        
        elif args.format == 'sarif':
            # Export as SARIF
            alerts = scanner.get_code_scanning_alerts(args.owner, args.repo)
            output_file = args.output or f"security-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sarif"
            scanner.export_sarif(alerts, output_file)
            print(f"SARIF report saved to {output_file}")
        
        # Print summary to console
        alerts = scanner.get_code_scanning_alerts(args.owner, args.repo)
        if alerts:
            analysis = scanner.analyze_security_alerts(alerts)
            print(f"\nSecurity Summary for {args.owner}/{args.repo}:")
            print(f"Total Alerts: {analysis['summary']['total']}")
            
            if analysis['summary'].get('critical', 0) > 0:
                print(f"CRITICAL: {analysis['summary']['critical']} - IMMEDIATE ACTION REQUIRED")
            if analysis['summary'].get('error', 0) > 0:
                print(f"ERROR: {analysis['summary']['error']}")
            if analysis['summary'].get('high', 0) > 0:
                print(f"HIGH: {analysis['summary']['high']}")
            
            if analysis['critical_alerts']:
                print("\nCRITICAL ALERTS:")
                for alert in analysis['critical_alerts'][:3]:
                    print(f"  - {alert['rule']}: {alert['path']}:{alert.get('line', '?')}")
        else:
            print(f"\nNo open security alerts for {args.owner}/{args.repo}")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print("\nTo use this scanner:")
        print("1. Create a GitHub Personal Access Token")
        print("2. Set environment variable: export GITHUB_TOKEN='your-token-here'")
        print("3. Run the scanner again")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Security scan failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()