# Power Monitor Example Plugin

This example plugin demonstrates device monitoring capabilities by tracking power consumption and sending alerts when devices exceed configured thresholds.

## Features

- Monitor power consumption for all or selected devices
- Configurable power threshold alerts
- Automatic alert throttling (max 1 alert per hour per device)
- Real-time monitoring via device reading hooks
- Manual threshold updates and testing

## Configuration

The plugin can be configured with the following options:

- **power_threshold**: Power threshold in watts (default: 1000W)
- **check_interval**: Check interval in seconds (default: 60s)  
- **enabled_devices**: List of device IPs to monitor (empty = all devices)

## Installation

1. Copy this directory to the main `plugins/` folder
2. Modify the plugin ID in `manifest.json` if needed
3. Enable the plugin through Admin → Plugins

## Actions

The plugin supports these actions:

- `update_threshold`: Change the power threshold
- `clear_alerts`: Clear alert history  
- `test_alert`: Send a test alert for a device

## Hooks Used

- `device.reading_updated`: Triggered when device data is updated
- `device.discovered`: Triggered when new devices are found

## Hooks Emitted

- `notification.send`: Emits power alert notifications

## Example Usage

```python
# Update threshold to 1500W
await plugin.handle_action('update_threshold', {'threshold': 1500})

# Send test alert
await plugin.handle_action('test_alert', {'device_ip': '192.168.1.100'})

# Clear alert history
await plugin.handle_action('clear_alerts', {})
```

This plugin serves as a foundation for building more sophisticated monitoring and alerting systems.