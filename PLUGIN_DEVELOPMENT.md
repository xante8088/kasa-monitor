# Plugin Development Guide

This guide provides comprehensive instructions for developing plugins for Kasa Monitor.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Plugin Architecture](#plugin-architecture)
3. [Creating Your First Plugin](#creating-your-first-plugin)
4. [Plugin Manifest](#plugin-manifest)
5. [Plugin Base Class](#plugin-base-class)
6. [Hook System](#hook-system)
7. [Configuration Management](#configuration-management)
8. [Database Access](#database-access)
9. [Testing Plugins](#testing-plugins)
10. [Best Practices](#best-practices)
11. [Advanced Features](#advanced-features)
12. [Deployment](#deployment)

## Getting Started

### Prerequisites

- Python 3.8+
- Access to Kasa Monitor installation
- Basic understanding of Python and async/await
- Familiarity with JSON schema

### Development Environment

1. **Clone or access the Kasa Monitor repository**
2. **Navigate to the plugins directory**: `cd plugins/`
3. **Copy the basic template**: `cp -r templates/basic-plugin-template/ my-plugin/`
4. **Start developing**: Edit the template files for your plugin

## Plugin Architecture

Kasa Monitor plugins follow a modular architecture with these key components:

### Plugin Types

- **Device Plugins**: Monitor and control specific device types
- **Integration Plugins**: Connect with external services (Slack, webhooks, etc.)
- **Analytics Plugins**: Process and analyze device data
- **Automation Plugins**: Automate device actions and scheduling
- **Utility Plugins**: Provide helper functionality

### Plugin Lifecycle

1. **Discovery**: Plugin is found in the plugins directory
2. **Loading**: Plugin code is loaded and validated
3. **Initialization**: Plugin's `initialize()` method is called
4. **Running**: Plugin responds to hooks and handles actions
5. **Shutdown**: Plugin's `shutdown()` method is called

### Directory Structure

```
my-plugin/
├── manifest.json          # Plugin metadata and configuration
├── main.py                # Main plugin class
├── requirements.txt       # Python dependencies (optional)
├── config/                # Configuration files (optional)
├── templates/             # Templates for UI components (optional)
├── static/                # Static assets (optional)
└── README.md             # Plugin documentation
```

## Creating Your First Plugin

Let's create a simple device monitor plugin step by step.

### Step 1: Create Plugin Directory

```bash
mkdir plugins/my-device-monitor
cd plugins/my-device-monitor
```

### Step 2: Create Manifest File

Create `manifest.json`:

```json
{
  "id": "my-device-monitor",
  "name": "My Device Monitor",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "A simple device monitoring plugin",
  "plugin_type": "device",
  "main_class": "MyDeviceMonitor",
  "dependencies": [],
  "python_dependencies": [],
  "permissions": [
    "devices.read",
    "notifications.send"
  ],
  "config_schema": {
    "type": "object",
    "properties": {
      "threshold_watts": {
        "type": "number",
        "default": 100,
        "description": "Power threshold for alerts"
      },
      "check_interval": {
        "type": "integer",
        "default": 300,
        "description": "Check interval in seconds"
      }
    }
  },
  "hooks": [
    "device.reading_updated"
  ],
  "api_version": "1.0",
  "min_app_version": "0.3.0"
}
```

### Step 3: Create Main Plugin Class

Create `main.py`:

```python
"""My Device Monitor Plugin."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from plugin_system import PluginBase

logger = logging.getLogger(__name__)


class MyDeviceMonitor(PluginBase):
    """Simple device monitoring plugin."""

    def __init__(self):
        super().__init__()
        self.threshold_watts = 100
        self.check_interval = 300
        self.monitoring_task = None

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            # Load configuration
            config = await self.get_config()
            self.threshold_watts = config.get('threshold_watts', 100)
            self.check_interval = config.get('check_interval', 300)

            # Register hook for device readings
            await self.hook_manager.register_hook(
                'device.reading_updated',
                self.on_device_reading
            )

            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self.monitor_devices())

            logger.info(f"My Device Monitor initialized with {self.threshold_watts}W threshold")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize My Device Monitor: {e}")
            return False

    async def shutdown(self):
        """Shutdown the plugin."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        await self.hook_manager.unregister_hook(
            'device.reading_updated',
            self.on_device_reading
        )

        logger.info("My Device Monitor shutdown complete")

    async def on_device_reading(self, device_data: Dict[str, Any]):
        """Handle device reading updates."""
        device_ip = device_data.get('ip')
        current_power = device_data.get('current_power_w', 0)

        if current_power > self.threshold_watts:
            await self.send_alert(device_data)

    async def send_alert(self, device_data: Dict[str, Any]):
        """Send high power alert."""
        await self.hook_manager.emit_hook('notification.send', {
            'type': 'high_power',
            'severity': 'warning',
            'title': 'High Power Usage',
            'message': f"Device {device_data.get('alias')} using {device_data.get('current_power_w')}W",
            'device_ip': device_data.get('ip')
        })

    async def monitor_devices(self):
        """Background monitoring task."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                # Add custom monitoring logic here
                logger.debug("Monitoring devices...")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get plugin status."""
        return {
            'threshold_watts': self.threshold_watts,
            'check_interval': self.check_interval,
            'monitoring_active': self.monitoring_task and not self.monitoring_task.done()
        }

    async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plugin actions."""
        if action == 'update_threshold':
            new_threshold = params.get('threshold')
            if new_threshold and new_threshold > 0:
                self.threshold_watts = new_threshold
                await self.update_config({'threshold_watts': new_threshold})
                return {'status': 'success', 'message': f'Threshold updated to {new_threshold}W'}
            return {'status': 'error', 'message': 'Invalid threshold value'}
        
        return {'status': 'error', 'message': f'Unknown action: {action}'}
```

### Step 4: Test Your Plugin

1. **Install the plugin**: Copy to `plugins/` directory
2. **Enable via admin panel**: Go to Admin → Plugins
3. **Configure settings**: Click the settings icon
4. **Monitor logs**: Check for initialization messages

## Plugin Manifest

The `manifest.json` file defines plugin metadata and capabilities.

### Required Fields

```json
{
  "id": "unique-plugin-id",           // Unique identifier
  "name": "Human-readable name",      // Display name
  "version": "1.0.0",                 // Semantic version
  "author": "Author Name",            // Plugin author
  "description": "Plugin description", // What the plugin does
  "plugin_type": "device",            // Plugin category
  "main_class": "PluginClassName",    // Main class name
  "api_version": "1.0"                // API version
}
```

### Optional Fields

```json
{
  "dependencies": ["other-plugin-id"],     // Plugin dependencies
  "python_dependencies": ["requests"],     // Python package dependencies
  "permissions": ["devices.read"],         // Required permissions
  "hooks": ["device.reading_updated"],     // Hooks the plugin uses
  "min_app_version": "0.3.0",             // Minimum app version
  "max_app_version": "2.0.0",             // Maximum app version
  "homepage": "https://github.com/...",   // Plugin homepage
  "license": "GPL-3.0",                   // License
  "icon": "🔌",                           // Display icon
  "config_schema": { ... }                // Configuration schema
}
```

### Configuration Schema

Define user-configurable options using JSON Schema:

```json
{
  "config_schema": {
    "type": "object",
    "properties": {
      "api_key": {
        "type": "string",
        "format": "password",
        "description": "API key for external service"
      },
      "enabled_devices": {
        "type": "array",
        "items": {"type": "string"},
        "default": [],
        "description": "List of device IPs to monitor"
      },
      "threshold": {
        "type": "number",
        "minimum": 0,
        "maximum": 10000,
        "default": 100,
        "description": "Power threshold in watts"
      },
      "notifications": {
        "type": "boolean",
        "default": true,
        "description": "Enable notifications"
      }
    },
    "required": ["api_key"]
  }
}
```

## Plugin Base Class

All plugins inherit from `PluginBase` which provides core functionality.

### Required Methods

```python
async def initialize(self) -> bool:
    """Initialize the plugin. Return True on success."""
    pass

async def shutdown(self):
    """Clean up resources when plugin is unloaded."""
    pass
```

### Optional Methods

```python
async def get_status(self) -> Dict[str, Any]:
    """Return current plugin status."""
    return {"status": "running"}

async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle plugin-specific actions."""
    return {"status": "error", "message": "Action not supported"}
```

### Available Properties

```python
self.plugin_id          # Plugin ID from manifest
self.config            # Current plugin configuration
self.db_manager        # Database manager instance
self.hook_manager      # Hook manager instance
```

### Helper Methods

```python
# Configuration management
config = await self.get_config()
await self.update_config({"key": "value"})

# Logging
logger = logging.getLogger(__name__)
logger.info("Plugin started")
```

## Hook System

The hook system enables event-driven communication between plugins and the core system.

### Registering Hooks

```python
# Register to receive events
await self.hook_manager.register_hook('event.name', self.handler_method)

async def handler_method(self, data: Dict[str, Any]):
    """Handle the event."""
    print(f"Received event: {data}")
```

### Emitting Hooks

```python
# Send events to other plugins
await self.hook_manager.emit_hook('notification.send', {
    'type': 'alert',
    'title': 'Device Alert',
    'message': 'Something happened',
    'severity': 'warning'
})
```

### Common Hooks

#### Device Events
- `device.reading_updated`: New device reading available
- `device.status_changed`: Device online/offline status changed
- `device.discovered`: New device discovered
- `device.removed`: Device removed from monitoring

#### System Events
- `system.startup`: System starting up
- `system.shutdown`: System shutting down
- `notification.send`: Send notification
- `analytics.report_requested`: Analytics report requested

#### Plugin Events
- `plugin.loaded`: Plugin was loaded
- `plugin.enabled`: Plugin was enabled
- `plugin.disabled`: Plugin was disabled
- `plugin.configured`: Plugin configuration changed

### Hook Data Examples

```python
# device.reading_updated
{
    "ip": "192.168.1.100",
    "alias": "Living Room Lamp",
    "current_power_w": 75.5,
    "voltage": 120.2,
    "is_on": True,
    "timestamp": "2025-01-01T12:00:00Z"
}

# notification.send
{
    "type": "power_alert",
    "severity": "warning",  # info, warning, error, critical
    "title": "High Power Usage",
    "message": "Device exceeds power threshold",
    "device_ip": "192.168.1.100",
    "timestamp": "2025-01-01T12:00:00Z"
}
```

## Configuration Management

### Loading Configuration

```python
async def initialize(self):
    config = await self.get_config()
    self.api_key = config.get('api_key')
    self.threshold = config.get('threshold', 100)
```

### Updating Configuration

```python
async def handle_action(self, action: str, params: Dict[str, Any]):
    if action == 'update_settings':
        new_config = {
            'threshold': params.get('threshold'),
            'notifications': params.get('notifications', True)
        }
        await self.update_config(new_config)
        return {'status': 'success'}
```

### Configuration Validation

The system automatically validates configuration against the schema defined in `manifest.json`. Invalid configurations will be rejected.

## Database Access

Plugins can access the main application database through `self.db_manager`.

### Common Database Operations

```python
# Get monitored devices
devices = await self.db_manager.get_monitored_devices()

# Get device readings
reading = await self.db_manager.get_latest_device_reading(device_ip)
readings = await self.db_manager.get_device_readings(device_ip, start_time, end_time)

# Get device statistics
stats = await self.db_manager.get_device_stats(device_ip, days=7)
```

### Plugin-Specific Storage

For plugin-specific data, create your own database or files:

```python
import sqlite3
from pathlib import Path

# Create plugin data directory
plugin_data_dir = Path("./plugins/data/my-plugin")
plugin_data_dir.mkdir(parents=True, exist_ok=True)

# Use SQLite for structured data
db_path = plugin_data_dir / "plugin_data.db"
conn = sqlite3.connect(str(db_path))

# Or use JSON files for simple data
config_file = plugin_data_dir / "config.json"
with open(config_file, 'w') as f:
    json.dump(data, f)
```

## Testing Plugins

### Unit Testing

Create test files in your plugin directory:

```python
# test_my_plugin.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from main import MyDeviceMonitor

@pytest.fixture
async def plugin():
    plugin = MyDeviceMonitor()
    plugin.hook_manager = AsyncMock()
    plugin.db_manager = AsyncMock()
    return plugin

@pytest.mark.asyncio
async def test_initialization(plugin):
    plugin.get_config = AsyncMock(return_value={'threshold_watts': 150})
    result = await plugin.initialize()
    assert result is True
    assert plugin.threshold_watts == 150

@pytest.mark.asyncio
async def test_device_reading_handler(plugin):
    device_data = {
        'ip': '192.168.1.100',
        'current_power_w': 200,
        'alias': 'Test Device'
    }
    
    plugin.threshold_watts = 100
    plugin.send_alert = AsyncMock()
    
    await plugin.on_device_reading(device_data)
    plugin.send_alert.assert_called_once_with(device_data)
```

### Integration Testing

Test with the actual plugin system:

```python
# integration_test.py
import asyncio
from plugin_system import PluginLoader

async def test_plugin_loading():
    loader = PluginLoader("./plugins")
    await loader.load_plugin("my-device-monitor")
    
    plugin = loader.get_plugin("my-device-monitor")
    assert plugin is not None
    assert plugin.state == "running"
```

### Manual Testing

1. **Install plugin** in development environment
2. **Enable through admin panel**
3. **Check logs** for errors or warnings
4. **Test configuration** changes
5. **Verify hook interactions**
6. **Test error conditions**

## Best Practices

### Code Quality

1. **Use async/await**: All plugin methods should be async-compatible
2. **Handle exceptions**: Wrap operations in try/except blocks
3. **Log appropriately**: Use proper log levels (debug, info, warning, error)
4. **Validate inputs**: Check parameters and configuration values
5. **Resource cleanup**: Properly clean up in the shutdown method

### Performance

1. **Avoid blocking operations**: Use async alternatives
2. **Limit resource usage**: Monitor memory and CPU usage
3. **Batch operations**: Group database or API calls when possible
4. **Use caching**: Cache frequently accessed data
5. **Background tasks**: Use asyncio tasks for long-running operations

### Security

1. **Validate permissions**: Check required permissions are granted
2. **Sanitize inputs**: Validate and sanitize all user inputs
3. **Secure credentials**: Use secure storage for sensitive data
4. **Limit access**: Only request necessary permissions
5. **Audit trail**: Log security-relevant actions

### Compatibility

1. **Version pinning**: Specify compatible app versions
2. **Graceful degradation**: Handle missing features gracefully
3. **API compatibility**: Use stable API endpoints
4. **Dependency management**: Minimize external dependencies
5. **Documentation**: Keep README and comments up to date

## Advanced Features

### Background Tasks

```python
class MyPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.background_tasks = []

    async def initialize(self):
        # Start background tasks
        task = asyncio.create_task(self.periodic_task())
        self.background_tasks.append(task)
        return True

    async def shutdown(self):
        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def periodic_task(self):
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self.do_periodic_work()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic task: {e}")
```

### External API Integration

```python
import aiohttp

class APIIntegrationPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.session = None

    async def initialize(self):
        self.session = aiohttp.ClientSession()
        return True

    async def shutdown(self):
        if self.session:
            await self.session.close()

    async def call_external_api(self, data):
        async with self.session.post('https://api.example.com/webhook', json=data) as response:
            return await response.json()
```

### Custom Web Endpoints

```python
from fastapi import APIRouter

class WebEndpointPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.router = APIRouter()
        self.setup_routes()

    def setup_routes(self):
        @self.router.get("/status")
        async def get_plugin_status():
            return await self.get_status()

        @self.router.post("/action")
        async def perform_action(action_data: dict):
            return await self.handle_action(action_data['action'], action_data.get('params', {}))

    async def get_router(self):
        """Return FastAPI router for integration."""
        return self.router
```

### Data Processing Pipelines

```python
class DataProcessorPlugin(PluginBase):
    async def on_device_reading(self, device_data):
        # Process data through pipeline
        processed_data = await self.process_pipeline(device_data)
        
        # Emit processed data
        await self.hook_manager.emit_hook('data.processed', processed_data)

    async def process_pipeline(self, data):
        # Step 1: Validate data
        validated_data = await self.validate_data(data)
        
        # Step 2: Transform data
        transformed_data = await self.transform_data(validated_data)
        
        # Step 3: Enrich data
        enriched_data = await self.enrich_data(transformed_data)
        
        return enriched_data
```

## Deployment

### Packaging

Create a ZIP file containing your plugin:

```bash
cd plugins/my-plugin
zip -r my-plugin-v1.0.0.zip . -x "*.pyc" "__pycache__/*" ".git/*"
```

### Installation Methods

1. **Admin Panel Upload**: Use the web interface to upload ZIP files
2. **Direct Copy**: Copy plugin directory to `plugins/` folder
3. **Git Clone**: Clone from repository into plugins directory

### Distribution

1. **GitHub Releases**: Create releases with ZIP attachments
2. **Plugin Registry**: Submit to official plugin registry (future)
3. **Documentation**: Include installation instructions

### Versioning

Follow semantic versioning (SemVer):

- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backwards compatible
- **Patch** (0.0.1): Bug fixes, backwards compatible

## Troubleshooting

### Common Issues

1. **Plugin won't load**
   - Check manifest.json syntax
   - Verify main_class name matches actual class
   - Check Python syntax errors
   - Review required permissions

2. **Configuration errors**
   - Validate config_schema syntax
   - Check required fields are provided
   - Verify data types match schema

3. **Hook registration fails**
   - Ensure hook names are correct
   - Check if permissions allow hook usage
   - Verify handler method signature

4. **Performance issues**
   - Profile plugin resource usage
   - Check for blocking operations
   - Review background task implementation

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def initialize(self):
    logger.debug("Starting plugin initialization")
    # ... initialization code
    logger.debug("Plugin initialization complete")
```

Check plugin logs in the admin panel or system logs.

## Examples

See the `plugins/examples/` directory for complete working examples:

- **power-monitor**: Device monitoring with alerts
- **slack-alerts**: External service integration
- **usage-analytics**: Data processing and analytics

Each example includes full source code, documentation, and configuration examples.

## API Reference

For detailed API documentation, see [PLUGIN_API.md](PLUGIN_API.md).

## Community

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Wiki**: Community-maintained documentation
- **Discord**: Real-time chat and support

## License

Plugins should be compatible with Kasa Monitor's GPL-3.0 license. Include appropriate license headers in your code.

---

This guide covers the essentials of plugin development for Kasa Monitor. For more advanced topics and API details, refer to the additional documentation and example plugins.