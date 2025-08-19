# Slack Alerts Example Plugin

This example plugin demonstrates integration capabilities by sending device alerts and notifications to Slack channels using webhook integration.

## Features

- Send device alerts to Slack channels
- Configurable alert types and formatting
- Device status change notifications
- New device discovery alerts
- Custom message formatting with colors and emojis
- Test message functionality

## Setup

### 1. Create Slack Webhook

1. Go to your Slack workspace settings
2. Navigate to "Apps" → "Incoming WebHooks"
3. Create a new webhook for your desired channel
4. Copy the webhook URL

### 2. Configure Plugin

Set the following configuration options:

- **webhook_url**: Your Slack webhook URL (required)
- **channel**: Slack channel to send messages to (default: #kasa-monitor)
- **username**: Bot username for messages (default: Kasa Monitor)
- **emoji**: Bot emoji (default: :electric_plug:)
- **alert_types**: Array of alert types to send (default: all types)

## Alert Types

- `power_alert`: High power consumption alerts
- `device_offline`: Device disconnection alerts
- `device_online`: Device reconnection alerts
- Custom alert types from other plugins

## Installation

1. Copy this directory to the main `plugins/` folder
2. Install dependencies: `pip install aiohttp>=3.8.0`
3. Configure your Slack webhook URL
4. Enable the plugin through Admin → Plugins

## Actions

The plugin supports these actions:

- `test_message`: Send a test message to Slack
- `update_config`: Update plugin configuration
- `send_summary`: Send device status summary

## Hooks Used

- `notification.send`: Receives notifications from other plugins
- `device.status_changed`: Monitors device online/offline status
- `device.discovered`: Notified when new devices are found

## Message Format

Slack messages include:
- Colored attachments based on severity
- Device information and timestamps
- Formatted text with emojis and markdown
- Custom fields for structured data

## Example Usage

```python
# Send test message
await plugin.handle_action('test_message', {
    'message': 'Testing Slack integration'
})

# Update configuration
await plugin.handle_action('update_config', {
    'config': {
        'channel': '#alerts',
        'alert_types': ['power_alert', 'device_offline']
    }
})

# Send device summary
await plugin.handle_action('send_summary', {})
```

## Security

- Webhook URLs should be kept secure
- Consider using environment variables for sensitive config
- Limit alert types to reduce notification noise
- Monitor message rate limits in Slack

This plugin demonstrates how to integrate Kasa Monitor with external services and provides a foundation for building more sophisticated notification systems.