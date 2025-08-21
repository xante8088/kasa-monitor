#!/usr/bin/env python3
"""Security vulnerability scanner for the kasa-monitor backend"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

security_issues = {
    'critical': [],
    'high': [],
    'medium': [],
    'low': []
}

# Check for hardcoded secrets
secret_patterns = [
    (r'["\'](sk_live_|sk_test_)[a-zA-Z0-9]{24,}["\']', 'Stripe API Key'),
    (r'["\'](xox[baprs]-[a-zA-Z0-9-]+)["\']', 'Slack Token'),
    (r'["\']AIza[a-zA-Z0-9_-]{35}["\']', 'Google API Key'),
    (r'["\'](ghp_|github_pat_)[a-zA-Z0-9]{36,}["\']', 'GitHub Token'),
    (r'password\s*=\s*["\'][^"\']{8,}["\']', 'Hardcoded Password'),
    (r'SECRET_KEY\s*=\s*["\'][^"\']+["\']', 'Hardcoded Secret Key'),
    (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API Key'),
]

# Check for SQL injection vulnerabilities
sql_patterns = [
    (r'execute\([^)]*%', 'SQL Injection - String formatting'),
    (r'execute\([^)]*f["\'`]', 'SQL Injection - f-string'),
    (r'execute\([^)]*\+', 'SQL Injection - String concatenation'),
    (r'executemany\([^)]*%', 'SQL Injection - String formatting in executemany'),
    (r'cursor\.execute\([^)]*\.format\(', 'SQL Injection - format method'),
]

# Check for command injection
cmd_patterns = [
    (r'os\.system\([^)]*\+', 'Command Injection - String concatenation'),
    (r'subprocess\.\w+\([^)]*shell=True', 'Command Injection - Shell=True'),
    (r'os\.popen\(', 'Command Injection - os.popen usage'),
]

def scan_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip migration, test, and security fix files
        path_str = str(filepath).lower()
        if any(skip in path_str for skip in ['migration', 'test', 'security_fix', '__pycache__']):
            return
            
        # Check for secrets
        for pattern, desc in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Skip if it's loading from env
                for match in matches:
                    line_with_match = [line for line in content.split('\n') if match in line][0] if matches else ''
                    if 'os.getenv' not in line_with_match and 'os.environ' not in line_with_match:
                        security_issues['critical'].append({
                            'file': str(filepath.relative_to(Path.cwd())),
                            'issue': desc,
                            'type': 'secret',
                            'match': match[:30] + '...' if len(match) > 30 else match
                        })
        
        # Check for SQL injection
        for pattern, desc in sql_patterns:
            if re.search(pattern, content):
                # Check if it's using parameterized queries
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if re.search(pattern, line):
                        # Check context (previous and next lines)
                        context = '\n'.join(lines[max(0,i-1):min(len(lines),i+2)])
                        # Skip if using ? placeholders or parameterized queries
                        if '?' not in context and '%s' not in context:
                            security_issues['high'].append({
                                'file': str(filepath.relative_to(Path.cwd())),
                                'issue': desc,
                                'type': 'injection',
                                'line': i + 1
                            })
        
        # Check for command injection
        for pattern, desc in cmd_patterns:
            if re.search(pattern, content):
                security_issues['high'].append({
                    'file': str(filepath.relative_to(Path.cwd())),
                    'issue': desc,
                    'type': 'command_injection'
                })
                
        # Check for insecure random
        if 'random.random' in content or 'random.randint' in content:
            if any(term in content.lower() for term in ['crypto', 'token', 'secret', 'password', 'jwt']):
                security_issues['high'].append({
                    'file': str(filepath.relative_to(Path.cwd())),
                    'issue': 'Insecure random for cryptographic use',
                    'type': 'crypto'
                })
                
        # Check for eval/exec usage
        if 'eval(' in content or 'exec(' in content:
            security_issues['critical'].append({
                'file': str(filepath.relative_to(Path.cwd())),
                'issue': 'Dangerous eval/exec usage',
                'type': 'code_execution'
            })
            
        # Check for pickle usage (deserialization vulnerability)
        if 'pickle.loads' in content or 'pickle.load' in content:
            security_issues['high'].append({
                'file': str(filepath.relative_to(Path.cwd())),
                'issue': 'Insecure deserialization with pickle',
                'type': 'deserialization'
            })
            
        # Check for XXE vulnerabilities
        if 'etree.parse' in content or 'etree.fromstring' in content:
            if 'resolve_entities=False' not in content:
                security_issues['medium'].append({
                    'file': str(filepath.relative_to(Path.cwd())),
                    'issue': 'Potential XXE vulnerability',
                    'type': 'xxe'
                })
                
        # Check for path traversal
        if '../' in content or '..\\' in content:
            security_issues['medium'].append({
                'file': str(filepath.relative_to(Path.cwd())),
                'issue': 'Potential path traversal',
                'type': 'path_traversal'
            })
            
    except Exception as e:
        pass

# Check specific security configurations
def check_security_configs():
    # Check .env file
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
            
        # Check JWT secret
        if 'JWT_SECRET_KEY=' in env_content:
            jwt_secret = re.search(r'JWT_SECRET_KEY=(.+)', env_content)
            if jwt_secret:
                secret_value = jwt_secret.group(1).strip()
                if len(secret_value) < 32:
                    security_issues['high'].append({
                        'file': '.env',
                        'issue': 'JWT secret key is too short (should be at least 32 characters)',
                        'type': 'config'
                    })
                if 'change-in-production' in secret_value or 'your-secret-key-here' in secret_value:
                    security_issues['critical'].append({
                        'file': '.env',
                        'issue': 'JWT secret key contains default/example value',
                        'type': 'config'
                    })
        else:
            security_issues['critical'].append({
                'file': '.env',
                'issue': 'JWT_SECRET_KEY not found in .env',
                'type': 'config'
            })
            
        # Check CORS configuration
        if 'CORS_ORIGINS=' not in env_content and 'ALLOWED_ORIGINS=' not in env_content:
            security_issues['medium'].append({
                'file': '.env',
                'issue': 'CORS origins not configured',
                'type': 'config'
            })
    else:
        security_issues['critical'].append({
            'file': '.env',
            'issue': '.env file not found',
            'type': 'config'
        })
        
    # Check if security headers are implemented
    main_file = Path('main.py')
    if main_file.exists():
        with open(main_file, 'r') as f:
            main_content = f.read()
            
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]
        
        for header in required_headers:
            if header not in main_content:
                security_issues['high'].append({
                    'file': 'main.py',
                    'issue': f'Security header {header} not implemented',
                    'type': 'headers'
                })

# Scan all Python files
print("Starting security scan...")
for py_file in Path('.').rglob('*.py'):
    scan_file(py_file)

# Check security configurations
check_security_configs()

# Remove duplicates
for severity in security_issues:
    seen = set()
    unique_issues = []
    for issue in security_issues[severity]:
        key = f"{issue['file']}:{issue['issue']}"
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)
    security_issues[severity] = unique_issues

# Calculate statistics
total_issues = sum(len(issues) for issues in security_issues.values())

# Print results
print("\n" + "="*60)
print("SECURITY SCAN RESULTS")
print("="*60)
print(f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nTotal Issues Found: {total_issues}")
print(f"  Critical: {len(security_issues['critical'])}")
print(f"  High:     {len(security_issues['high'])}")
print(f"  Medium:   {len(security_issues['medium'])}")
print(f"  Low:      {len(security_issues['low'])}")
print()

if security_issues['critical']:
    print("🔴 CRITICAL ISSUES (Immediate action required):")
    print("-" * 50)
    for issue in security_issues['critical'][:10]:
        print(f"  • {issue['file']}")
        print(f"    Issue: {issue['issue']}")
        if 'match' in issue:
            print(f"    Found: {issue['match']}")
        print()
    if len(security_issues['critical']) > 10:
        print(f"  ... and {len(security_issues['critical']) - 10} more critical issues")
    print()

if security_issues['high']:
    print("🟠 HIGH PRIORITY ISSUES:")
    print("-" * 50)
    for issue in security_issues['high'][:10]:
        print(f"  • {issue['file']}")
        print(f"    Issue: {issue['issue']}")
        if 'line' in issue:
            print(f"    Line: {issue['line']}")
        print()
    if len(security_issues['high']) > 10:
        print(f"  ... and {len(security_issues['high']) - 10} more high priority issues")
    print()

if security_issues['medium']:
    print("🟡 MEDIUM PRIORITY ISSUES:")
    print("-" * 50)
    for issue in security_issues['medium'][:5]:
        print(f"  • {issue['file']}: {issue['issue']}")
    if len(security_issues['medium']) > 5:
        print(f"  ... and {len(security_issues['medium']) - 5} more medium priority issues")
    print()

# Security posture assessment
print("\n" + "="*60)
print("SECURITY POSTURE ASSESSMENT")
print("="*60)

if total_issues == 0:
    print("✅ EXCELLENT: No security issues detected!")
elif len(security_issues['critical']) == 0 and len(security_issues['high']) < 5:
    print("✅ GOOD: No critical issues, minimal high priority issues")
elif len(security_issues['critical']) < 3:
    print("⚠️  FAIR: Some critical issues need immediate attention")
else:
    print("❌ POOR: Multiple critical security issues detected")

print("\nRECOMMENDATIONS:")
print("-" * 50)
if len(security_issues['critical']) > 0:
    print("1. ❗ Address all CRITICAL issues immediately")
    print("   - Remove hardcoded secrets and use environment variables")
    print("   - Fix any code execution vulnerabilities")
    
if len(security_issues['high']) > 0:
    print("2. ⚠️  Fix HIGH priority issues before deployment")
    print("   - Use parameterized queries for all database operations")
    print("   - Replace insecure random with secrets module for crypto")
    
print("3. 📋 Review and fix medium/low priority issues")
print("4. 🔒 Implement security best practices:")
print("   - Regular dependency updates")
print("   - Security headers on all responses")
print("   - Input validation and sanitization")
print("   - Proper error handling without information disclosure")

# Save detailed report
report_file = Path('security_scan_report.json')
with open(report_file, 'w') as f:
    json.dump({
        'scan_date': datetime.now().isoformat(),
        'summary': {
            'total': total_issues,
            'critical': len(security_issues['critical']),
            'high': len(security_issues['high']),
            'medium': len(security_issues['medium']),
            'low': len(security_issues['low'])
        },
        'issues': security_issues
    }, f, indent=2)
    
print(f"\n📄 Detailed report saved to: {report_file}")