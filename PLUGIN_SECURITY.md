# Plugin Security and Signing System

This document describes the comprehensive plugin security system implemented in Kasa Monitor, including cryptographic signing, verification, and security policies.

## Overview

The plugin security system ensures that plugins are authentic, unmodified, and come from trusted sources. It uses RSA digital signatures with configurable trust levels and security policies.

## Security Architecture

### Trust Levels

The system recognizes five trust levels for plugins:

1. **OFFICIAL** - Signed by official Kasa Monitor keys (highest trust)
2. **VERIFIED** - Signed by verified developers 
3. **COMMUNITY** - Signed by community members
4. **UNSIGNED** - No signature (configurable whether allowed)
5. **INVALID** - Invalid or tampered signature (always rejected)

### Signature Algorithm

- **Primary**: RSA-PSS with SHA-256 (recommended)
- **Fallback**: RSA-PKCS1v15 with SHA-256
- **Key Size**: 2048, 3072, or 4096 bits (2048 minimum)

## Plugin Signing CLI Tool

### Installation and Setup

The plugin signing tool is located at `tools/plugin_signer.py` and provides comprehensive signing capabilities.

### Basic Usage

#### Generate Key Pair
```bash
python tools/plugin_signer.py generate-keys --name my_company
```

This creates:
- `my_company_private.pem` (keep secure!)
- `my_company_public.pem` (share with users)

#### Sign a Plugin
```bash
python tools/plugin_signer.py sign plugin.zip \
  --key my_company_private.pem \
  --signer "My Company" \
  --organization "My Organization" \
  --output plugin_signed.zip
```

#### Verify a Plugin
```bash
python tools/plugin_signer.py verify plugin_signed.zip
```

#### Get Plugin Information
```bash
python tools/plugin_signer.py info plugin_signed.zip
```

### Advanced Options

#### Custom Key Size
```bash
python tools/plugin_signer.py generate-keys --name secure_dev --key-size 4096
```

#### Rich Metadata
```bash
python tools/plugin_signer.py sign plugin.zip \
  --key private.pem \
  --signer "John Doe" \
  --contact "john@example.com" \
  --organization "ACME Corp" \
  --description "Production release v1.2.3"
```

#### Trusted Keys Directory
```bash
python tools/plugin_signer.py verify plugin.zip --trusted-keys-dir ./custom/keys
```

## Security Configuration

### Security Policies

The system supports configurable security policies:

```json
{
  "require_signature": false,
  "minimum_trust_level": "unsigned",
  "allow_unsigned": true,
  "verify_on_load": true,
  "quarantine_invalid": true
}
```

#### Policy Options

- **require_signature**: Reject all unsigned plugins
- **minimum_trust_level**: Minimum trust level required ("official", "verified", "community", "unsigned")
- **allow_unsigned**: Whether to allow unsigned plugins
- **verify_on_load**: Verify signatures when loading plugins
- **quarantine_invalid**: Quarantine plugins with invalid signatures

### API Endpoints

#### Get Security Policies
```bash
GET /api/plugins/security/policies
```

#### Update Security Policies
```bash
POST /api/plugins/security/policies
Content-Type: application/json

{
  "require_signature": true,
  "minimum_trust_level": "community"
}
```

#### Verify Plugin Without Installing
```bash
POST /api/plugins/security/verify
Content-Type: multipart/form-data

file=@plugin.zip
```

#### List Trusted Keys
```bash
GET /api/plugins/security/trusted-keys
```

#### Add Trusted Key
```bash
POST /api/plugins/security/trusted-keys
Content-Type: application/json

{
  "name": "verified_developer",
  "public_key": "-----BEGIN PUBLIC KEY-----\n..."
}
```

## Trust Management

### Key Naming Convention

The trust level is determined by the key filename:

- `official_*` → OFFICIAL trust level
- `verified_*` → VERIFIED trust level  
- `*` → COMMUNITY trust level

Examples:
- `official_kasa_monitor.pem` → Official
- `verified_john_doe.pem` → Verified
- `community_contributor.pem` → Community

### Adding Trusted Keys

#### Manual Method
1. Copy public key to `keys/trusted/` directory
2. Name according to trust level convention
3. Restart server or reload trusted keys

#### API Method
```bash
curl -X POST http://localhost:5272/api/plugins/security/trusted-keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "verified_developer",
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
  }'
```

## Plugin Upload Security

### Automatic Verification

When uploading plugins via `/api/plugins/install/upload`, the system:

1. **Extracts** signature files (SIGNATURE.json, SIGNATURE.sig)
2. **Verifies** signature against trusted keys
3. **Checks** security policies
4. **Validates** trust level requirements
5. **Reports** security status in response

### Response Format

Successful upload with security info:
```json
{
  "message": "Plugin uploaded and installation started",
  "security": {
    "trust_level": "verified",
    "verified": true,
    "warnings": []
  }
}
```

Failed upload due to security:
```json
{
  "error": "Plugin security check failed",
  "security_result": {
    "allowed": false,
    "trust_level": "invalid",
    "verification": {
      "verified": false,
      "errors": ["Signature verification failed"]
    }
  }
}
```

### Bypass Option

For development or emergency purposes:
```bash
curl -X POST -F "file=@plugin.zip" -F "skip_signature_check=true" \
  http://localhost:5272/api/plugins/install/upload
```

## Signature Format

### Plugin Structure

A signed plugin contains:
```
plugin_signed.zip
├── manifest.json          # Plugin manifest
├── main.py               # Plugin code
├── README.md             # Documentation
├── SIGNATURE.json        # Signature metadata
└── SIGNATURE.sig         # Base64-encoded signature
```

### SIGNATURE.json Format

```json
{
  "version": "1.0",
  "algorithm": "RSA-PSS-SHA256",
  "timestamp": "2025-08-19T20:27:50.719040+00:00",
  "plugin_hash": "sha256:abc123...",
  "signer": "Developer Name",
  "metadata": {
    "organization": "Company Name",
    "contact": "dev@example.com"
  }
}
```

## Security Best Practices

### For Plugin Developers

1. **Secure Key Storage**
   - Store private keys securely (encrypted storage)
   - Never commit private keys to version control
   - Use strong passphrases for key encryption

2. **Key Management**
   - Rotate keys periodically
   - Use separate keys for different trust levels
   - Maintain key backup and recovery procedures

3. **Signing Process**
   - Always verify plugin functionality before signing
   - Include meaningful metadata in signatures
   - Use consistent naming conventions

### For System Administrators

1. **Trust Policy Configuration**
   - Set appropriate minimum trust levels
   - Regularly review trusted keys
   - Monitor security events and logs

2. **Key Distribution**
   - Verify public key authenticity before adding
   - Use secure channels for key distribution
   - Maintain audit logs of key additions

3. **Security Monitoring**
   - Monitor plugin installation attempts
   - Review signature verification failures
   - Track trust level distributions

## Production Deployment

### Recommended Settings

For production environments:
```json
{
  "require_signature": true,
  "minimum_trust_level": "verified",
  "allow_unsigned": false,
  "verify_on_load": true,
  "quarantine_invalid": true
}
```

### Key Distribution

1. **Official Keys**: Distributed with application releases
2. **Verified Developer Keys**: Obtained through verification process
3. **Community Keys**: Added by administrators after review

### Monitoring and Alerting

Set up monitoring for:
- Failed signature verifications
- Unsigned plugin installation attempts
- Invalid signature detections
- Trust policy violations

## Troubleshooting

### Common Issues

#### "Signature verification failed"
- Check that the correct public key is in `keys/trusted/`
- Verify key naming follows trust level convention
- Ensure signature was created with matching private key

#### "Plugin trust level below minimum"
- Check current security policies
- Verify plugin signer's trust level
- Consider updating trust policies if appropriate

#### "No signature found"
- Plugin was not signed
- Enable `allow_unsigned` policy if intentional
- Sign the plugin using the CLI tool

#### "Invalid signature format"
- Signature files may be corrupted
- Re-sign the plugin with current tools
- Check for ZIP file corruption

### Debug Commands

```bash
# List trusted keys
python tools/plugin_signer.py list-keys

# Detailed verification
python tools/plugin_signer.py verify plugin.zip --verbose

# Check signature without verification
python tools/plugin_signer.py info plugin.zip
```

## API Reference

### Security Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plugins/security/policies` | GET | Get current security policies |
| `/api/plugins/security/policies` | POST | Update security policies |
| `/api/plugins/security/verify` | POST | Verify plugin without installing |
| `/api/plugins/security/trusted-keys` | GET | List trusted keys |
| `/api/plugins/security/trusted-keys` | POST | Add trusted key |

### Upload Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | File | Plugin ZIP file |
| `skip_signature_check` | Boolean | Bypass signature verification |
| `enable_after_install` | Boolean | Enable plugin after installation |

## Support

For security-related issues:
1. Check this documentation
2. Review server logs for detailed error messages
3. Test with the CLI verification tool
4. Verify trust configuration and policies

The plugin security system provides enterprise-grade protection while maintaining flexibility for development and testing scenarios.