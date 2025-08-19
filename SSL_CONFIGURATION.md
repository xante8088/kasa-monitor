# SSL/HTTPS Configuration Guide

This guide explains how to configure SSL/HTTPS in Kasa Monitor.

## Overview

Kasa Monitor supports SSL/HTTPS with configurable ports for secure communication. The system can automatically detect SSL configuration and start the server with appropriate settings.

## Configuration Methods

### 1. Web Interface Configuration

1. Navigate to **Admin → System Configuration**
2. Enable **SSL/HTTPS** checkbox
3. Configure the following settings:
   - **SSL Certificate**: Path to your certificate file (.crt, .pem, .cer)
   - **Private Key**: Path to your private key file (.key, .pem)
   - **HTTPS Port**: Port for HTTPS connections (default: 5273)
   - **Force HTTPS**: Redirect HTTP traffic to HTTPS (optional)

### 2. Environment Variables (Docker)

For Docker deployments, you can configure HTTPS port using environment variables:

```bash
# Set custom HTTPS port
export HTTPS_PORT=443

# Or in docker-compose.yml
environment:
  - HTTPS_PORT=443
```

### 3. File Upload

The web interface supports uploading SSL certificates and private keys:

1. Generate or obtain SSL certificates
2. Use the file upload buttons in the SSL configuration section
3. Files are automatically stored in the `/ssl` directory

## Certificate Management

### Generate CSR (Certificate Signing Request)

The system includes a built-in CSR generator:

1. Click **Generate CSR** in the SSL configuration section
2. Fill in the required information:
   - Country Code (2 letters)
   - State/Province
   - City/Locality
   - Organization
   - Common Name (your domain)
   - Email Address
   - Key Size (2048, 3072, or 4096 bits)
   - Subject Alternative Names (optional)

3. The system will generate both a private key and CSR file
4. Submit the CSR to a Certificate Authority (CA) to get your certificate

### Self-Signed Certificates

For development or internal use, you can create self-signed certificates:

```bash
# Generate private key
openssl genrsa -out server.key 2048

# Generate self-signed certificate
openssl req -new -x509 -key server.key -out server.crt -days 365 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## Port Configuration

### Default Ports

- **HTTP**: 5272 (when SSL is disabled)
- **HTTPS**: 5273 (when SSL is enabled, configurable)

### Common HTTPS Ports

- **443**: Standard HTTPS port (requires root/admin privileges)
- **8443**: Alternative HTTPS port (commonly used for development)
- **5273**: Default Kasa Monitor HTTPS port

### Docker Port Mapping

```yaml
# docker-compose.yml
services:
  kasa-monitor:
    ports:
      - "443:443"      # Map standard HTTPS port
      - "80:5272"      # Map HTTP port
    environment:
      - HTTPS_PORT=443
```

## Security Considerations

1. **Use strong certificates**: Avoid self-signed certificates in production
2. **Keep certificates updated**: Monitor expiration dates
3. **Secure private keys**: Protect private key files with appropriate permissions
4. **Use strong key sizes**: Minimum 2048 bits, prefer 3072 or 4096 bits
5. **Enable Force HTTPS**: Redirect all HTTP traffic to HTTPS in production

## SSL File Management

The web interface provides tools to manage SSL files:

- **View Files**: See all SSL files with details (size, type, modification date)
- **Download Files**: Download individual files or multiple files as ZIP
- **Delete Files**: Remove unwanted SSL files with confirmation
- **Upload Files**: Upload certificates and private keys

## Troubleshooting

### Common Issues

1. **Certificate not found**: Ensure certificate and key files exist in the correct paths
2. **Permission denied**: Check file permissions for SSL directory and files
3. **Port already in use**: Change HTTPS port or stop conflicting services
4. **Certificate mismatch**: Verify certificate and private key match
5. **Browser warnings**: Install certificate in browser trust store for self-signed certificates

### Server Logs

Check the server logs for SSL-related messages:

```
INFO:__main__:Starting server with SSL enabled on port 5273
INFO:__main__:SSL Certificate: /path/to/certificate.crt
INFO:__main__:SSL Private Key: /path/to/private.key
```

### Testing HTTPS

Test HTTPS connectivity:

```bash
# Test with curl (ignore self-signed certificate warnings)
curl -k https://localhost:5273/api/system/config

# Test certificate validity
openssl s_client -connect localhost:5273 -servername localhost
```

## Examples

### Development Setup

```bash
# Set custom port for development
export HTTPS_PORT=8443

# Start server
python backend/server.py
```

### Production Docker Setup

```yaml
version: '3.8'
services:
  kasa-monitor:
    image: kasa-monitor:latest
    ports:
      - "443:443"
      - "80:5272"
    environment:
      - HTTPS_PORT=443
    volumes:
      - ./ssl:/app/ssl:ro
      - ./data:/app/data
    restart: unless-stopped
```

### Nginx Reverse Proxy

For advanced setups, use Nginx as a reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/certs/server.key;
    
    location / {
        proxy_pass https://kasa-monitor:5273;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Support

For additional help with SSL configuration, check the:
- System logs for error messages
- Web interface SSL configuration section
- Docker documentation for container networking
- OpenSSL documentation for certificate management