# Basic Plugin Template

This is a basic template for creating new Kasa Monitor plugins. Use this as a starting point for developing your own plugins.

## Getting Started

1. **Copy the template**: Copy this entire directory to create your new plugin
2. **Update manifest.json**: Change the plugin ID, name, description, and other metadata
3. **Rename the class**: Update the class name in `main.py` and the `main_class` in manifest.json
4. **Implement your logic**: Add your plugin functionality to the template methods
5. **Test your plugin**: Enable it through the admin interface and test functionality

## Template Structure

### manifest.json
- Contains plugin metadata and configuration
- Update all fields to match your plugin
- Define permissions, hooks, and configuration schema

### main.py
- Contains the main plugin class
- Inherits from `PluginBase`
- Implements required lifecycle methods

## Required Methods

### `async def initialize(self) -> bool`
- Called when plugin is loaded
- Load configuration, register hooks, start tasks
- Return `True` on success, `False` on failure

### `async def shutdown(self)`
- Called when plugin is unloaded
- Clean up resources, unregister hooks, stop tasks

## Optional Methods

### `async def get_status(self) -> Dict[str, Any]`
- Return current plugin status
- Used for monitoring and debugging

### `async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]`
- Handle plugin-specific actions
- Called from API or other plugins

## Hook System

### Registering Hooks
```python
await self.hook_manager.register_hook('event.name', self.handler_method)
```

### Emitting Hooks
```python
await self.hook_manager.emit_hook('event.name', data)
```

### Common Hooks
- `device.reading_updated`: Device data updates
- `device.status_changed`: Device online/offline
- `device.discovered`: New device found
- `notification.send`: Send notifications

## Configuration

Access plugin configuration:
```python
config = await self.get_config()
setting = config.get('setting_name', 'default_value')
```

Update configuration:
```python
await self.update_config({'setting_name': 'new_value'})
```

## Database Access

Access the main database:
```python
devices = await self.db_manager.get_monitored_devices()
reading = await self.db_manager.get_latest_device_reading(device_ip)
```

## Logging

Use the logger for debugging:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Plugin started")
logger.error(f"Error occurred: {e}")
```

## Best Practices

1. **Error Handling**: Always wrap operations in try/except blocks
2. **Resource Cleanup**: Properly clean up in shutdown method
3. **Configuration**: Use config schema for validation
4. **Logging**: Use appropriate log levels
5. **Performance**: Avoid blocking operations
6. **Security**: Validate all inputs and permissions

## Plugin Types

- **device**: Monitor and control devices
- **integration**: Connect with external services
- **analytics**: Process and analyze data
- **automation**: Automate device actions
- **utility**: Provide helper functionality

## Testing

1. Copy plugin to plugins directory
2. Enable through Admin → Plugins
3. Check logs for initialization
4. Test actions and hooks
5. Monitor performance and errors

## Example Customizations

### Add Background Task
```python
self.background_task = asyncio.create_task(self.background_loop())
```

### Handle Multiple Hooks
```python
await self.hook_manager.register_hook('device.reading_updated', self.on_reading)
await self.hook_manager.register_hook('device.discovered', self.on_discovery)
```

### Store Plugin Data
```python
# Create plugin-specific database or files
plugin_data_dir = Path("./plugins/data/my-plugin")
plugin_data_dir.mkdir(parents=True, exist_ok=True)
```

This template provides a solid foundation for plugin development while following Kasa Monitor's plugin architecture and best practices.