# Reverse Proxy Setup Guide

This guide explains how to set up and use the nginx reverse proxy for secure HTTPS access to your Kasa Monitor frontend.

## Overview

The reverse proxy setup provides:
- **HTTPS Frontend Access** with SSL termination
- **Enhanced Security** with rate limiting and security headers
- **HTTP to HTTPS Redirection** for all traffic
- **Separate Admin Interface** for administrative tasks
- **Production-Ready Configuration** with caching and compression

## Current Configuration

### Ports
- **HTTP (Redirect)**: `8090` → Redirects to HTTPS
- **HTTPS (Main)**: `8445` → Main web interface
- **Admin HTTPS**: `8446` → Dedicated admin interface

### SSL Certificate
- **Certificate**: `ssl/tacocat_serveirc_com.crt`
- **Private Key**: `ssl/tacocat.serveirc.com_20250819_124010.key`
- **Domain**: `tacocat.serveirc.com`

## How to Access

### Main Interface (HTTPS)
```
https://localhost:8445
```
- Full web interface with HTTPS security
- All frontend features available
- SSL certificate validation

### Admin Interface (HTTPS)
```
https://localhost:8446/admin
```
- Dedicated admin access
- Direct backend API connection
- Enhanced security settings

### HTTP (Auto-Redirect)
```
http://localhost:8090
```
- Automatically redirects to HTTPS port 8445
- No direct HTTP access (security feature)

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│   Browser       │    │   Nginx Proxy   │    │   Application    │
│   (Port 8445)   │───▶│   (SSL Term)    │───▶│   Backend+       │
└─────────────────┘    └─────────────────┘    │   Frontend       │
                                              └──────────────────┘
                                              
Frontend (Next.js):     localhost:3000
Backend HTTP:           localhost:5272
Backend HTTPS:          localhost:8443
```

## Security Features

### SSL/TLS
- **TLS 1.2+ Only** - Deprecated protocols blocked
- **Strong Cipher Suites** - Modern encryption standards
- **HSTS Headers** - Prevent downgrade attacks
- **Certificate Validation** - Valid CA-signed certificates

### Security Headers
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-XSS-Protection` - Cross-site scripting protection
- `Strict-Transport-Security` - Forces HTTPS connections

### Rate Limiting
- **API Endpoints**: 10 requests/second per IP
- **Login Endpoints**: 5 requests/minute per IP (brute force protection)
- **Burst Tolerance**: Temporary spikes allowed

## Configuration Files

### Main Configuration
- **Location**: `/Users/ryan.hein/kasaweb/kasa-monitor/nginx.conf`
- **Type**: Production-ready nginx configuration
- **Features**: SSL, rate limiting, security headers, compression

### Docker Compose
- **Location**: `/Users/ryan.hein/kasaweb/kasa-monitor/docker-compose.proxy.yml`
- **Type**: Container orchestration with nginx proxy
- **Includes**: Nginx, backend, frontend containers

## Management

### Starting the Proxy
```bash
# Start nginx with custom configuration
nginx -c /Users/ryan.hein/kasaweb/kasa-monitor/nginx.conf

# Or use Docker Compose
docker-compose -f docker-compose.proxy.yml up -d
```

### Stopping the Proxy
```bash
# Stop nginx
nginx -s stop

# Or stop Docker containers
docker-compose -f docker-compose.proxy.yml down
```

### Checking Status
```bash
# Check if nginx is running
ps aux | grep nginx

# Check port usage
netstat -an | grep LISTEN | grep -E "(8090|8445|8446)"

# Test HTTPS connectivity
curl -k https://localhost:8445
```

### Configuration Testing
```bash
# Test nginx configuration syntax
nginx -t -c /Users/ryan.hein/kasaweb/kasa-monitor/nginx.conf
```

## System Integration

The reverse proxy configuration can be managed through the **System Configuration** page:

1. Navigate to **Admin → System Configuration**
2. Scroll to **Reverse Proxy Configuration** section
3. Enable the reverse proxy
4. Configure ports and server name
5. Save configuration

### Web Interface Features
- **Port Configuration** - Customize HTTP/HTTPS ports
- **Server Name Setup** - Match your SSL certificate domain
- **Force HTTPS Toggle** - Enable/disable HTTP redirects
- **Status Monitoring** - Check if proxy is running
- **Quick Access Links** - Direct links to HTTPS interfaces

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :8445
   
   # Change ports in nginx.conf or kill conflicting process
   ```

2. **SSL Certificate Errors**
   - Verify certificate files exist and are readable
   - Check certificate validity: `openssl x509 -in cert.crt -text -noout`
   - Ensure server name matches certificate domain

3. **Permission Denied**
   - For ports < 1024, nginx needs root privileges
   - Use non-privileged ports (1024+) for development

4. **Backend Connection Failed**
   - Verify backend is running on expected ports
   - Check firewall settings
   - Test direct backend connectivity

### Log Files
- **Access Log**: `/opt/homebrew/var/log/nginx/access.log`
- **Error Log**: `/opt/homebrew/var/log/nginx/error.log`
- **Backend Logs**: Check terminal output from backend server

### Testing Connectivity
```bash
# Test HTTPS main interface
curl -k -I https://localhost:8445

# Test HTTPS admin interface  
curl -k -I https://localhost:8446/admin

# Test HTTP redirect
curl -I http://localhost:8090

# Test API through proxy
curl -k https://localhost:8445/api/auth/setup-required
```

## Production Deployment

### DNS Configuration
1. Point your domain to the server IP
2. Update `server_name` in nginx.conf to your domain
3. Obtain proper SSL certificates for your domain
4. Use standard ports (80/443) with proper permissions

### SSL Certificates
For production, consider:
- **Let's Encrypt** - Free automated certificates
- **Commercial CA** - Extended validation certificates
- **Internal CA** - For corporate environments

### Security Hardening
- Enable fail2ban for brute force protection
- Configure firewall rules
- Regular security updates
- Monitor access logs for suspicious activity

## Support

For issues with the reverse proxy setup:
1. Check the configuration files for syntax errors
2. Review log files for error messages
3. Test individual components (nginx, backend, frontend)
4. Verify SSL certificate validity and paths
5. Check port availability and permissions

The reverse proxy provides enterprise-grade security and performance for your Kasa Monitor deployment.