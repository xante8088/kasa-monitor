# Energy Monitoring

Comprehensive guide to tracking and analyzing energy consumption with Kasa Monitor.

## Understanding Energy Metrics

### Key Terms

- **Power (W)**: Instantaneous consumption in Watts
- **Energy (kWh)**: Total consumption over time (kilowatt-hours)
- **Voltage (V)**: Electrical pressure (typically 110-240V)
- **Current (A)**: Electrical flow in Amperes
- **Power Factor**: Efficiency of power usage (0-1)

### Measurement Accuracy

Device accuracy varies by model:

| Model | Power Accuracy | Energy Accuracy | Measures |
|-------|---------------|-----------------|----------|
| HS110 | ±1% | ±2% | W, kWh, V, A |
| KP115 | ±1% | ±1.5% | W, kWh, V, A, PF |
| KP125 | ±0.5% | ±1% | W, kWh, V, A, PF |
| HS105 | N/A | N/A | On/off only |

## Real-Time Monitoring

### Dashboard View

Each device card shows:
- **Current Power**: Live consumption (updates every 60s)
- **Status Indicator**: 🟢 On / ⚫ Off / 🔴 Offline
- **Daily Total**: Today's energy usage
- **Trend Arrow**: ↑ Increasing / ↓ Decreasing / → Stable

### Detail View

Click any device for expanded metrics:

```
┌──────────────────────────────────┐
│ Living Room Lamp                 │
│ Currently: ON                     │
├──────────────────────────────────┤
│ Power:     45.2 W                │
│ Voltage:   120.1 V               │
│ Current:   0.38 A                │
│ PF:        0.99                  │
├──────────────────────────────────┤
│ Today:     0.543 kWh             │
│ This Week: 3.801 kWh             │
│ This Month: 16.234 kWh           │
└──────────────────────────────────┘
```

### Live Graph

Real-time power graph features:
- **Update Rate**: Every 60 seconds
- **Time Window**: Last 24 hours default
- **Zoom**: Pinch or scroll to zoom
- **Pan**: Drag to move through time

## Historical Data

### Time Ranges

Select predefined ranges:
- Last 24 hours
- Last 7 days
- Last 30 days
- Last 12 months
- Custom range

### Graph Types

#### Power Over Time
Shows instantaneous power consumption:
- **Use Case**: Identify usage patterns
- **Resolution**: 1-minute to 1-hour intervals
- **Export**: CSV, PNG, JSON

#### Energy Accumulation
Shows cumulative energy usage:
- **Use Case**: Track total consumption
- **Resolution**: Hourly, daily, monthly
- **Export**: CSV, Excel

#### Cost Analysis
Shows associated costs:
- **Use Case**: Budget tracking
- **Resolution**: Daily, weekly, monthly
- **Export**: CSV, PDF report

### Data Resolution

| Time Range | Default Resolution | Storage |
|------------|-------------------|---------|
| < 24 hours | 1 minute | Raw data |
| 1-7 days | 5 minutes | Averaged |
| 7-30 days | 1 hour | Averaged |
| > 30 days | 1 day | Aggregated |

## Usage Patterns

### Daily Patterns

Identify consumption patterns:

```
Peak Hours:   6-9 AM, 5-10 PM
Off-Peak:     11 PM - 6 AM
Baseline:     2 AM - 5 AM (minimum load)
```

### Weekly Trends

Compare weekday vs weekend usage:
- **Weekdays**: Higher morning/evening peaks
- **Weekends**: More distributed usage
- **Patterns**: Identify routine changes

### Monthly Analysis

Track seasonal variations:
- Summer: Higher cooling loads
- Winter: Higher heating loads
- Holidays: Irregular patterns

## Device Categories

### Always-On Devices

Devices that run 24/7:
- Refrigerators
- Routers/modems
- Security systems
- Smart hubs

**Monitoring Tips**:
- Check baseline consumption
- Identify efficiency degradation
- Calculate monthly cost

### Scheduled Devices

Devices with regular patterns:
- Coffee makers
- Water heaters
- Pool pumps
- Irrigation

**Monitoring Tips**:
- Verify schedule efficiency
- Optimize run times
- Check for overruns

### On-Demand Devices

User-activated devices:
- TVs/entertainment
- Computers
- Lights
- Kitchen appliances

**Monitoring Tips**:
- Track usage habits
- Identify waste
- Set reminders

### Standby Power

Phantom/vampire loads:
- Device chargers
- TVs in standby
- Computer peripherals
- Smart speakers

**Monitoring Tips**:
- Measure standby consumption
- Calculate annual waste
- Consider smart strips

## Analytics & Insights

### Consumption Rankings

Top consumers by:
1. **Total Energy**: Highest kWh users
2. **Cost**: Most expensive devices
3. **Runtime**: Longest running
4. **Peak Power**: Highest wattage

### Efficiency Metrics

Calculate device efficiency:

```
Efficiency Score = Useful Output / Energy Input
Cost per Hour = (Power in kW) × (Rate per kWh)
Daily Average = Total kWh / Days Monitored
```

### Anomaly Detection

Identify unusual patterns:
- Sudden consumption increase
- Device always on when usually off
- Power spikes beyond normal
- Offline periods

### Comparative Analysis

Compare devices:
- Similar devices in different rooms
- Before/after equipment changes
- Year-over-year usage
- Against manufacturer specs

## Reports & Exports

### Standard Reports

#### Daily Summary
```
Date: 2024-01-15
Total Consumption: 24.5 kWh
Total Cost: $2.94
Peak Demand: 3.2 kW @ 18:30
Devices Active: 12 of 15
```

#### Monthly Report
- Total consumption graph
- Cost breakdown by device
- Peak demand days
- Efficiency trends
- Year-over-year comparison

### Custom Reports

Create custom reports with:
- Selected devices
- Specific metrics
- Custom date ranges
- Grouping options

### Export Formats

| Format | Use Case | Contents |
|--------|----------|----------|
| CSV | Spreadsheet analysis | Raw data |
| Excel | Formatted reports | Charts included |
| PDF | Sharing/archiving | Full formatting |
| JSON | API integration | Structured data |
| PNG | Quick sharing | Graph images |

## Optimization Tips

### Reduce Consumption

1. **Identify Waste**
   - Devices left on unnecessarily
   - Inefficient equipment
   - Standby power drains

2. **Optimize Schedules**
   - Shift to off-peak hours
   - Reduce runtime
   - Combine operations

3. **Replace Inefficient Devices**
   - Compare similar devices
   - Calculate ROI for upgrades
   - Monitor improvements

### Peak Shaving

Reduce peak demand charges:
1. Identify peak hours
2. Stagger device usage
3. Set load limits
4. Automate load shedding

### Load Balancing

Distribute power usage:
- Avoid simultaneous starts
- Sequence high-power devices
- Use scheduling features
- Monitor total load

## Advanced Features

### Baseline Establishment

Set consumption baselines:
1. Monitor for 30 days
2. Calculate averages
3. Set normal ranges
4. Enable alerts for deviations

### Predictive Analysis

Forecast future usage:
- Based on historical patterns
- Weather correlation
- Seasonal adjustments
- Growth trends

### Integration Options

Connect with other systems:
- **Home Assistant**: Via API
- **InfluxDB**: Time-series storage
- **Grafana**: Advanced visualization
- **Excel**: Direct export

### Machine Learning

Future features:
- Automatic pattern recognition
- Predictive maintenance alerts
- Optimization suggestions
- Anomaly detection

## Troubleshooting

### No Power Readings

1. Check device capabilities
2. Verify firmware version
3. Reset energy monitoring
4. Calibrate if supported

### Incorrect Readings

1. **Calibration**: Adjust factor
2. **Interference**: Check for noise
3. **Firmware**: Update device
4. **Wiring**: Verify connections

### Missing Historical Data

1. Check database storage
2. Verify polling is active
3. Review retention settings
4. Check for gaps in data

### Graph Display Issues

1. Clear browser cache
2. Check date range selection
3. Verify data exists
4. Try different browser

## Best Practices

### Regular Monitoring

- **Daily**: Check unusual spikes
- **Weekly**: Review patterns
- **Monthly**: Analyze reports
- **Quarterly**: Optimize settings

### Data Management

- **Retention**: Balance storage vs history
- **Backup**: Regular database backups
- **Archival**: Export old data
- **Cleanup**: Remove obsolete devices

### Accuracy Maintenance

- **Calibration**: Annual check
- **Firmware**: Keep updated
- **Validation**: Compare with utility meter
- **Documentation**: Log changes

## API Access

### Get Current Power
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/device/192.168.1.100
```

### Get Historical Data
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/device/192.168.1.100/history?start_time=2024-01-01&interval=1h"
```

### Export Data
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/device/192.168.1.100/export?format=csv" \
  -o device-data.csv
```

## Related Pages

- [Cost Analysis](Cost-Analysis) - Understanding costs
- [Dashboard Overview](Dashboard-Overview) - Main interface
- [Device Management](Device-Management) - Device setup
- [API Documentation](API-Documentation) - Developer guide

## Resources

- [Understanding kWh](https://www.eia.gov/energyexplained/)
- [Energy Efficiency Tips](https://www.energy.gov/energysaver)
- [Smart Home Energy Guide](https://www.energystar.gov)

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added