# Security Policy

## Vulnerability Scanning & Remediation

This document outlines security best practices and vulnerability management for Kasa Monitor.

## Docker Security Scanning

### Using Docker Scout

```bash
# Build and scan image
docker build -t kasa-monitor:latest .
docker scout cves kasa-monitor:latest

# Get detailed recommendations
docker scout recommendations kasa-monitor:latest

# Check for specific CVE
docker scout cves kasa-monitor:latest --only-cve CVE-2024-39338
```

### Using Trivy (Alternative)

```bash
# Install Trivy
brew install aquasecurity/trivy/trivy

# Scan image
trivy image kasa-monitor:latest

# Scan Dockerfile
trivy config Dockerfile

# Scan filesystem
trivy fs --security-checks vuln,config .
```

## Common CVEs and Fixes

### Python Dependencies

| Package | CVE | Severity | Fix |
|---------|-----|----------|-----|
| cryptography < 42.0.0 | CVE-2023-49083 | HIGH | Update to >= 45.0.0 |
| pyjwt < 2.8.0 | CVE-2022-29217 | HIGH | Update to >= 2.10.1 |
| fastapi < 0.109.0 | CVE-2024-24762 | MEDIUM | Update to >= 0.115.5 |

### Node Dependencies

| Package | CVE | Severity | Fix |
|---------|-----|----------|-----|
| axios < 1.7.4 | CVE-2024-39338 | HIGH | Update to >= 1.7.9 |
| next < 14.2.10 | CVE-2024-34351 | MEDIUM | Update to >= 14.2.31 |

## Security Best Practices

### 1. Container Security

- ✅ Use specific version tags (not `latest`)
- ✅ Run as non-root user (UID 1001)
- ✅ Use multi-stage builds
- ✅ Minimize installed packages
- ✅ Regular security updates
- ✅ Use dumb-init for signal handling
- ✅ Set read-only filesystem where possible

### 2. Secret Management

```bash
# Never commit secrets
# Use environment variables or Docker secrets

# Docker Secrets (Swarm mode)
echo "my-secret-password" | docker secret create db_password -

# Docker Compose with secrets
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### 3. Network Security

```yaml
# Use custom networks, not default bridge
networks:
  kasa-network:
    driver: bridge
    internal: true  # No external access

# Limit published ports
ports:
  - "127.0.0.1:3000:3000"  # Localhost only
```

### 4. Resource Limits

```yaml
# Prevent resource exhaustion
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## Automated Security Updates

### Dependabot Configuration

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    security-updates-only: true
    
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    security-updates-only: true
    
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
```

### GitHub Security Scanning

Enable in repository settings:
- Dependabot security updates
- Code scanning alerts
- Secret scanning

## Regular Security Audits

### Weekly Tasks
```bash
# Update dependencies
npm audit fix
pip-audit --fix

# Scan Docker images
docker scout cves kasa-monitor:latest
```

### Monthly Tasks
```bash
# Full dependency update
npm update
pip install --upgrade -r requirements.txt

# Rebuild with latest base images
docker build --pull -t kasa-monitor:latest .
```

## Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. Email security details to: [maintainer email]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Checklist for Releases

- [ ] Run `docker scout cves` - no HIGH/CRITICAL
- [ ] Run `npm audit` - no HIGH/CRITICAL
- [ ] Run `pip-audit` - no HIGH/CRITICAL
- [ ] Update base images to latest stable
- [ ] Test with non-root user
- [ ] Verify no secrets in image (`docker history`)
- [ ] Check image size is reasonable
- [ ] Update CHANGELOG with security fixes

## Compliance

This project aims to follow:
- OWASP Docker Security Top 10
- CIS Docker Benchmark
- NIST Cybersecurity Framework

## Additional Resources

- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)