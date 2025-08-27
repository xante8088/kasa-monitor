# Troubleshooting Guide

Comprehensive troubleshooting guide for common issues and their solutions in Kasa Monitor v1.2.1.

## Table of Contents

- [SSL Certificate Issues](#ssl-certificate-issues)
- [Authentication & Session Problems](#authentication--session-problems)
- [Data Export Issues](#data-export-issues)
- [Device Persistence Problems](#device-persistence-problems)
- [Time Period Selection Issues](#time-period-selection-issues)
- [Chart Display Problems](#chart-display-problems)
- [Audit Log Display Issues](#audit-log-display-issues)
- [Docker & Container Issues](#docker--container-issues)
- [Performance Problems](#performance-problems)

## SSL Certificate Issues

### Certificate Not Persisting After Docker Restart

**Problem:** SSL certificates disappear after Docker container restart.

**Solution (v1.2.0):**
```yaml
# Ensure SSL volume is properly configured in docker-compose.yml
volumes:
  kasa_ssl:  # Named volume for persistence

services:
  kasa-monitor:
    volumes:
      - kasa_ssl:/app/ssl  # Mount SSL volume
```

**Verification:**
```bash
# Check if volume exists
docker volume ls | grep kasa_ssl

# Verify certificates in container
docker exec kasa-monitor ls -la /app/ssl/

# Check database for saved paths
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "SELECT * FROM ssl_config;"
```

### Cross-Device Link Error

**Problem:** `OSError: [Errno 18] Invalid cross-device link` when uploading certificates.

**Solution:** Fixed in v1.2.0 - The system now uses `shutil.move()` instead of `os.rename()`.

**If still occurring:**
```bash
# Update to latest version
docker pull xante8088/kasa-monitor:latest

# Restart with new image
docker-compose down
docker-compose up -d
```

### Certificate Not Loading on Startup

**Problem:** Certificates exist but aren't automatically loaded.

**Solution:**
```bash
# Check certificate permissions
docker exec kasa-monitor stat /app/ssl/certificate.crt

# Fix permissions if needed
docker exec kasa-monitor chmod 644 /app/ssl/*.crt
docker exec kasa-monitor chmod 600 /app/ssl/*.key

# Verify auto-detection is enabled
docker exec kasa-monitor printenv | grep SSL_ENABLED
```

### SSL Redirect Loop

**Problem:** Browser stuck in redirect loop when SSL is enabled.

**Solution:**
```nginx
# Check reverse proxy configuration
# Ensure X-Forwarded-Proto header is set
proxy_set_header X-Forwarded-Proto $scheme;

# In application, check for header
if request.headers.get('X-Forwarded-Proto') == 'https':
    # Already HTTPS, don't redirect
```

## Authentication & Session Problems

### Token Expired But Not Refreshing

**Problem:** Users getting logged out despite refresh token being valid.

**Solution:**
```javascript
// Check if refresh token exists and is valid
const refreshToken = localStorage.getItem('refresh_token');
if (!refreshToken) {
  console.error('No refresh token found');
  return;
}

// Verify token hasn't expired
const decoded = jwt_decode(refreshToken);
if (decoded.exp * 1000 < Date.now()) {
  console.error('Refresh token expired');
  // Force re-login
  window.location.href = '/login';
}

// Attempt refresh
try {
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  
  if (!response.ok) {
    throw new Error('Refresh failed');
  }
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
} catch (error) {
  console.error('Token refresh failed:', error);
  window.location.href = '/login';
}
```

### Session Warning Not Appearing

**Problem:** Users not receiving session expiration warnings.

**Solution:**
```javascript
// Ensure session warning hook is initialized
import { useSessionWarning } from '@/hooks/use-session-warning';

function App() {
  // Initialize session warning system
  useSessionWarning({
    warningTime: 5 * 60 * 1000,  // 5 minutes before expiry
    checkInterval: 60 * 1000      // Check every minute
  });
  
  return <YourApp />;
}
```

### Multiple Concurrent Sessions Not Working

**Problem:** User gets logged out when logging in from another device.

**Solution:**
```sql
-- Check current session limit
SELECT value FROM system_config WHERE key = 'MAX_CONCURRENT_SESSIONS';

-- View user's active sessions
SELECT * FROM user_sessions 
WHERE user_id = ? AND expires_at > datetime('now');

-- Increase session limit if needed (admin only)
UPDATE system_config 
SET value = '5' 
WHERE key = 'MAX_CONCURRENT_SESSIONS';
```

### Invalid Authentication Response Format

**Problem:** Frontend not handling new structured error responses.

**Solution:**
```javascript
// Update error handler for new format
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      const errorData = error.response.data;
      
      // Handle new structured format
      if (errorData.error_code) {
        switch (errorData.error_code) {
          case 'TOKEN_EXPIRED':
            // Attempt token refresh
            return refreshTokenAndRetry(error.config);
          case 'INVALID_TOKEN':
          case 'USER_INACTIVE':
            // Force re-login
            window.location.href = errorData.redirect_to || '/login';
            break;
        }
      } else {
        // Handle legacy format
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

## Data Export Issues

### Export Permission Denied

**Problem:** User receives "Permission denied" when trying to export data.

**Solution:**
```sql
-- Check user permissions
SELECT p.* FROM user_permissions up
JOIN permissions p ON up.permission_id = p.id
WHERE up.user_id = ? AND p.name = 'DATA_EXPORT';

-- Grant export permission (admin only)
INSERT INTO user_permissions (user_id, permission_id)
SELECT ?, id FROM permissions WHERE name = 'DATA_EXPORT';
```

### Export Rate Limit Exceeded

**Problem:** User gets "Rate limit exceeded" error.

**Solution:**
```python
# Current limit: 10 exports per hour

# Check user's recent exports
SELECT COUNT(*) FROM data_exports 
WHERE user_id = ? 
AND created_at > datetime('now', '-1 hour');

# Wait for rate limit reset
# Rate limit uses rolling window, so wait 1 hour from oldest export
```

**Frontend handling:**
```javascript
if (error.response?.status === 429) {
  const retryAfter = error.response.headers['retry-after'];
  showNotification({
    type: 'warning',
    message: `Export limit reached. Try again in ${retryAfter} seconds.`,
    duration: 10000
  });
}
```

### Cannot Access Other User's Exports

**Problem:** Admin cannot view other users' exports.

**Solution:**
```python
# Verify admin role
SELECT role FROM users WHERE id = ?;

# Admin users should have access to all exports
# Check if the endpoint is correctly checking admin status:
if user.role.value != "admin" and export.get("user_id") != user.id:
    raise HTTPException(403, "Access denied")
```

### Export Files Not Being Cleaned Up

**Problem:** Old export files accumulating in storage.

**Solution:**
```bash
# Check retention scheduler status
docker exec kasa-monitor ps aux | grep retention

# Manually trigger cleanup
docker exec kasa-monitor python3 -c "
from export_retention_service import ExportRetentionService
service = ExportRetentionService()
service.cleanup_expired_exports()
"

# Verify cleanup schedule in cron
docker exec kasa-monitor crontab -l | grep export_cleanup
```

## Device Persistence Problems

### Devices Disappearing After Docker Update

**Problem:** Discovered devices lost after updating Docker container.

**Solution (Fixed in v1.2.0):**
```yaml
# Ensure data volume is properly mounted
volumes:
  kasa_data:  # Named volume for persistence

services:
  kasa-monitor:
    volumes:
      - kasa_data:/app/data  # Mount data volume
```

**Recovery steps:**
```bash
# Check if devices exist in database
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db \
  "SELECT * FROM devices;"

# Re-run device discovery
curl -X POST http://localhost:5272/api/devices/discover \
  -H "Authorization: Bearer ${TOKEN}"
```

### Database Table Name Mismatch

**Problem:** Error: "no such table: device_configurations"

**Solution:** Fixed in v1.2.0 - Table names corrected to "devices".

**Migration for existing installations:**
```sql
-- Check existing tables
.tables

-- If old table exists, migrate data
ALTER TABLE device_configurations RENAME TO devices;

-- Update any views or triggers
DROP VIEW IF EXISTS device_status_view;
CREATE VIEW device_status_view AS SELECT * FROM devices;
```

## Time Period Selection Issues

### Time Period Not Updating Charts

**Problem:** Selecting a different time period doesn't update the chart data.

**Solution:**
```javascript
// Check if the component is properly receiving period updates
useEffect(() => {
  console.log('Period changed:', selectedPeriod);
  fetchData(selectedPeriod);
}, [selectedPeriod]);

// Ensure API call includes the period parameter
const fetchData = async (period) => {
  const response = await fetch(
    `/api/device/${deviceIp}/history?period=${period}&aggregation=auto`
  );
  // ...
};
```

### Custom Date Range Not Working

**Problem:** Custom date range picker doesn't function correctly.

**Solution:**
```javascript
// Verify date format is correct
const formatDate = (date) => {
  return date.toISOString().split('T')[0]; // YYYY-MM-DD format
};

// Check browser compatibility
if (!window.DateTimeFormat) {
  console.warn('Browser does not support DateTimeFormat');
  // Use fallback date picker
}
```

### Chart Memory Leak with Rapid Period Changes

**Problem:** Memory usage increases when rapidly switching between time periods.

**Solution:**
```javascript
// Proper cleanup in React component
useEffect(() => {
  let isMounted = true;
  const controller = new AbortController();
  
  const fetchData = async () => {
    try {
      const response = await fetch(url, {
        signal: controller.signal
      });
      if (isMounted) {
        setData(await response.json());
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error(error);
      }
    }
  };
  
  fetchData();
  
  return () => {
    isMounted = false;
    controller.abort();
    // Clean up chart instance
    if (chartRef.current) {
      chartRef.current.destroy();
    }
  };
}, [period]);
```

## Chart Display Problems

### Charts Not Loading After Update

**Problem:** Charts show loading spinner indefinitely after v1.2.1 update.

**Solution:**
```bash
# Clear browser cache
# Chrome/Edge: Ctrl+Shift+R or Cmd+Shift+R
# Firefox: Ctrl+F5 or Cmd+Shift+R
# Safari: Cmd+Option+R

# Clear application cache
localStorage.clear();
sessionStorage.clear();

# Force reload
location.reload(true);
```

### Incorrect Data Aggregation

**Problem:** Chart shows incorrect aggregation for selected time period.

**Solution:**
```sql
-- Check aggregation settings in database
SELECT * FROM system_config WHERE key LIKE 'aggregation%';

-- Verify data points exist for the period
SELECT COUNT(*), 
       MIN(timestamp) as earliest,
       MAX(timestamp) as latest
FROM readings 
WHERE device_ip = '192.168.1.100'
  AND timestamp > datetime('now', '-7 days');
```

### Chart Performance Issues

**Problem:** Charts lag or freeze with large datasets.

**Solution:**
```javascript
// Enable performance optimizations
const chartOptions = {
  animation: {
    duration: 0  // Disable animations for better performance
  },
  parsing: false,  // Pre-parse data
  normalized: true, // Data is already normalized
  spanGaps: true,  // Handle missing data points
  datasets: {
    line: {
      pointRadius: 0,  // Hide points for better performance
      borderWidth: 1   // Thinner lines
    }
  }
};

// Limit data points
const maxDataPoints = 1000;
if (data.length > maxDataPoints) {
  // Implement data decimation
  data = decimateData(data, maxDataPoints);
}
```

## Audit Log Display Issues

### Audit Log Modal Shows Grey Overlay

**Problem:** Audit log details modal has grey overlay blocking interaction.

**Solution (Fixed in v1.2.0):**
```css
/* Fixed CSS - grey overlay removed */
.modal-backdrop {
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1040;
}

.modal {
  z-index: 1050;  /* Modal above backdrop */
}
```

**If still occurring:**
```javascript
// Clear any stuck modals
document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());

// Ensure proper modal cleanup
$('#auditModal').on('hidden.bs.modal', function () {
  $('.modal-backdrop').remove();
  $('body').removeClass('modal-open');
});
```

### Audit Logs Not Recording Events

**Problem:** Events not appearing in audit log.

**Solution:**
```python
# Check audit logging is enabled
SELECT value FROM system_config WHERE key = 'AUDIT_LOGGING_ENABLED';

# Verify audit log directory exists and is writable
ls -la /app/logs/audit/

# Check for errors in audit service
tail -f /app/logs/error.log | grep audit
```

## Docker & Container Issues

### Container Fails Health Check

**Problem:** Docker container marked as unhealthy.

**Solution:**
```bash
# Check health check logs
docker inspect kasa-monitor | grep -A 10 Health

# View health check command output
docker exec kasa-monitor curl -f http://localhost:3000/health

# Common issues:
# - Port mismatch (should be 3000, not 8000)
# - Service not started yet (increase start_period)
# - Database not initialized
```

### Volume Permission Issues

**Problem:** Permission denied errors when accessing volumes.

**Solution:**
```bash
# Check volume ownership
docker exec kasa-monitor ls -la /app/data /app/ssl

# Fix ownership
docker exec kasa-monitor chown -R app:app /app/data /app/ssl

# For host-mounted volumes
sudo chown -R 1000:1000 ./data ./ssl
```

## Performance Problems

### Slow Export Generation

**Problem:** Large exports taking too long or timing out.

**Solution:**
```python
# Optimize export query
# Use pagination for large datasets
CHUNK_SIZE = 10000

# Enable background processing
EXPORT_BACKGROUND_ENABLED = True

# Increase timeout
EXPORT_TIMEOUT_SECONDS = 300  # 5 minutes
```

### High Memory Usage

**Problem:** Container using excessive memory.

**Solution:**
```yaml
# Set memory limits in docker-compose.yml
services:
  kasa-monitor:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

```javascript
// For frontend (Node.js)
NODE_OPTIONS=--max-old-space-size=1024
```

### Database Lock Errors

**Problem:** "database is locked" errors during concurrent operations.

**Solution:**
```python
# Increase SQLite timeout
DATABASE_TIMEOUT = 30  # seconds

# Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=30000;

# Consider connection pooling
DATABASE_POOL_SIZE = 5
DATABASE_MAX_OVERFLOW = 10
```

## Getting Help

### Diagnostic Commands

```bash
# System status
docker exec kasa-monitor python3 -c "
from server import app
print(app.get_system_status())
"

# Database integrity check
docker exec kasa-monitor sqlite3 /app/data/kasa_monitor.db "PRAGMA integrity_check;"

# View recent errors
docker logs kasa-monitor --tail 100 | grep ERROR

# Check disk space
docker exec kasa-monitor df -h /app/data /app/ssl

# Service status
docker exec kasa-monitor ps aux
```

### Log Locations

- **Application logs:** `/app/logs/app.log`
- **Audit logs:** `/app/logs/audit/audit_YYYYMMDD.log`
- **Error logs:** `/app/logs/error.log`
- **Access logs:** `/app/logs/access.log`

### Support Resources

- **Documentation:** [Wiki Home](Home)
- **Issues:** [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)
- **Discussions:** [GitHub Discussions](https://github.com/xante8088/kasa-monitor/discussions)

---

**Document Version:** 1.1.0  
**Last Updated:** 2025-08-27  
**Review Status:** Current  
**Change Summary:** Updated for v1.2.1 with new sections for time period selection and chart display issues