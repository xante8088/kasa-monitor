# Export Retention Policies Implementation

## Overview

This document outlines the complete implementation of export retention policies for the Kasa Monitor data export system. The implementation provides automated cleanup, storage management, and compliance-friendly file lifecycle management.

## Components Implemented

### 1. Core Services

#### ExportRetentionService (`export_retention_service.py`)
- **Purpose**: Main service for managing export file lifecycle
- **Key Features**:
  - Configurable retention periods based on format, size, user role, and access patterns
  - Automated cleanup of expired exports
  - Storage space monitoring with emergency cleanup
  - Smart retention logic with bonus time for popular/admin exports
  - Comprehensive audit logging for all retention operations

#### ExportRetentionScheduler (`export_retention_scheduler.py`) 
- **Purpose**: Background scheduler for automated retention tasks
- **Key Features**:
  - Daily maintenance at configurable hours (default 2 AM)
  - Hourly checks for expiring exports and batch cleanup
  - Emergency storage cleanup when disk space is low
  - Storage monitoring with different schedules for business hours
  - Comprehensive error handling and recovery

#### ExportRetentionConfig (`export_retention_config.py`)
- **Purpose**: Configuration management for retention policies
- **Key Features**:
  - Database-backed configuration with audit trail
  - Environment variable integration
  - Category-based configuration organization
  - Type-safe value conversion and validation
  - Configuration import/export functionality

### 2. API Integration

#### ExportRetentionAPI (`export_retention_api.py`)
- **Purpose**: REST API endpoints for retention management
- **Key Features**:
  - User access to expiring exports and retention info
  - Admin controls for policy management and forced cleanup
  - Export download tracking (affects retention calculation)
  - Configuration management endpoints
  - Comprehensive error handling and security checks

### 3. System Integration

#### ExportRetentionIntegration (`export_retention_integration.py`)
- **Purpose**: System-wide integration and startup/shutdown
- **Key Features**:
  - Global system initialization and management
  - Environment variable configuration application
  - Health checks and system status monitoring
  - Graceful startup and shutdown procedures

### 4. Enhanced Export Service

#### Enhanced DataExportService (`data_export_service.py`)
- **Key Additions**:
  - Retention period calculation during export creation
  - Download tracking for retention bonus calculations
  - Export extension capabilities
  - User notification for expiring exports
  - Integration with retention service for lifecycle management

## Database Schema Changes

### New Tables

#### `export_retention_policies`
```sql
CREATE TABLE export_retention_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_type TEXT NOT NULL,
    policy_key TEXT NOT NULL,
    retention_days INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(policy_type, policy_key)
);
```

#### `export_retention_audit`
```sql
CREATE TABLE export_retention_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    export_id TEXT NOT NULL,
    action TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    retention_days INTEGER,
    file_size INTEGER,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Modified Tables

#### `data_exports` - New Columns
- `expires_at TIMESTAMP` - Calculated expiration date
- `accessed_at TIMESTAMP` - Last download time
- `retention_period INTEGER` - Retention in days
- `status TEXT DEFAULT 'active'` - Lifecycle state
- `download_count INTEGER DEFAULT 0` - Number of downloads
- `user_role TEXT` - User role for retention calculation

#### `system_config` - Enhanced Configuration
- Extended to support all retention configuration options
- Category-based organization for easy management
- Type-safe value storage and retrieval

## Configuration Options

### Default Retention Policies
```python
DEFAULT_RETENTION_POLICIES = {
    "default": 30,      # 30 days default
    "csv": 7,           # CSV exports - 7 days
    "excel": 14,        # Excel exports - 14 days  
    "json": 30,         # JSON exports - 30 days
    "sqlite": 90,       # SQLite exports - 90 days
    "large_export": 3,  # Large exports (>100MB) - 3 days
}
```

### Environment Variables
```bash
# Core settings
EXPORT_RETENTION_ENABLED=true
EXPORT_DEFAULT_RETENTION_DAYS=30
EXPORT_CLEANUP_HOUR=2

# Format-specific retention
EXPORT_CSV_RETENTION_DAYS=7
EXPORT_EXCEL_RETENTION_DAYS=14
EXPORT_JSON_RETENTION_DAYS=30
EXPORT_SQLITE_RETENTION_DAYS=90

# Storage thresholds
EXPORT_MAX_STORAGE_GB=50
EXPORT_EMERGENCY_CLEANUP_THRESHOLD_GB=1
EXPORT_WARNING_THRESHOLD_GB=5
EXPORT_LARGE_FILE_THRESHOLD_MB=100
```

### System Configuration Keys
- `export.retention.enabled` - Enable/disable retention system
- `export.retention.default_days` - Default retention period
- `export.retention.{format}_days` - Format-specific retention periods
- `export.cleanup.hour` - Daily cleanup hour (0-23)
- `export.cleanup.check_interval_minutes` - Scheduler check interval
- `export.storage.*` - Storage management settings
- `export.user.*` - User-specific retention bonuses

## Smart Retention Logic

### Base Retention Calculation
1. **Format-based**: Each export format has default retention period
2. **File size**: Large files (>100MB) get reduced retention (max 3 days)
3. **User role**: Admin exports get +14 days bonus
4. **Access frequency**: Files downloaded >5 times get +7 days bonus

### Lifecycle States
- `ACTIVE` - Export available for download
- `EXPIRES_SOON` - Within 24 hours of expiration
- `EXPIRED` - Past retention period but not yet deleted
- `DELETED` - File removed from system

### Emergency Cleanup Priorities
1. **Phase 1**: Remove already expired exports
2. **Phase 2**: Remove large exports (>100MB) older than 1 day
3. **Phase 3**: Remove oldest exports if still needed

## Storage Management

### Monitoring Thresholds
- **Emergency cleanup**: <1GB free space triggers immediate cleanup
- **Warning level**: <5GB free space logs warnings
- **Large file threshold**: 100MB files get special handling

### Cleanup Scheduling
- **Daily maintenance**: Runs at configured hour (default 2 AM)
- **Hourly checks**: Mark expiring exports and small batch cleanup
- **Storage monitoring**: Business hours (hourly) vs off-hours (every 4 hours)
- **Emergency cleanup**: Triggered immediately when space critically low

## Audit Logging

### Retention Events Logged
- **Retention calculation**: When periods are calculated/updated
- **File expiration**: When exports reach expiration
- **File deletion**: When files are physically removed
- **Policy changes**: When retention policies are modified
- **Emergency cleanup**: When emergency procedures are triggered
- **Download tracking**: When exports are accessed (affects retention)

### Event Details Included
- Export metadata (size, format, age, user)
- Retention calculation factors
- Storage space information
- Policy settings at time of action
- Error messages and recovery actions

## API Endpoints

### User Endpoints
- `GET /api/exports/retention/exports/expiring` - Get expiring exports
- `GET /api/exports/retention/exports/{id}/retention` - Get retention info
- `PUT /api/exports/retention/exports/extend` - Extend retention period
- `POST /api/exports/retention/exports/{id}/download` - Record download
- `GET /api/exports/retention/status` - Get system status
- `GET /api/exports/retention/statistics` - Get retention statistics

### Admin Endpoints
- `GET /api/exports/retention/policies` - Get retention policies
- `PUT /api/exports/retention/policies` - Update retention policies  
- `GET /api/exports/retention/config/{category}` - Get configuration
- `PUT /api/exports/retention/config` - Update configuration
- `POST /api/exports/retention/maintenance/run` - Force maintenance
- `POST /api/exports/retention/cleanup/emergency` - Force emergency cleanup
- `GET /api/exports/retention/config/export` - Export configuration
- `POST /api/exports/retention/config/import` - Import configuration

## Integration with Main Application

### Startup Integration
```python
from export_retention_integration import startup_retention_system

# In main application startup
retention_system = await startup_retention_system()
```

### Shutdown Integration  
```python
from export_retention_integration import shutdown_retention_system_handler

# In main application shutdown
await shutdown_retention_system_handler()
```

### Health Check Integration
```python
from export_retention_integration import health_check_retention_system

# In health check endpoint
retention_health = await health_check_retention_system()
```

### FastAPI Router Registration
```python
from export_retention_api import router as retention_router

app.include_router(retention_router)
```

## Testing and Validation

### Test Scenarios Covered
1. **Retention Policy Calculation**
   - Format-based retention periods
   - Size-based adjustments
   - User role bonuses
   - Access frequency bonuses

2. **Cleanup Operations**
   - Regular expired export cleanup
   - Emergency storage cleanup
   - Batch processing performance
   - Error recovery

3. **Storage Monitoring**
   - Disk space calculation
   - Warning thresholds
   - Emergency triggers
   - Space freed calculations

4. **Configuration Management**
   - Environment variable loading
   - Database configuration updates
   - Type conversion and validation
   - Audit trail generation

5. **API Security**
   - User ownership validation
   - Admin permission checks
   - Export access control
   - Input validation

### Performance Considerations
- **Batch Processing**: Cleanup operations process exports in batches to avoid system overload
- **Efficient Queries**: Database indexes on expiration dates and status fields
- **Background Processing**: All heavy operations run in background scheduler
- **Graceful Degradation**: System continues functioning if scheduler fails
- **Resource Management**: Configurable cleanup intervals and batch sizes

## Compliance and Security

### Data Protection
- **Secure Deletion**: Physical file removal with audit trail
- **Access Control**: User-based export ownership validation
- **Audit Trail**: Comprehensive logging of all retention actions
- **Configuration Security**: Readonly and sensitive config flags

### Compliance Features
- **Retention Policies**: Configurable periods for different data types
- **Audit Logging**: Complete trail of data lifecycle events
- **Manual Override**: Admin capability to extend retention when needed
- **Emergency Procedures**: Documented and logged emergency cleanup
- **Data Export**: Configuration and audit data can be exported for compliance

## Monitoring and Alerting

### Key Metrics
- Storage space utilization
- Number of exports by lifecycle status
- Cleanup operation success rates
- Retention policy compliance
- Emergency cleanup frequency

### Alert Conditions
- Low storage space warnings
- Failed cleanup operations
- Configuration changes
- Emergency cleanup triggers
- Scheduler health issues

## Future Enhancements

### Potential Improvements
1. **Notification System**: Email/UI notifications for expiring exports
2. **Archive Storage**: Move old exports to cheaper storage before deletion
3. **Retention Templates**: Predefined retention profiles for different use cases
4. **Advanced Analytics**: Usage patterns and optimization recommendations
5. **Multi-tier Storage**: Different storage classes based on access patterns
6. **Export Compression**: Automatic compression for old exports
7. **Backup Integration**: Include export retention in backup procedures

### Configuration Enhancements
1. **Time-based Policies**: Different retention periods for different times
2. **User Group Policies**: Retention based on user groups/departments
3. **Content-based Policies**: Retention based on export content analysis
4. **Dynamic Policies**: AI-driven retention period optimization

## Deployment Notes

### Prerequisites
- SQLite database with existing export tables
- Write access to exports directory
- Environment variable configuration (optional)
- FastAPI application for API endpoints

### Installation Steps
1. Copy all retention system files to backend directory
2. Update main application to include retention startup/shutdown
3. Register API router in FastAPI application
4. Configure environment variables as needed
5. Run database schema updates (handled automatically)
6. Verify system health checks pass

### Monitoring
- Check scheduler status regularly
- Monitor storage space utilization
- Review audit logs for unusual activity
- Validate retention policy compliance
- Monitor cleanup operation success rates

The export retention system provides a comprehensive solution for managing export file lifecycles with professional-grade features including automated cleanup, storage management, audit logging, and compliance support. The modular design allows for easy customization and extension while maintaining robust performance and security.