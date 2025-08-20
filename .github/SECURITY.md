# Security Policy

## Supported Versions

We actively support and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Kasa Monitor, please follow these steps:

### 1. Do NOT Create a Public Issue

Please **do not** create a public GitHub issue for security vulnerabilities. This could put users at risk.

### 2. Report Privately

Send your security report via one of these methods:

- **Email**: Send to `security@kasa-monitor.example.com` (preferred)
- **GitHub Security Advisory**: Use the [private vulnerability reporting feature](https://github.com/xante8088/kasa-monitor/security/advisories/new)

### 3. Include These Details

Please include as much information as possible:

- **Description**: A clear description of the vulnerability
- **Impact**: What an attacker could achieve by exploiting this
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Proof of Concept**: Code or screenshots demonstrating the vulnerability
- **Suggested Fix**: If you have ideas on how to fix it
- **Your Contact Info**: So we can follow up with questions

### 4. What to Expect

- **Acknowledgment**: We'll acknowledge receipt within 48 hours
- **Initial Assessment**: We'll provide an initial assessment within 5 business days
- **Updates**: We'll keep you informed of our progress
- **Resolution**: We aim to resolve critical issues within 30 days
- **Credit**: We'll credit you in our security advisory (if you wish)

## Security Features

### Authentication & Authorization
- JWT-based authentication with secure secret management
- Role-based access control (RBAC)
- Password policy enforcement
- Optional two-factor authentication (2FA)

### Data Protection
- Encrypted data storage for sensitive information
- Secure file upload with content validation
- Input sanitization and validation
- SQL injection protection

### Network Security
- CORS configuration for controlled access
- Rate limiting to prevent abuse
- HTTPS support with SSL/TLS configuration
- Network isolation options with Docker

### Monitoring & Logging
- Comprehensive audit logging
- Security event monitoring
- Anomaly detection for suspicious activities
- Automated alerting for security incidents

## Security Best Practices for Users

### Installation
1. **Use HTTPS**: Always deploy with SSL/TLS certificates
2. **Change Default Credentials**: Update all default passwords
3. **Network Isolation**: Use firewall rules to restrict access
4. **Regular Updates**: Keep the application and dependencies updated

### Configuration
1. **Environment Variables**: Store secrets in environment variables, not code
2. **Database Security**: Use strong database passwords and encryption
3. **Backup Security**: Encrypt and secure backup files
4. **Access Control**: Implement principle of least privilege

### Monitoring
1. **Log Monitoring**: Regularly review audit logs
2. **Security Scanning**: Run security scans on your deployment
3. **Dependency Monitoring**: Monitor for vulnerable dependencies
4. **Incident Response**: Have a plan for security incidents

## Known Security Considerations

### Network Exposure
- The application discovers devices on your local network
- Ensure your network is properly segmented and secured
- Monitor device access patterns for anomalies

### Data Retention
- Energy usage data is stored indefinitely by default
- Configure data retention policies as needed
- Securely dispose of old backup files

### Third-Party Integrations
- Review permissions for any plugins or integrations
- Monitor third-party service access
- Keep integrations updated

## Security Updates

We regularly update our security measures:

- **Dependency Updates**: Automated via Dependabot
- **Security Patches**: Released as soon as possible
- **Vulnerability Scanning**: Continuous monitoring
- **Code Reviews**: All changes undergo security review

## Contact

For security-related questions or concerns:

- **Security Team**: `security@kasa-monitor.example.com`
- **General Contact**: Create an issue for non-security questions
- **Documentation**: Check our [Security Guide](https://github.com/xante8088/kasa-monitor/wiki/Security-Guide)

---

**Remember**: When in doubt, report it. We'd rather investigate a false positive than miss a real security issue.