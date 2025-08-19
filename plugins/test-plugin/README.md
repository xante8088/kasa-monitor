# Test Plugin

A simple test plugin for demonstrating and verifying the Kasa Monitor plugin system functionality.

## Features

- Device discovery monitoring
- Data collection logging
- Configurable log levels
- Email notification support (configuration only)
- Plugin metrics and status reporting

## Configuration

The plugin supports the following configuration options:

- **enabled** (boolean): Enable or disable the plugin (default: true)
- **log_level** (string): Set logging level - debug, info, warning, error (default: info)
- **notification_email** (string): Email address for notifications (optional)

## Hooks

The plugin registers for the following hooks:

- `device_discovered`: Called when a new device is discovered
- `data_collected`: Called when device data is collected

## Permissions

The plugin requires the following permissions:

- `device_access`: Access to device information
- `database_read`: Read access to the database

## Installation

1. Package the plugin files into a ZIP archive
2. Upload via the Kasa Monitor plugin management interface
3. Configure the plugin settings as needed
4. Enable the plugin to start monitoring

## Testing

This plugin is designed for testing the plugin system and can be safely installed and removed without affecting system functionality.