# Release Notes - v1.2.0

**Release Date:** August 26, 2025  
**Status:** Current Release  
**Type:** Major Security & Feature Update

## Executive Summary

Kasa Monitor v1.2.0 delivers critical security enhancements, improved user experience, and robust data management features. This release addresses all identified security vulnerabilities, implements comprehensive compliance features, and significantly enhances the authentication and data export systems.

## 🔒 Security Enhancements

### Critical Security Fixes

#### **Data Export Security**
- **Permission Enforcement:** All export endpoints now require `DATA_EXPORT` permission
- **User Ownership Validation:** Users can only access their own exports (admin override available)
- **Rate Limiting:** 10 exports per hour per user to prevent abuse
- **Audit Logging:** Comprehensive logging for GDPR/SOX compliance
- **Status:** ✅ RESOLVED - Previously CRITICAL vulnerability

#### **Authentication System Improvements**
- **Token Refresh Mechanism:** Seamless session renewal without re-authentication
- **Structured Error Responses:** Clear, actionable authentication errors
- **Session Management:** Track and control user sessions with limits
- **Global Exception Handler:** Consistent error handling across all endpoints
- **Session Warnings:** Proactive notifications before session expiration

#### **SSL Certificate Persistence**
- **Docker Volume Support:** Certificates persist across container restarts
- **Cross-Device Link Fix:** Resolved filesystem compatibility issues
- **Auto-Detection:** Automatically loads certificates on startup
- **Database Path Storage:** Certificate configurations saved for persistence

## 🚀 New Features

### Enhanced Data Export System

**UI Integration:**
- DataExportModal component integrated into main interface
- Device-specific export functionality from device cards
- Permission-based UI elements (export buttons hidden for unauthorized users)

**Backend Enhancements:**
- User ownership tracking in database
- Automated retention policies with configurable cleanup
- Export history filtered by user ownership
- Comprehensive audit trail for all operations

**API Improvements:**
```http
POST /api/exports/create
# Now requires DATA_EXPORT permission
# Validates user ownership
# Implements rate limiting
# Creates audit log entry
```

### Authentication & Session Management

**New Endpoints:**
```http
POST /api/auth/refresh          # Token refresh
GET /api/auth/sessions          # List active sessions
DELETE /api/auth/sessions/{id}  # Terminate specific session
GET /api/auth/security-status   # Security configuration status
```

**Token Configuration:**
- Access tokens: 30-minute expiration
- Refresh tokens: 7-day expiration
- Automatic refresh 5 minutes before expiry
- Secure token rotation on refresh

**Session Features:**
- Maximum 3 concurrent sessions per user
- 30-minute inactivity timeout
- Session fingerprinting (IP + User Agent)
- Session warning system with extension capability

### SSL/TLS Improvements

**Persistent Storage:**
```yaml
volumes:
  kasa_ssl:  # Named volume for SSL persistence
```

**Configuration Management:**
- UI-based certificate upload
- Automatic certificate validation
- Certificate expiration monitoring
- Support for Let's Encrypt and commercial certificates

## 🐛 Bug Fixes

### Device Persistence
- **Fixed:** Devices disappearing after Docker container updates
- **Cause:** Database table name mismatch (`device_configurations` vs `devices`)
- **Solution:** Corrected table references and added migration support

### Audit Log Modal
- **Fixed:** Grey overlay preventing interaction with audit log details
- **Cause:** Incorrect z-index and modal backdrop handling
- **Solution:** Proper modal layering and cleanup on close

### SSL Certificate Upload
- **Fixed:** Cross-device link error in Docker environments
- **Cause:** `os.rename()` fails across filesystem boundaries
- **Solution:** Using `shutil.move()` for atomic operations

### Token Expiration Handling
- **Fixed:** Inconsistent 401 responses causing frontend issues
- **Cause:** Mix of string and object error responses
- **Solution:** Standardized structured JSON error format

## 📊 Compliance & Audit

### GDPR Compliance (Article 30)
- ✅ Complete audit trail of data processing activities
- ✅ User consent tracking and management
- ✅ Data portability through secure exports
- ✅ Right to deletion with audit trail
- ✅ Retention policies with automatic cleanup

### SOX Compliance (Section 404)
- ✅ Tamper-evident audit logging with checksums
- ✅ Complete user identity tracking
- ✅ Access control with permission validation
- ✅ Change management documentation
- ✅ Segregation of duties through RBAC

### Audit Events Tracked
| Event Type | Description | Severity |
|------------|-------------|----------|
| DATA_EXPORT | Export creation | INFO |
| DATA_EXPORTED | Export completion | INFO |
| EXPORT_DOWNLOADED | File download | INFO |
| DATA_DELETED | Export deletion | INFO |
| PERMISSION_DENIED | Unauthorized access | WARNING |
| RATE_LIMIT_EXCEEDED | Export limit hit | WARNING |
| TOKEN_REFRESH | Session renewal | INFO |
| SESSION_EXPIRED | Session timeout | INFO |

## 💔 Breaking Changes

### API Changes
1. **Export Endpoints:** Now require `DATA_EXPORT` permission
2. **Error Responses:** Changed from strings to structured JSON objects
3. **Session Management:** New session limits may affect existing integrations

### Configuration Changes
1. **JWT_SECRET_KEY:** Now required in production environments
2. **SSL Volumes:** Must add `kasa_ssl` volume to docker-compose.yml
3. **Database Schema:** New columns added (requires migration)

## 📦 Migration Guide

### From v1.1.x to v1.2.0

#### 1. Update Docker Compose
```yaml
# Add SSL volume
volumes:
  kasa_data:
  kasa_ssl:  # New SSL volume

services:
  kasa-monitor:
    volumes:
      - kasa_ssl:/app/ssl  # Mount SSL volume
```

#### 2. Set Required Environment Variables
```bash
# Generate JWT secret
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env

# Update docker-compose.yml
environment:
  - JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

#### 3. Run Database Migration
```bash
# Apply schema updates
docker exec kasa-monitor python3 migrate_exports_table.py
```

#### 4. Update Frontend Integration
```javascript
// Handle new error format
if (error.response?.status === 401) {
  const { error_code, redirect_to } = error.response.data;
  if (redirect_to) {
    window.location.href = redirect_to;
  }
}

// Implement token refresh
async function refreshSession() {
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token })
  });
  // Update stored tokens
}
```

#### 5. Grant Export Permissions
```sql
-- Grant DATA_EXPORT permission to existing users
INSERT INTO user_permissions (user_id, permission_id)
SELECT u.id, p.id FROM users u, permissions p 
WHERE p.name = 'DATA_EXPORT' AND u.role IN ('admin', 'operator');
```

## 🎯 Performance Improvements

- **Export Processing:** Chunked processing for large datasets
- **Session Management:** Efficient concurrent session tracking
- **SSL Operations:** Optimized certificate validation and loading
- **Database Operations:** Fixed table references reducing query overhead

## 📋 Testing

### Test Coverage
- ✅ Authentication system: 95% coverage
- ✅ Export security: 92% coverage
- ✅ Session management: 88% coverage
- ✅ SSL persistence: 90% coverage
- ✅ Audit logging: 94% coverage

### Test Files
- `test_auth_improvements.py` - Authentication tests
- `test_export_security.py` - Export permission tests
- `verify_export_security.py` - Security validation
- `test_export_retention.py` - Retention policy tests

## 🔮 Future Roadmap

### Planned for v1.3.0
- Two-factor authentication (2FA)
- Advanced rate limiting per endpoint
- Export scheduling and automation
- Enhanced plugin security
- WebSocket security improvements

### Under Consideration
- OAuth2/OIDC integration
- Kubernetes deployment support
- Multi-tenancy support
- Advanced analytics dashboard
- Mobile application

## 📚 Documentation Updates

### New Documentation
- [SSL Configuration Guide](SSL-Configuration-Guide)
- [Authentication & Session Management](Authentication-Session-Management)
- [Troubleshooting Guide](Troubleshooting-Guide)
- [Release Notes v1.2.0](Release-Notes-v1.2.0)

### Updated Documentation
- [Home](Home) - Added v1.2.0 feature highlights
- [Security Guide](Security-Guide) - Enhanced with new security features
- [Data Export System](Data-Export-System) - Updated with security details
- [Installation](Installation) - Added new configuration options

## 🙏 Acknowledgments

Thank you to all contributors and users who reported issues and provided feedback for this release.

## 📞 Support

### Getting Help
- **Documentation:** [Wiki Home](Home)
- **Issues:** [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)
- **Discussions:** [GitHub Discussions](https://github.com/xante8088/kasa-monitor/discussions)

### Reporting Security Issues
Please report security vulnerabilities privately to security@[project-domain]

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-26  
**Review Status:** Current  
**Release Manager:** Development Team