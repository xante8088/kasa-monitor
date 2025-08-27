# Time Period Selection Guide

Complete guide to using the time period selection feature introduced in Kasa Monitor v1.2.1.

## Overview

The time period selection feature allows you to customize the time range for each chart independently, providing flexible data visualization and analysis capabilities.

## Available Time Periods

### Predefined Periods
- **Last 24 Hours** - High-resolution 5-minute intervals
- **Last 7 Days** - Hourly data points
- **Last 30 Days** - 6-hour intervals
- **Last 3 Months** - Daily aggregation
- **Last 6 Months** - Daily aggregation
- **Last Year** - Weekly aggregation
- **Custom Range** - User-defined start and end dates

## Using Time Period Selectors

### Basic Usage

1. **Navigate to Device Details**
   - Click on any device card
   - Select "View Details" or click the device name

2. **Locate Time Period Selector**
   - Each chart has a dropdown selector in the top-right corner
   - Default selection is "Last 24 Hours"

3. **Select Time Period**
   - Click the dropdown
   - Choose desired time period
   - Chart updates automatically

### Custom Date Range

1. **Select "Custom Range"** from dropdown
2. **Choose dates:**
   ```
   Start Date: [Calendar Picker]
   End Date: [Calendar Picker]
   ```
3. **Click "Apply"**
4. **Data loads for selected range**

## Intelligent Data Aggregation

### Automatic Aggregation

The system automatically determines the optimal data aggregation based on the selected period:

| Period | Aggregation | Data Points | Update Frequency |
|--------|------------|-------------|------------------|
| 24 Hours | 5 minutes | ~288 | Real-time |
| 7 Days | 1 hour | ~168 | Every 5 minutes |
| 30 Days | 6 hours | ~120 | Every 15 minutes |
| 3 Months | 1 day | ~90 | Every hour |
| 6 Months | 1 day | ~180 | Every hour |
| 1 Year | 1 week | ~52 | Daily |

### Manual Aggregation Control

For advanced users, you can override automatic aggregation via API:

```javascript
// API call with custom aggregation
fetch(`/api/device/${deviceIp}/history?period=30d&aggregation=hourly`)
```

Available aggregation levels:
- `raw` - No aggregation (warning: large datasets)
- `5m` - 5-minute intervals
- `hourly` - Hourly averages
- `daily` - Daily totals
- `weekly` - Weekly summaries
- `monthly` - Monthly aggregates

## Chart-Specific Features

### Power Consumption Chart

**Time Period Behavior:**
- Short periods (24h-7d): Shows instantaneous power readings
- Medium periods (30d-3m): Shows average power consumption
- Long periods (6m-1y): Shows peak and average values

**Data Display:**
```
24 Hours: Line chart with 5-minute resolution
7 Days: Line chart with hourly averages
30+ Days: Area chart with min/max ranges
```

### Energy Usage Chart

**Time Period Behavior:**
- Displays cumulative energy consumption (kWh)
- Automatically adjusts units (Wh, kWh, MWh)
- Shows total consumption for period

**Calculations:**
```
Daily Total = Sum of all readings in 24h period
Weekly Total = Sum of daily totals
Monthly Total = Sum of all readings in month
```

### Cost Analysis Chart

**Time Period Behavior:**
- Applies rate structure based on time period
- Includes time-of-use rates if configured
- Shows projected costs for incomplete periods

**Cost Calculation:**
```javascript
// Period-based cost calculation
if (period <= '7d') {
  // Use hourly rates
  cost = energy_kwh * hourly_rate
} else if (period <= '30d') {
  // Apply tiered rates
  cost = calculateTieredRate(energy_kwh)
} else {
  // Use monthly billing cycles
  cost = calculateMonthlyBilling(energy_kwh)
}
```

## Performance Optimization

### Data Caching

**Cache Duration by Period:**
- 24 Hours: 5 minutes
- 7 Days: 15 minutes
- 30 Days: 1 hour
- 3+ Months: 6 hours

**Cache Invalidation:**
- New data automatically invalidates cache
- Manual refresh available via refresh button
- Cache cleared on device configuration changes

### Loading States

**Progressive Loading:**
1. Initial skeleton display
2. Cached data loads (if available)
3. Fresh data fetched in background
4. Chart updates seamlessly

### Memory Management

**Best Practices:**
- Avoid rapidly switching between periods
- Use shorter periods for real-time monitoring
- Use longer periods for trend analysis
- Close unused device detail views

## Common Use Cases

### Daily Monitoring
```
Period: Last 24 Hours
Purpose: Track real-time consumption
Charts: Power, Current Status
Refresh: Every 5 minutes
```

### Weekly Analysis
```
Period: Last 7 Days
Purpose: Identify usage patterns
Charts: Energy, Cost, Power
Export: Weekly report
```

### Monthly Billing
```
Period: Last 30 Days
Purpose: Estimate monthly costs
Charts: Cost Analysis, Energy Total
Compare: Previous month
```

### Seasonal Trends
```
Period: Last 6 Months
Purpose: Identify seasonal patterns
Charts: All charts
Export: Seasonal analysis
```

### Annual Review
```
Period: Last Year
Purpose: Year-over-year comparison
Charts: Energy, Cost trends
Report: Annual summary
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `1` | Select 24 Hours |
| `7` | Select 7 Days |
| `3` `0` | Select 30 Days |
| `c` | Open Custom Range |
| `r` | Refresh Current Period |
| `e` | Export Current View |

## API Integration

### Fetching Period Data

```python
import requests

# Get data for last 7 days
response = requests.get(
    f"http://localhost:5272/api/device/{device_ip}/history",
    params={
        "period": "7d",
        "aggregation": "auto",
        "timezone": "America/New_York"
    },
    headers={"Authorization": f"Bearer {token}"}
)

data = response.json()
print(f"Data points: {data['metadata']['count']}")
print(f"Aggregation used: {data['metadata']['aggregation']}")
```

### Custom Period Query

```javascript
// Custom date range
const startDate = new Date('2024-01-01');
const endDate = new Date('2024-01-31');

const response = await fetch(
  `/api/device/${deviceIp}/history?` +
  `start_time=${startDate.toISOString()}&` +
  `end_time=${endDate.toISOString()}&` +
  `aggregation=daily`,
  {
    headers: { 'Authorization': `Bearer ${token}` }
  }
);
```

## Troubleshooting

### Charts Not Updating

**Check:**
1. Network connection
2. Valid authentication token
3. Browser console for errors
4. API response in network tab

**Solution:**
```javascript
// Force refresh
localStorage.removeItem(`chart_cache_${deviceIp}`);
location.reload();
```

### Incorrect Aggregation

**Issue:** Data appears too granular or too aggregated

**Solution:**
```javascript
// Override automatic aggregation
const customAggregation = {
  '24h': '1m',    // 1-minute intervals
  '7d': '30m',    // 30-minute intervals
  '30d': '1h',    // Hourly
  '3m': '6h',     // 6-hour intervals
  '6m': '1d',     // Daily
  '1y': '1w'      // Weekly
};
```

### Memory Issues

**Symptoms:** Browser becomes slow with multiple charts

**Solutions:**
1. Limit open device detail views to 3-4
2. Use shorter time periods for multiple devices
3. Enable hardware acceleration in browser
4. Clear browser cache periodically

## Best Practices

### For Users

1. **Start with shorter periods** for real-time monitoring
2. **Use longer periods** for trend analysis
3. **Export data** before switching periods if needed
4. **Compare periods** using multiple browser tabs
5. **Set up alerts** for anomalies in specific periods

### For Administrators

1. **Configure optimal aggregation** settings
2. **Set cache policies** based on system resources
3. **Monitor API usage** for period queries
4. **Educate users** on efficient period selection
5. **Schedule maintenance** during low-usage periods

## Related Documentation

- [API Documentation](API-Documentation) - Technical API reference
- [Device Management](Device-Management) - Device configuration
- [Performance Tuning](Performance-Tuning) - Optimization guide
- [Troubleshooting Guide](Troubleshooting-Guide) - Common issues

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-27  
**Review Status:** Current  
**Change Summary:** Initial documentation for time period selection feature in v1.2.1