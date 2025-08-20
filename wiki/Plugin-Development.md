# Plugin Development

Guide for developing basic plugins for Kasa Monitor.

> **Note**: The plugin system is currently in early development. This documentation covers the basic framework that is implemented. Advanced features mentioned in roadmap are planned for future releases.

## Overview

Kasa Monitor supports a basic plugin system that allows extending functionality through custom Python modules. The current implementation provides:

- Plugin discovery and loading
- Basic lifecycle management (enable/disable)
- Simple hook system for device events
- Configuration management

## Getting Started

### Plugin Structure

```
my-plugin/
├── manifest.json    # Plugin metadata (required)
├── main.py         # Main plugin code (required)
└── README.md       # Plugin documentation
```

### Manifest File

Every plugin must have a `manifest.json` file:

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "A simple plugin for Kasa Monitor",
  "plugin_type": "utility",
  "main_class": "MyPlugin",
  "api_version": "1.0",
  "permissions": ["devices.read"],
  "hooks": ["device.discovered", "device.data.received"]
}
```

### Basic Plugin Implementation

Create a `main.py` file with your plugin class:

```python
from plugin_system import BasePlugin

class MyPlugin(BasePlugin):
    """Simple plugin example."""
    
    def __init__(self):
        super().__init__()
        self.name = "My Plugin"
        
    async def initialize(self):
        """Initialize plugin resources."""
        self.logger.info(f"{self.name} initialized")
        return True
        
    async def shutdown(self):
        """Clean up plugin resources."""
        self.logger.info(f"{self.name} shutting down")
        
    async def on_device_discovered(self, device_ip: str, device_info: dict):
        """Handle device discovery event."""
        self.logger.info(f"New device discovered: {device_ip}")
        
    async def on_device_data_received(self, device_ip: str, data: dict):
        """Handle device data updates."""
        power = data.get('power_w', 0)
        if power > 100:
            self.logger.warning(f"High power usage on {device_ip}: {power}W")
```

## Available Plugin Types

The current implementation supports these plugin types:

- **device** - Device-specific functionality
- **integration** - Third-party service integration
- **automation** - Automation rules
- **utility** - General utilities

## Example Plugins

Several example plugins are provided in `/plugins/examples/`:

### Power Monitor Plugin
Monitors power consumption and alerts on high usage:

```python
class PowerMonitorPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.threshold = 150  # Watts
        
    async def on_device_data_received(self, device_ip: str, data: dict):
        power = data.get('power_w', 0)
        if power > self.threshold:
            await self.send_alert(f"High power: {power}W on {device_ip}")
```

### Slack Alerts Plugin
Sends notifications to Slack (requires configuration):

```python
class SlackAlertsPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.webhook_url = self.config.get('webhook_url')
        
    async def send_slack_message(self, message: str):
        # Send message to Slack webhook
        pass
```

## Plugin Installation

1. **Manual Installation**:
   - Place plugin folder in `/plugins/` directory
   - Restart Kasa Monitor

2. **Enable Plugin**:
   - Plugins are auto-discovered on startup
   - Use the admin interface to enable/disable plugins

## Available Hooks

Current implementation provides these hooks:

| Hook | Description | Parameters |
|------|-------------|------------|
| `device.discovered` | New device found | `device_ip`, `device_info` |
| `device.data.received` | Device data update | `device_ip`, `data` |
| `device.connected` | Device comes online | `device_ip` |
| `device.disconnected` | Device goes offline | `device_ip` |

## Plugin Configuration

Plugins can have configuration that's stored in the database:

```python
class ConfigurablePlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        # Access configuration
        self.setting = self.config.get('my_setting', 'default_value')
```

Configuration schema can be defined in manifest.json:

```json
{
  "config_schema": {
    "my_setting": {
      "type": "string",
      "default": "default_value",
      "description": "A configuration setting"
    }
  }
}
```

## Limitations

The current plugin system has these limitations:

- No UI component integration
- No custom API endpoint registration
- Limited hook system (basic events only)
- No plugin marketplace or automatic updates
- No sandboxing or security isolation
- Python-only (no JavaScript/TypeScript support)

## Plugin Development Tips

1. **Keep it Simple**: Start with basic functionality
2. **Use Async**: All plugin methods should be async
3. **Handle Errors**: Wrap operations in try/except blocks
4. **Log Appropriately**: Use self.logger for debugging
5. **Test Thoroughly**: Test with various device types

## Plugin Template

A basic template is provided in `/plugins/templates/basic-plugin-template/`:

```bash
# Copy template to start new plugin
cp -r plugins/templates/basic-plugin-template plugins/my-new-plugin
```

## Future Roadmap

The following features are planned but **not yet implemented**:

- **Advanced Hook System**: More granular event hooks
- **UI Extensions**: Dashboard widgets and custom pages
- **API Extensions**: Register custom API endpoints
- **Plugin Marketplace**: Browse and install community plugins
- **Dependency Management**: Automatic dependency installation
- **Security Sandboxing**: Isolated plugin execution
- **Plugin Packaging**: .kplugin package format
- **Hot Reload**: Load/unload plugins without restart
- **Cross-plugin Communication**: Plugin-to-plugin messaging
- **Scheduled Tasks**: Cron-like task scheduling

## Debugging Plugins

Enable debug logging to troubleshoot plugins:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check plugin state in the database:
```sql
SELECT * FROM plugins WHERE plugin_id = 'my-plugin';
```

## Support

- Check example plugins in `/plugins/examples/`
- Review the base plugin implementation in `backend/plugin_system.py`
- For bugs or feature requests, open a GitHub issue

---

*Note: This documentation reflects the current basic implementation. Many advanced features are planned for future releases. For production use, thoroughly test plugins in your environment.*