# Plugin API Documentation

This document provides comprehensive API documentation for the Kasa Monitor plugin system.

## Table of Contents

1. [REST API Endpoints](#rest-api-endpoints)
2. [Plugin Base Class API](#plugin-base-class-api)
3. [Hook System API](#hook-system-api)
4. [Database Manager API](#database-manager-api)
5. [Configuration API](#configuration-api)
6. [Error Handling](#error-handling)
7. [Authentication](#authentication)
8. [Rate Limiting](#rate-limiting)

## REST API Endpoints

All plugin management endpoints are available under `/api/plugins/`.

### Authentication

All endpoints require authentication via Bearer token:

```http
Authorization: Bearer <your-jwt-token>
```

### List Plugins

Get all discovered plugins with their current status.

```http
GET /api/plugins
```

**Response:**
```json
[
  {
    "id": "power-monitor",
    "name": "Power Monitor",
    "version": "1.0.0",
    "author": "Kasa Monitor Team",
    "description": "Monitor device power consumption",
    "plugin_type": "device",
    "state": "running",
    "enabled": true,
    "main_class": "PowerMonitorPlugin",
    "dependencies": [],
    "python_dependencies": [],
    "permissions": ["devices.read", "notifications.send"],
    "config_schema": { ... },
    "hooks": ["device.reading_updated"],
    "api_version": "1.0",
    "min_app_version": "0.3.0",
    "homepage": "https://github.com/kasaweb/kasa-monitor",
    "license": "GPL-3.0",
    "error_message": null,
    "last_updated": "2025-01-01T12:00:00Z"
  }
]
```

### Get Plugin Details

Get detailed information about a specific plugin.

```http
GET /api/plugins/{plugin_id}
```

**Parameters:**
- `plugin_id` (string): Unique plugin identifier

**Response:**
```json
{
  "id": "power-monitor",
  "name": "Power Monitor",
  "version": "1.0.0",
  "state": "running",
  "enabled": true,
  "status": {
    "power_threshold": 1000,
    "check_interval": 60,
    "monitoring_active": true
  },
  "metrics": {
    "hooks_registered": 2,
    "events_processed": 150,
    "last_activity": "2025-01-01T12:00:00Z"
  }
}
```

### Enable Plugin

Enable a plugin and start its services.

```http
POST /api/plugins/{plugin_id}/enable
```

**Response:**
```json
{
  "status": "success",
  "message": "Plugin enabled successfully",
  "plugin_state": "running"
}
```

### Disable Plugin

Disable a plugin and stop its services.

```http
POST /api/plugins/{plugin_id}/disable
```

**Response:**
```json
{
  "status": "success",
  "message": "Plugin disabled successfully",
  "plugin_state": "disabled"
}
```

### Reload Plugin

Reload a plugin (useful for development).

```http
POST /api/plugins/{plugin_id}/reload
```

**Response:**
```json
{
  "status": "success",
  "message": "Plugin reloaded successfully",
  "plugin_state": "running"
}
```

### Delete Plugin

Remove a plugin from the system.

```http
DELETE /api/plugins/{plugin_id}
```

**Response:**
```json
{
  "status": "success",
  "message": "Plugin deleted successfully"
}
```

### Install Plugin

Install a new plugin from uploaded ZIP file.

```http
POST /api/plugins/install
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (file): ZIP file containing plugin

**Response:**
```json
{
  "status": "success",
  "message": "Plugin installed successfully",
  "plugin_id": "my-new-plugin",
  "name": "My New Plugin",
  "version": "1.0.0"
}
```

### Get Plugin Configuration

Get current plugin configuration.

```http
GET /api/plugins/{plugin_id}/config
```

**Response:**
```json
{
  "config": {
    "power_threshold": 1000,
    "check_interval": 60,
    "enabled_devices": ["192.168.1.100", "192.168.1.101"]
  },
  "schema": {
    "type": "object",
    "properties": {
      "power_threshold": {
        "type": "number",
        "default": 1000,
        "description": "Power threshold in watts"
      }
    }
  }
}
```

### Update Plugin Configuration

Update plugin configuration.

```http
PUT /api/plugins/{plugin_id}/config
Content-Type: application/json
```

**Request Body:**
```json
{
  "config": {
    "power_threshold": 1500,
    "check_interval": 30
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Configuration updated successfully"
}
```

### Execute Plugin Action

Execute a plugin-specific action.

```http
POST /api/plugins/{plugin_id}/action
Content-Type: application/json
```

**Request Body:**
```json
{
  "action": "update_threshold",
  "params": {
    "threshold": 1200
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Threshold updated to 1200W",
  "result": {
    "previous_threshold": 1000,
    "new_threshold": 1200
  }
}
```

### Get Plugin Metrics

Get plugin performance metrics.

```http
GET /api/plugins/metrics
```

**Response:**
```json
{
  "total_count": 5,
  "enabled_count": 3,
  "running_count": 3,
  "error_count": 0,
  "by_type": {
    "device": 2,
    "integration": 1,
    "analytics": 2
  },
  "by_state": {
    "running": 3,
    "disabled": 2
  }
}
```

### Get Plugin Logs

Get recent plugin logs.

```http
GET /api/plugins/{plugin_id}/logs?limit=100&level=info
```

**Parameters:**
- `limit` (integer, optional): Maximum number of log entries (default: 100)
- `level` (string, optional): Minimum log level (debug, info, warning, error)
- `since` (datetime, optional): Return logs since this timestamp

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-01-01T12:00:00Z",
      "level": "info",
      "message": "Plugin initialized successfully",
      "logger": "power-monitor"
    }
  ],
  "total_count": 150,
  "has_more": true
}
```

## Plugin Base Class API

The `PluginBase` class provides the foundation for all plugins.

### Constructor

```python
class PluginBase:
    def __init__(self):
        self.plugin_id: str = None
        self.config: Dict[str, Any] = {}
        self.db_manager: DatabaseManager = None
        self.hook_manager: HookManager = None
        self.logger: logging.Logger = None
```

### Required Methods

#### Initialize

```python
async def initialize(self) -> bool:
    """
    Initialize the plugin.
    
    Called when the plugin is loaded and should perform setup tasks
    such as loading configuration, registering hooks, and starting
    background tasks.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    pass
```

#### Shutdown

```python
async def shutdown(self) -> None:
    """
    Shutdown the plugin.
    
    Called when the plugin is being unloaded. Should clean up
    resources, unregister hooks, and stop background tasks.
    """
    pass
```

### Optional Methods

#### Get Status

```python
async def get_status(self) -> Dict[str, Any]:
    """
    Get current plugin status.
    
    Returns:
        Dict containing status information for monitoring and debugging
    """
    return {"status": "running"}
```

#### Handle Action

```python
async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle plugin-specific actions.
    
    Args:
        action: Action name to execute
        params: Action parameters
        
    Returns:
        Dict with status and result information
    """
    return {"status": "error", "message": "Action not supported"}
```

### Configuration Methods

#### Get Configuration

```python
async def get_config(self) -> Dict[str, Any]:
    """
    Get current plugin configuration.
    
    Returns:
        Dict containing current configuration values
    """
    pass
```

#### Update Configuration

```python
async def update_config(self, config: Dict[str, Any]) -> bool:
    """
    Update plugin configuration.
    
    Args:
        config: New configuration values to merge
        
    Returns:
        bool: True if update successful
    """
    pass
```

### Utility Methods

#### Create Task

```python
def create_task(self, coro) -> asyncio.Task:
    """
    Create a managed asyncio task.
    
    Tasks created this way are automatically cancelled during shutdown.
    
    Args:
        coro: Coroutine to execute
        
    Returns:
        asyncio.Task object
    """
    pass
```

## Hook System API

The hook system enables event-driven communication between plugins and the core system.

### HookManager Class

#### Register Hook

```python
async def register_hook(self, event_name: str, handler: Callable) -> bool:
    """
    Register a handler for a specific event.
    
    Args:
        event_name: Name of the event to listen for
        handler: Async function to call when event occurs
        
    Returns:
        bool: True if registration successful
    """
    pass
```

#### Unregister Hook

```python
async def unregister_hook(self, event_name: str, handler: Callable) -> bool:
    """
    Unregister a previously registered handler.
    
    Args:
        event_name: Name of the event
        handler: Handler function to remove
        
    Returns:
        bool: True if unregistration successful
    """
    pass
```

#### Emit Hook

```python
async def emit_hook(self, event_name: str, data: Dict[str, Any]) -> int:
    """
    Emit an event to all registered handlers.
    
    Args:
        event_name: Name of the event to emit
        data: Event data to pass to handlers
        
    Returns:
        int: Number of handlers that received the event
    """
    pass
```

### Event Types

#### Device Events

**device.reading_updated**
```python
{
    "ip": "192.168.1.100",
    "alias": "Living Room Lamp",
    "model": "HS110",
    "current_power_w": 75.5,
    "voltage": 120.2,
    "current": 0.63,
    "total_energy_kwh": 45.2,
    "is_on": True,
    "rssi": -45,
    "timestamp": "2025-01-01T12:00:00Z"
}
```

**device.status_changed**
```python
{
    "ip": "192.168.1.100",
    "alias": "Living Room Lamp",
    "is_online": True,
    "previous_status": False,
    "timestamp": "2025-01-01T12:00:00Z"
}
```

**device.discovered**
```python
{
    "ip": "192.168.1.100",
    "alias": "New Device",
    "model": "HS110",
    "mac": "AA:BB:CC:DD:EE:FF",
    "device_type": "SmartPlug",
    "timestamp": "2025-01-01T12:00:00Z"
}
```

#### Notification Events

**notification.send**
```python
{
    "type": "power_alert",
    "severity": "warning",  # info, warning, error, critical
    "title": "High Power Usage",
    "message": "Device exceeds power threshold",
    "device_ip": "192.168.1.100",
    "timestamp": "2025-01-01T12:00:00Z",
    "metadata": {
        "threshold": 1000,
        "current_power": 1250
    }
}
```

#### System Events

**system.startup**
```python
{
    "timestamp": "2025-01-01T12:00:00Z",
    "version": "0.3.19"
}
```

**system.shutdown**
```python
{
    "timestamp": "2025-01-01T12:00:00Z",
    "reason": "user_requested"
}
```

## Database Manager API

The database manager provides access to device data and system information.

### Device Methods

#### Get Monitored Devices

```python
async def get_monitored_devices(self) -> List[Dict[str, Any]]:
    """
    Get list of all monitored devices.
    
    Returns:
        List of device dictionaries with current status
    """
    pass
```

#### Get Device Readings

```python
async def get_device_readings(
    self, 
    device_ip: str, 
    start_time: datetime, 
    end_time: datetime,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Get device readings within time range.
    
    Args:
        device_ip: Device IP address
        start_time: Start of time range
        end_time: End of time range
        limit: Maximum number of readings
        
    Returns:
        List of reading dictionaries
    """
    pass
```

#### Get Latest Device Reading

```python
async def get_latest_device_reading(self, device_ip: str) -> Optional[Dict[str, Any]]:
    """
    Get most recent reading for a device.
    
    Args:
        device_ip: Device IP address
        
    Returns:
        Latest reading dictionary or None
    """
    pass
```

#### Get Device Statistics

```python
async def get_device_stats(
    self, 
    device_ip: str, 
    days: int = 7
) -> Dict[str, Any]:
    """
    Get aggregated statistics for a device.
    
    Args:
        device_ip: Device IP address
        days: Number of days to analyze
        
    Returns:
        Statistics dictionary with averages, totals, etc.
    """
    pass
```

### User Methods

#### Get Current User

```python
async def get_current_user(self, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user information.
    
    Args:
        user_id: User ID
        
    Returns:
        User dictionary or None
    """
    pass
```

#### Check User Permission

```python
async def check_user_permission(self, user_id: int, permission: str) -> bool:
    """
    Check if user has specific permission.
    
    Args:
        user_id: User ID
        permission: Permission string (e.g., "devices.read")
        
    Returns:
        bool: True if user has permission
    """
    pass
```

## Configuration API

### Schema Validation

Plugin configurations are validated against JSON Schema definitions in the manifest.

#### Supported Types

```json
{
  "type": "object",
  "properties": {
    "string_field": {
      "type": "string",
      "default": "default_value",
      "description": "String configuration field"
    },
    "number_field": {
      "type": "number",
      "minimum": 0,
      "maximum": 1000,
      "default": 100,
      "description": "Numeric configuration field"
    },
    "integer_field": {
      "type": "integer",
      "minimum": 1,
      "default": 5,
      "description": "Integer configuration field"
    },
    "boolean_field": {
      "type": "boolean",
      "default": true,
      "description": "Boolean configuration field"
    },
    "array_field": {
      "type": "array",
      "items": {"type": "string"},
      "default": [],
      "description": "Array configuration field"
    },
    "enum_field": {
      "type": "string",
      "enum": ["option1", "option2", "option3"],
      "default": "option1",
      "description": "Enumerated configuration field"
    }
  },
  "required": ["string_field"]
}
```

#### Format Specifiers

```json
{
  "password_field": {
    "type": "string",
    "format": "password",
    "description": "Password field (hidden in UI)"
  },
  "textarea_field": {
    "type": "string",
    "format": "textarea",
    "description": "Multi-line text field"
  },
  "email_field": {
    "type": "string",
    "format": "email",
    "description": "Email address field"
  },
  "url_field": {
    "type": "string",
    "format": "uri",
    "description": "URL field"
  }
}
```

## Error Handling

### Error Response Format

All API endpoints return errors in a consistent format:

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "PLUGIN_NOT_FOUND",
  "error_type": "PluginError",
  "context": {
    "plugin_id": "invalid-plugin",
    "operation": "enable"
  }
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `PLUGIN_NOT_FOUND` | Plugin with specified ID not found |
| `PLUGIN_LOAD_ERROR` | Failed to load plugin code |
| `PLUGIN_INIT_ERROR` | Plugin initialization failed |
| `PLUGIN_CONFIG_ERROR` | Invalid plugin configuration |
| `PLUGIN_PERMISSION_ERROR` | Insufficient permissions |
| `PLUGIN_DEPENDENCY_ERROR` | Missing plugin dependencies |
| `PLUGIN_VERSION_ERROR` | Incompatible plugin version |
| `PLUGIN_MANIFEST_ERROR` | Invalid manifest.json |
| `PLUGIN_ALREADY_EXISTS` | Plugin with same ID already exists |

### Exception Classes

```python
class PluginError(Exception):
    """Base plugin system exception."""
    pass

class PluginNotFoundError(PluginError):
    """Plugin not found."""
    pass

class PluginLoadError(PluginError):
    """Failed to load plugin."""
    pass

class PluginInitError(PluginError):
    """Plugin initialization failed."""
    pass

class PluginConfigError(PluginError):
    """Invalid plugin configuration."""
    pass
```

## Authentication

### JWT Token Requirements

All plugin API endpoints require authentication using JWT tokens:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Required Permissions

Different operations require specific permissions:

| Operation | Required Permission |
|-----------|-------------------|
| List plugins | `plugins.view` |
| Enable/disable plugins | `plugins.manage` |
| Install plugins | `plugins.install` |
| Configure plugins | `plugins.configure` |
| Delete plugins | `plugins.delete` |
| View plugin logs | `system.logs` |

### Plugin Permissions

Plugins can request permissions in their manifest:

```json
{
  "permissions": [
    "devices.read",      // Read device data
    "devices.write",     // Control devices
    "devices.control",   // Send device commands
    "notifications.send", // Send notifications
    "system.config",     // Access system configuration
    "users.read",        // Read user information
    "analytics.read",    // Read analytics data
    "analytics.write"    // Write analytics data
  ]
}
```

## Rate Limiting

API endpoints have rate limits to prevent abuse:

| Endpoint | Rate Limit |
|----------|------------|
| GET requests | 100/minute |
| POST/PUT requests | 50/minute |
| Plugin installs | 10/hour |
| Configuration updates | 20/minute |

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

## SDK and Libraries

### Python SDK

A Python SDK is available for easier plugin development:

```python
from kasa_monitor_sdk import Plugin, hook, action

class MyPlugin(Plugin):
    @hook('device.reading_updated')
    async def on_device_reading(self, data):
        """Handle device readings."""
        pass
    
    @action('update_threshold')
    async def update_threshold(self, threshold: int):
        """Update power threshold."""
        self.config['threshold'] = threshold
        await self.save_config()
        return {"status": "success"}
```

### JavaScript/TypeScript SDK

For web-based plugins and integrations:

```typescript
import { PluginAPI } from '@kasa-monitor/plugin-sdk';

const api = new PluginAPI(baseURL, token);

// List plugins
const plugins = await api.plugins.list();

// Enable plugin
await api.plugins.enable('my-plugin');

// Update configuration
await api.plugins.updateConfig('my-plugin', { threshold: 1500 });
```

## Webhooks

Plugins can register webhooks for external integrations:

```python
class WebhookPlugin(PluginBase):
    async def register_webhook(self, url: str, events: List[str]):
        """Register webhook for events."""
        await self.hook_manager.register_webhook(url, events)
    
    async def on_device_reading(self, data):
        """Send webhook on device reading."""
        webhook_data = {
            "event": "device.reading_updated",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_webhook(webhook_data)
```

## Examples

### Complete Plugin Example

```python
"""Temperature Alert Plugin."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from plugin_system import PluginBase

logger = logging.getLogger(__name__)

class TemperatureAlertPlugin(PluginBase):
    """Monitor device temperature and send alerts."""
    
    def __init__(self):
        super().__init__()
        self.temp_threshold = 70.0  # Celsius
        self.check_interval = 300   # 5 minutes
        self.monitoring_task = None
        self.alert_history = {}
    
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            # Load configuration
            config = await self.get_config()
            self.temp_threshold = config.get('temp_threshold', 70.0)
            self.check_interval = config.get('check_interval', 300)
            
            # Register hooks
            await self.hook_manager.register_hook(
                'device.reading_updated', 
                self.on_device_reading
            )
            
            # Start monitoring task
            self.monitoring_task = self.create_task(self.monitor_temperatures())
            
            logger.info(f"Temperature Alert plugin initialized with {self.temp_threshold}°C threshold")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Temperature Alert plugin: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            
        await self.hook_manager.unregister_hook(
            'device.reading_updated',
            self.on_device_reading
        )
        
        logger.info("Temperature Alert plugin shutdown complete")
    
    async def on_device_reading(self, device_data: Dict[str, Any]) -> None:
        """Handle device reading updates."""
        device_ip = device_data.get('ip')
        temperature = device_data.get('temperature_c')
        
        if temperature and temperature > self.temp_threshold:
            await self.send_temperature_alert(device_data)
    
    async def send_temperature_alert(self, device_data: Dict[str, Any]) -> None:
        """Send high temperature alert."""
        device_ip = device_data.get('ip')
        temperature = device_data.get('temperature_c')
        
        # Throttle alerts (one per hour per device)
        now = datetime.now(timezone.utc)
        last_alert = self.alert_history.get(device_ip)
        
        if last_alert and (now - last_alert).total_seconds() < 3600:
            return
            
        self.alert_history[device_ip] = now
        
        # Send notification
        await self.hook_manager.emit_hook('notification.send', {
            'type': 'temperature_alert',
            'severity': 'warning',
            'title': 'High Temperature Alert',
            'message': f"Device {device_data.get('alias')} temperature: {temperature}°C",
            'device_ip': device_ip,
            'metadata': {
                'temperature': temperature,
                'threshold': self.temp_threshold
            }
        })
        
        logger.warning(f"High temperature alert: {device_ip} at {temperature}°C")
    
    async def monitor_temperatures(self) -> None:
        """Background temperature monitoring task."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Get all monitored devices
                devices = await self.db_manager.get_monitored_devices()
                
                for device in devices:
                    latest_reading = await self.db_manager.get_latest_device_reading(device['ip'])
                    if latest_reading:
                        await self.on_device_reading(latest_reading)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in temperature monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def get_status(self) -> Dict[str, Any]:
        """Get plugin status."""
        return {
            'temp_threshold': self.temp_threshold,
            'check_interval': self.check_interval,
            'monitoring_active': self.monitoring_task and not self.monitoring_task.done(),
            'recent_alerts': len(self.alert_history)
        }
    
    async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plugin actions."""
        if action == 'update_threshold':
            new_threshold = params.get('threshold')
            if new_threshold and new_threshold > 0:
                self.temp_threshold = new_threshold
                await self.update_config({'temp_threshold': new_threshold})
                return {
                    'status': 'success',
                    'message': f'Temperature threshold updated to {new_threshold}°C'
                }
            return {'status': 'error', 'message': 'Invalid threshold value'}
            
        elif action == 'clear_alerts':
            self.alert_history.clear()
            return {'status': 'success', 'message': 'Alert history cleared'}
            
        elif action == 'test_alert':
            device_ip = params.get('device_ip', '192.168.1.100')
            await self.send_temperature_alert({
                'ip': device_ip,
                'alias': f'Test Device {device_ip}',
                'temperature_c': self.temp_threshold + 10
            })
            return {'status': 'success', 'message': 'Test alert sent'}
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
```

This comprehensive API documentation covers all aspects of plugin development and integration with the Kasa Monitor system. For additional examples and tutorials, see the plugin development guide and example plugins in the repository.