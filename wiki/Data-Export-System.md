# Data Export System

Comprehensive data export and analysis system for Kasa Monitor device and energy data.

## Overview

The Data Export System provides powerful, secure tools for exporting, analyzing, and sharing your energy monitoring data. Export device readings, cost analysis, and system reports in multiple formats for external analysis, compliance reporting, or data backup.

**Security Enhancements (v1.2.0):**
- Permission-based access control (DATA_EXPORT permission required)
- User ownership validation (users can only access their own exports)
- Comprehensive audit logging for GDPR/SOX compliance
- Rate limiting (10 exports per hour per user)
- Automated retention policies and cleanup

```
┌─────────────────────────────────────┐
│         Data Export System         │
├─────────────────────────────────────┤
│  1. Device Data Export              │
│  2. Energy Analysis Reports         │
│  3. Cost Analysis Export            │
│  4. Custom Report Generation        │
│  5. Scheduled Export Jobs           │
└─────────────────────────────────────┘
```

## Features

### ✅ **Available Export Types**
- **Device Readings** - Power, energy, voltage data
- **Cost Analysis** - Energy costs and rate calculations
- **System Reports** - Device status, health metrics
- **Audit Logs** - Security and activity logs
- **Configuration Data** - Device and user settings

### ✅ **Supported Formats**
- **CSV** - Spreadsheet compatible
- **JSON** - API integration friendly
- **Excel** - Advanced spreadsheet analysis
- **PDF** - Professional reports

## Quick Start

### Export Device Data

```http
POST /api/exports/create
Authorization: Bearer {token}
Content-Type: application/json

{
  "export_type": "device_data",
  "format": "csv",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "devices": ["192.168.1.100", "192.168.1.101"],
  "fields": ["timestamp", "power_w", "energy_kwh", "cost"]
}
```

### Download Export

```http
GET /api/exports/download/{export_id}
Authorization: Bearer {token}
```

## Security & Permissions

### Required Permissions

All export endpoints require the `DATA_EXPORT` permission:

```http
Authorization: Bearer {token_with_data_export_permission}
```

### User Ownership

- **Regular Users:** Can only view and download their own exports
- **Admin Users:** Can access all exports across the system
- **Ownership Validation:** Automatic 403 Forbidden for unauthorized access attempts

### Rate Limiting

- **Limit:** 10 exports per hour per user
- **Response:** HTTP 429 when limit exceeded
- **Reset:** Rolling hour window

### Audit Logging

All export operations are logged for compliance:

| Operation | Event Type | Severity | Details Logged |
|-----------|-----------|----------|----------------|
| Export Created | DATA_EXPORT | INFO | Devices, date range, format, user |
| Export Downloaded | DATA_EXPORTED | INFO | Filename, size, format, user |
| Export Deleted | DATA_DELETED | INFO | Export ID, filename, user |
| Permission Denied | PERMISSION_DENIED | WARNING | User ID, attempted export |
| Rate Limit Exceeded | RATE_LIMIT_EXCEEDED | WARNING | User ID, export count |

## API Endpoints

### List Available Formats

```http
GET /api/exports/formats
```

**Response:**
```json
{
  "formats": [
    {
      "id": "csv",
      "name": "CSV",
      "description": "Comma-separated values",
      "mime_type": "text/csv",
      "extension": ".csv"
    },
    {
      "id": "json",
      "name": "JSON",
      "description": "JavaScript Object Notation",
      "mime_type": "application/json",
      "extension": ".json"
    },
    {
      "id": "excel",
      "name": "Excel",
      "description": "Microsoft Excel workbook",
      "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "extension": ".xlsx"
    }
  ]
}
```

### Get Available Devices

```http
GET /api/exports/devices
Authorization: Bearer {token}
```

**Response:**
```json
{
  "devices": [
    {
      "device_ip": "192.168.1.100",
      "device_name": "Living Room Lamp",
      "device_type": "plug",
      "last_seen": "2024-01-15T10:30:00Z",
      "data_points": 8760
    }
  ]
}
```

### Get Available Metrics

```http
GET /api/exports/metrics
Authorization: Bearer {token}
```

**Response:**
```json
{
  "metrics": [
    {
      "field": "power_w",
      "name": "Power (Watts)",
      "description": "Instantaneous power consumption",
      "data_type": "float",
      "unit": "W"
    },
    {
      "field": "energy_kwh",
      "name": "Energy (kWh)",
      "description": "Cumulative energy consumption",
      "data_type": "float",
      "unit": "kWh"
    },
    {
      "field": "cost",
      "name": "Cost",
      "description": "Calculated energy cost",
      "data_type": "float",
      "unit": "currency"
    }
  ]
}
```

### Create Export Job

```http
POST /api/exports/create
Authorization: Bearer {token}
Content-Type: application/json

{
  "export_type": "device_data",
  "format": "csv",
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  },
  "devices": ["192.168.1.100"],
  "fields": ["timestamp", "power_w", "energy_kwh", "voltage", "current", "cost"],
  "aggregation": "hourly",
  "filters": {
    "min_power": 0,
    "max_power": 2000
  },
  "options": {
    "include_headers": true,
    "timezone": "America/New_York",
    "decimal_places": 2
  }
}
```

**Response:**
```json
{
  "export_id": "export_12345",
  "status": "queued",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:32:00Z",
  "download_url": "/api/exports/download/export_12345"
}
```

### Check Export Status

```http
GET /api/exports/export_12345
Authorization: Bearer {token}
```

**Response:**
```json
{
  "export_id": "export_12345",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:31:45Z",
  "file_size": 1024000,
  "record_count": 744,
  "download_url": "/api/exports/download/export_12345",
  "expires_at": "2024-01-22T10:31:45Z"
}
```

### Export History

```http
GET /api/exports/history?limit=10&offset=0
Authorization: Bearer {token}
```

**Response:**
```json
{
  "exports": [
    {
      "export_id": "export_12345",
      "export_type": "device_data",
      "format": "csv",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "file_size": 1024000,
      "record_count": 744,
      "user_id": 1,
      "username": "admin",
      "retention_days": 7,
      "expires_at": "2024-01-22T10:30:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 10
}
```

**Note:** Regular users only see their own exports. Admins see all exports.

### Delete Export

```http
DELETE /api/exports/{export_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Export deleted successfully",
  "export_id": "export_12345",
  "deleted_at": "2024-01-15T11:00:00Z"
}
```

**Note:** Users can only delete their own exports unless they have admin role.

## Export Types

### Device Data Export

```json
{
  "export_type": "device_data",
  "format": "csv",
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  },
  "devices": ["192.168.1.100", "192.168.1.101"],
  "fields": [
    "timestamp",
    "device_ip",
    "device_name", 
    "power_w",
    "energy_kwh",
    "voltage",
    "current",
    "cost",
    "is_on"
  ],
  "aggregation": "raw"  // raw, hourly, daily, weekly, monthly
}
```

### Cost Analysis Export

```json
{
  "export_type": "cost_analysis",
  "format": "excel",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "grouping": "monthly",
  "include_charts": true,
  "breakdown_by": ["device", "time_of_use", "rate_tier"]
}
```

### System Reports

```json
{
  "export_type": "system_report",
  "format": "pdf",
  "report_sections": [
    "device_summary",
    "energy_consumption",
    "cost_breakdown",
    "system_health",
    "usage_patterns"
  ],
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  }
}
```

### Audit Log Export

```json
{
  "export_type": "audit_logs",
  "format": "json",
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  },
  "event_types": ["login_success", "login_failure", "device_controlled"],
  "severity_levels": ["info", "warning", "error"],
  "users": ["admin", "operator"]
}
```

## Advanced Features

### Data Aggregation

```json
{
  "aggregation": "hourly",
  "aggregation_functions": {
    "power_w": "average",
    "energy_kwh": "sum",
    "cost": "sum",
    "voltage": "average"
  }
}
```

### Filtering Options

```json
{
  "filters": {
    "min_power": 10,        // Minimum power threshold
    "max_power": 1500,      // Maximum power threshold
    "device_states": ["on"], // Only include when device is on
    "exclude_outliers": true, // Remove statistical outliers
    "time_of_day": {         // Filter by time range
      "start": "06:00",
      "end": "22:00"
    },
    "days_of_week": [1, 2, 3, 4, 5] // Monday-Friday only
  }
}
```

### Custom Fields

```json
{
  "custom_fields": [
    {
      "name": "efficiency",
      "formula": "power_w / rated_power * 100",
      "unit": "%"
    },
    {
      "name": "daily_average",
      "formula": "SUM(energy_kwh) / COUNT(DISTINCT DATE(timestamp))",
      "unit": "kWh/day"
    }
  ]
}
```

## Scheduled Exports

### Create Scheduled Export

```http
POST /api/exports/schedule
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Monthly Device Report",
  "schedule": "0 9 1 * *",  // First day of month at 9 AM
  "export_config": {
    "export_type": "device_data",
    "format": "excel",
    "date_range": "last_month",
    "devices": "all",
    "fields": ["timestamp", "device_name", "energy_kwh", "cost"]
  },
  "delivery": {
    "method": "email",
    "recipients": ["admin@example.com"],
    "subject": "Monthly Energy Report - {{date}}"
  }
}
```

### Manage Scheduled Exports

```http
GET /api/exports/schedules
PUT /api/exports/schedules/{schedule_id}
DELETE /api/exports/schedules/{schedule_id}
```

## Preview Data

### Generate Preview

```http
GET /api/exports/preview?export_type=device_data&devices=192.168.1.100&limit=5
Authorization: Bearer {token}
```

**Response:**
```json
{
  "preview": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "device_ip": "192.168.1.100",
      "device_name": "Living Room Lamp",
      "power_w": 45.2,
      "energy_kwh": 0.045,
      "cost": 0.005
    }
  ],
  "total_records": 8760,
  "estimated_file_size": "2.1 MB",
  "preview_note": "Showing first 5 records"
}
```

## Export Statistics

### Get Export Statistics

```http
GET /api/exports/stats
Authorization: Bearer {token}
```

**Response:**
```json
{
  "total_exports": 156,
  "exports_this_month": 23,
  "total_data_exported": "450.2 MB",
  "most_popular_format": "csv",
  "export_types": {
    "device_data": 120,
    "cost_analysis": 25,
    "system_report": 8,
    "audit_logs": 3
  },
  "formats": {
    "csv": 89,
    "excel": 45,
    "json": 15,
    "pdf": 7
  }
}
```

## Error Handling

### Common Error Responses

**Permission Denied:**
```json
{
  "detail": "Permission denied",
  "error_code": "PERMISSION_DENIED",
  "message": "You don't have permission to perform data exports",
  "required_permission": "DATA_EXPORT"
}
```

**Access Denied (Ownership):**
```json
{
  "detail": "Access denied",
  "error_code": "ACCESS_DENIED",
  "message": "You don't have access to this export",
  "export_owner": "other_user"
}
```

**Rate Limit Exceeded:**
```json
{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Export rate limit exceeded. Please try again later.",
  "limit": "10 per hour",
  "retry_after": "2024-01-15T11:30:00Z"
}
```

**Invalid date range:**
```json
{
  "detail": "Invalid date range",
  "error_code": "INVALID_DATE_RANGE",
  "message": "Start date must be before end date"
}
```

**Export not found:**
```json
{
  "detail": "Export not found",
  "error_code": "EXPORT_NOT_FOUND",
  "message": "Export with ID 'export_12345' does not exist or you don't have access"
}
```

**Export expired:**
```json
{
  "detail": "Export expired",
  "error_code": "EXPORT_EXPIRED",
  "message": "Export file has expired and is no longer available",
  "expired_at": "2024-01-22T10:30:00Z"
}
```

## Security & Privacy

### Data Access Control

- **Permission-based access** - Requires DATA_EXPORT permission
- **User ownership validation** - Users can only access their own exports
- **Admin override** - Admins can access all exports
- **Comprehensive audit logging** - GDPR/SOX compliant activity tracking
- **Rate limiting** - Prevents abuse with 10 exports/hour limit

### Export Retention Policies

**Automated Cleanup System:**
```json
{
  "retention_policies": [
    {
      "export_type": "device_data",
      "retention_days": 7,
      "auto_delete": true
    },
    {
      "export_type": "audit_logs",
      "retention_days": 30,
      "auto_delete": true,
      "compliance_hold": true
    },
    {
      "export_type": "system_report",
      "retention_days": 90,
      "auto_delete": false
    }
  ],
  "cleanup_schedule": "0 2 * * *",  // Daily at 2 AM
  "notification_before_deletion": 24  // Hours
}
```

### Compliance Features

**GDPR Compliance:**
- Right to data portability (export personal data)
- Audit trail of all data access
- User consent tracking
- Data anonymization options

**SOX Compliance:**
- Tamper-evident audit logs
- User authentication tracking
- Data integrity validation
- Change management records

### Data Privacy

```json
{
  "privacy_options": {
    "anonymize_ip_addresses": true,
    "exclude_user_data": true,
    "hash_device_identifiers": true,
    "remove_location_data": true
  }
}
```

## Performance Optimization

### Large Dataset Handling

```json
{
  "performance_options": {
    "chunk_size": 10000,      // Process in chunks
    "compression": true,       // Compress export files
    "background_processing": true, // Process in background
    "cache_results": false     // Don't cache large exports
  }
}
```

### Export Limits

```json
{
  "limits": {
    "max_records_per_export": 1000000,
    "max_date_range_days": 366,
    "max_concurrent_exports": 3,
    "max_file_size_mb": 100
  }
}
```

## Integration Examples

### Python Integration

```python
import requests
import pandas as pd
from io import StringIO

def export_device_data(token, device_ip, start_date, end_date):
    # Create export
    export_request = {
        "export_type": "device_data",
        "format": "csv",
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "devices": [device_ip],
        "fields": ["timestamp", "power_w", "energy_kwh", "cost"]
    }
    
    response = requests.post(
        "http://localhost:5272/api/exports/create",
        json=export_request,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    export_id = response.json()["export_id"]
    
    # Wait for completion and download
    while True:
        status_response = requests.get(
            f"http://localhost:5272/api/exports/{export_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        status = status_response.json()["status"]
        if status == "completed":
            break
        elif status == "failed":
            raise Exception("Export failed")
        
        time.sleep(5)
    
    # Download data
    download_response = requests.get(
        f"http://localhost:5272/api/exports/download/{export_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Convert to pandas DataFrame
    df = pd.read_csv(StringIO(download_response.text))
    return df

# Usage
df = export_device_data(
    token="your_jwt_token",
    device_ip="192.168.1.100",
    start_date="2024-01-01",
    end_date="2024-01-31"
)

print(f"Exported {len(df)} records")
print(df.head())
```

### JavaScript Integration

```javascript
class KasaDataExporter {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.token = token;
    }
    
    async createExport(config) {
        const response = await fetch(`${this.baseUrl}/api/exports/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        return await response.json();
    }
    
    async downloadExport(exportId) {
        const response = await fetch(`${this.baseUrl}/api/exports/download/${exportId}`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        
        return await response.blob();
    }
    
    async waitForCompletion(exportId, maxWaitTime = 300000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitTime) {
            const response = await fetch(`${this.baseUrl}/api/exports/${exportId}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            
            const status = await response.json();
            
            if (status.status === 'completed') {
                return status;
            } else if (status.status === 'failed') {
                throw new Error('Export failed');
            }
            
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
        
        throw new Error('Export timeout');
    }
}

// Usage
const exporter = new KasaDataExporter('http://localhost:5272', 'your_jwt_token');

const exportConfig = {
    export_type: 'device_data',
    format: 'json',
    date_range: {
        start: '2024-01-01T00:00:00Z',
        end: '2024-01-31T23:59:59Z'
    },
    devices: ['192.168.1.100'],
    fields: ['timestamp', 'power_w', 'energy_kwh', 'cost']
};

async function exportData() {
    try {
        const exportJob = await exporter.createExport(exportConfig);
        console.log('Export created:', exportJob.export_id);
        
        await exporter.waitForCompletion(exportJob.export_id);
        console.log('Export completed');
        
        const data = await exporter.downloadExport(exportJob.export_id);
        console.log('Data downloaded:', data.size, 'bytes');
        
        // Create download link
        const url = URL.createObjectURL(data);
        const a = document.createElement('a');
        a.href = url;
        a.download = `export_${exportJob.export_id}.json`;
        a.click();
        
    } catch (error) {
        console.error('Export failed:', error);
    }
}
```

## Related Pages

- [API Documentation](API-Documentation) - Complete API reference
- [Audit Logging](Audit-Logging) - Audit log export features
- [Cost Analysis](Cost-Analysis) - Cost calculation details
- [Device Management](Device-Management) - Device data structure

## Frontend Integration

### Data Export Modal

The Data Export Modal is now integrated into the main UI with permission checks:

```typescript
// DataExportModal component usage
import { DataExportModal } from '@/components/data-export-modal';

function DeviceCard({ device }) {
  const [showExportModal, setShowExportModal] = useState(false);
  const { user } = useAuth();
  
  // Check if user has export permission
  const canExport = user?.permissions?.includes('DATA_EXPORT');
  
  return (
    <>
      {canExport && (
        <Button 
          onClick={() => setShowExportModal(true)}
          icon={<DownloadIcon />}
        >
          Export Data
        </Button>
      )}
      
      {showExportModal && (
        <DataExportModal
          device={device}
          onClose={() => setShowExportModal(false)}
          onExport={handleExport}
        />
      )}
    </>
  );
}
```

### Device-Specific Exports

Export data for individual devices directly from the device card:

```javascript
async function exportDeviceData(deviceId, dateRange, format) {
  const response = await apiClient.post('/api/exports/create', {
    export_type: 'device_data',
    devices: [deviceId],
    date_range: dateRange,
    format: format
  });
  
  // Handle rate limiting
  if (response.status === 429) {
    const retryAfter = response.headers['retry-after'];
    showNotification(`Export limit reached. Try again in ${retryAfter} seconds.`);
    return;
  }
  
  // Monitor export progress
  const exportId = response.data.export_id;
  await monitorExportProgress(exportId);
}
```

## Implementation Notes

The Data Export System has been significantly enhanced in v1.2.0 with:

### Security Enhancements
- **Permission-based access control** - All endpoints require DATA_EXPORT permission
- **User ownership validation** - Prevents unauthorized access to exports
- **Comprehensive audit logging** - GDPR/SOX compliance with detailed activity tracking
- **Rate limiting** - Prevents abuse with configurable limits
- **Secure file handling** - Atomic operations with proper error handling

### UI Integration
- **DataExportModal component** - Integrated into main UI with permission checks
- **Device-specific exports** - Export individual device data from device cards
- **Export history view** - Track and manage previous exports
- **Progress indicators** - Real-time export status updates

### Backend Improvements
- **Database schema updates** - Added user_id column for ownership tracking
- **Export retention system** - Automated cleanup with configurable policies
- **Enhanced error handling** - Structured error responses for better UX
- **Performance optimization** - Efficient processing of large datasets

All exports are now tracked with user ownership, validated for permissions, logged for compliance, and automatically cleaned up based on retention policies.

---

**Document Version:** 2.0.0  
**Last Updated:** 2025-08-26  
**Review Status:** Current  
**Change Summary:** Updated with v1.2.0 security enhancements including permission enforcement, user ownership validation, audit logging, rate limiting, and retention policies