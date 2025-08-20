# Data Export System

Comprehensive data export and analysis system for Kasa Monitor device and energy data.

## Overview

The Data Export System provides powerful tools for exporting, analyzing, and sharing your energy monitoring data. Export device readings, cost analysis, and system reports in multiple formats for external analysis, compliance reporting, or data backup.

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
      "record_count": 744
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 10
}
```

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
  "message": "Export with ID 'export_12345' does not exist"
}
```

**Export expired:**
```json
{
  "detail": "Export expired",
  "error_code": "EXPORT_EXPIRED",
  "message": "Export file has expired and is no longer available"
}
```

## Security & Privacy

### Data Access Control

- **User-based filtering** - Users only see their own devices
- **Role-based access** - Different export capabilities by role
- **Audit logging** - All export activities are logged
- **Temporary files** - Export files auto-delete after 7 days

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
        "http://localhost:8000/api/exports/create",
        json=export_request,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    export_id = response.json()["export_id"]
    
    # Wait for completion and download
    while True:
        status_response = requests.get(
            f"http://localhost:8000/api/exports/{export_id}",
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
        f"http://localhost:8000/api/exports/download/{export_id}",
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
const exporter = new KasaDataExporter('http://localhost:8000', 'your_jwt_token');

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

## Implementation Notes

The Data Export System is a fully implemented feature that provides:

- **Real-time export processing** with background job support
- **Multiple format support** including CSV, JSON, Excel, and PDF
- **Flexible filtering and aggregation** options
- **Security and privacy controls** with user-based access
- **Integration-friendly APIs** for external systems
- **Performance optimization** for large datasets

All exports are tracked through audit logging and include automatic cleanup of temporary files.