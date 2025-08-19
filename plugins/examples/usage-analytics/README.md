# Usage Analytics Example Plugin

This example plugin demonstrates analytics capabilities by tracking device usage patterns, calculating efficiency metrics, and generating insights about power consumption.

## Features

- Real-time usage pattern analysis
- Efficiency scoring and recommendations
- Daily usage summaries and reports
- Power consumption trend analysis
- Configurable analysis intervals and data retention
- Multiple report types (usage, efficiency, patterns)

## Analytics Capabilities

### Usage Pattern Detection
- **Steady**: Consistent power usage
- **Variable**: Moderate power fluctuations
- **Spiky**: High power variations
- **Idle**: Below threshold usage

### Efficiency Metrics
- Average power efficiency scores
- Peak vs average power ratios
- Active vs inactive time analysis
- Energy consumption optimization

### Report Types
- **Usage Summary**: Power and energy statistics
- **Efficiency Analysis**: Performance insights
- **Pattern Analysis**: Temporal usage patterns
- **General Summary**: Combined overview with recommendations

## Configuration

- **analysis_interval**: Analysis frequency in seconds (default: 3600s)
- **retention_days**: Data retention period (default: 30 days)
- **min_usage_threshold**: Minimum watts to consider "active" (default: 10W)
- **generate_reports**: Enable automatic daily reports (default: true)

## Dependencies

The plugin requires additional Python packages:

```bash
pip install pandas>=1.5.0 numpy>=1.21.0
```

## Installation

1. Install required dependencies
2. Copy this directory to the main `plugins/` folder
3. Configure analysis settings as needed
4. Enable the plugin through Admin → Plugins

## Database Schema

The plugin creates its own analytics database with tables:

- **device_analytics**: Hourly analysis results
- **daily_summaries**: Daily aggregated reports

## Actions

The plugin supports these actions:

- `generate_report`: Create specific analytics reports
- `cleanup_data`: Remove old analytics data
- `run_analysis`: Trigger manual analysis

## Hooks Used

- `device.reading_updated`: Processes device power readings
- `analytics.report_requested`: Handles report generation requests

## Hooks Emitted

- `analytics.report_generated`: Emits completed reports

## Example Usage

```python
# Generate usage summary for specific device
await plugin.handle_action('generate_report', {
    'type': 'usage_summary',
    'device_ip': '192.168.1.100',
    'days': 7
})

# Generate efficiency analysis for all devices
await plugin.handle_action('generate_report', {
    'type': 'efficiency_analysis',
    'days': 30
})

# Manual cleanup of old data
await plugin.handle_action('cleanup_data', {})

# Trigger immediate analysis
await plugin.handle_action('run_analysis', {})
```

## Data Privacy

- All analytics data is stored locally
- No external data transmission
- Configurable data retention periods
- Secure local database storage

## Performance Considerations

- Analysis runs on configurable intervals
- Automatic cleanup of old data
- Efficient database indexing
- Memory-conscious data processing

This plugin provides a foundation for building sophisticated analytics and reporting systems while demonstrating best practices for data processing and storage.