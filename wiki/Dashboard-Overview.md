# Dashboard Overview

The Kasa Monitor dashboard is your central hub for monitoring and controlling all your smart devices.

## Layout Overview

### Header Bar
![Header](https://via.placeholder.com/800x100)

The header contains:
- **Logo & Title**: Kasa Monitor branding
- **Quick Stats**: Total devices, active devices, current total power
- **Action Buttons**:
  - 🔍 **Discover Devices**: Scan for new devices
  - 💰 **Electricity Rates**: Configure pricing
  - ⚙️ **Device Management**: Manage devices
  - 👤 **User Menu**: Profile and logout

### Cost Summary Panel
Located at the top of the dashboard, showing:
- **Today's Cost**: Running total for the current day
- **Month to Date**: Total cost for current month
- **Projected Monthly**: Estimated monthly cost based on usage
- **Peak Demand**: Highest power draw today

### Device Grid

The main area displays all your devices in a responsive grid layout.

#### Device Cards

Each device card shows:

```
┌─────────────────────────┐
│ 🔌 Living Room Lamp     │  <- Device name
│ HS110 Smart Plug        │  <- Model
│                         │
│ ⚡ 45.2W               │  <- Current power
│ 📊 0.36 kWh today      │  <- Daily usage
│ 💵 $0.04 today         │  <- Daily cost
│                         │
│ [====ON====] [Details>] │  <- Controls
└─────────────────────────┘
```

**Card Elements**:
- **Status Indicator**: Green (on) or Gray (off)
- **Device Name**: Custom alias
- **Model**: Device model number
- **Current Power**: Real-time consumption
- **Daily Stats**: Today's energy and cost
- **Quick Toggle**: On/off switch
- **Details Link**: View detailed analytics

#### Card States

- **Online & Active**: Full color, all data visible
- **Online & Idle**: Grayed out, showing as off
- **Offline**: Red border, "Offline" badge
- **Updating**: Pulsing animation

## Interactive Features

### Quick Actions

#### Device Control
- **Single Click**: Toggle device on/off
- **Long Press**: Quick settings menu
- **Details Button**: Open device analytics

#### Bulk Operations
1. Select multiple devices (checkbox mode)
2. Apply bulk actions:
   - Turn all on/off
   - Group devices
   - Export data

### Real-Time Updates

Data refreshes automatically:
- Power readings: Every 60 seconds
- Device status: Instant via WebSocket
- Cost calculations: Every 5 minutes

Visual indicators:
- 🟢 Green dot: Recent update
- 🟡 Yellow dot: Updating
- 🔴 Red dot: Connection issue

### Filtering & Sorting

#### Filter Options
- **Status**: All, On, Off, Offline
- **Type**: Plugs, Switches, Bulbs, Strips
- **Location**: By room/group
- **Power Range**: Low, Medium, High

#### Sort Options
- Name (A-Z)
- Power consumption (High to Low)
- Daily cost (High to Low)
- Total runtime
- Last updated

### Search

Quick search bar features:
- Search by device name
- Search by IP address
- Search by model
- Fuzzy matching supported

## Dashboard Sections

### 1. Summary Statistics

Top bar shows aggregate data:
```
Total Power: 458W | Devices: 12 (8 on) | Daily: 5.2 kWh | Cost: $0.62
```

### 2. Device Grid (Main Area)

Responsive layout:
- Desktop: 4 columns
- Tablet: 2-3 columns
- Mobile: 1 column

### 3. Quick Insights (Optional Sidebar)

When enabled, shows:
- Top 5 energy consumers
- Devices on longest
- Recent activity log
- Cost breakdown pie chart

## Customization Options

### Display Settings

Access via Settings → Dashboard:

- **Grid Density**: Compact, Normal, Comfortable
- **Card Style**: Simple, Detailed, Minimal
- **Update Frequency**: 30s, 60s, 120s
- **Show Offline Devices**: Yes/No
- **Group By**: None, Room, Type

### Color Themes

- **Light Mode**: Default white background
- **Dark Mode**: Dark theme for night viewing
- **Auto**: Follows system preference

### Data Display

Configure what's shown on cards:
- [ ] Current power
- [ ] Daily energy
- [ ] Daily cost
- [ ] Monthly totals
- [ ] Signal strength
- [ ] IP address
- [ ] Last update time

## Navigation

### From Dashboard

Click any device card to access:
- **Device Details**: Comprehensive analytics
- **History Graph**: Power over time
- **Statistics**: Usage patterns
- **Controls**: Advanced settings

### Keyboard Shortcuts

- `Space`: Toggle selected device
- `S`: Open search
- `D`: Discover devices
- `R`: Refresh all
- `1-9`: Quick toggle device 1-9
- `?`: Show help

## Mobile Experience

### Responsive Design

Optimized for mobile:
- Touch-friendly controls
- Swipe gestures
- Pull-to-refresh
- Collapsible sections

### Mobile-Specific Features

- **Swipe Actions**: Swipe left/right on devices
- **Bottom Navigation**: Quick access bar
- **Compact Mode**: Condensed view
- **Gesture Controls**: Pinch to zoom grid

## Performance Indicators

### Connection Status

Header shows connection health:
- 🟢 **Connected**: All systems operational
- 🟡 **Degraded**: Some devices offline
- 🔴 **Disconnected**: Backend unreachable

### Loading States

- **Skeleton Loading**: Shows layout while loading
- **Progressive Load**: Devices appear as discovered
- **Cached Data**: Shows last known state

## Tips & Tricks

### Optimize Your View

1. **Group Similar Devices**: Create rooms or zones
2. **Hide Inactive**: Filter out rarely-used devices
3. **Pin Favorites**: Star frequently-used devices
4. **Custom Names**: Use descriptive, memorable names

### Quick Monitoring

1. **Daily Review**: Check morning/evening peaks
2. **Cost Alerts**: Set threshold notifications
3. **Usage Patterns**: Identify energy waste
4. **Compare Devices**: Rank by efficiency

### Troubleshooting Dashboard Issues

**Devices Not Showing**
- Check network connection
- Verify device is powered
- Try manual refresh
- Check filter settings

**Slow Updates**
- Reduce update frequency
- Check network latency
- Limit number of devices shown
- Clear browser cache

**Incorrect Data**
- Sync device time
- Recalibrate energy monitoring
- Check rate configuration
- Verify device firmware

## Advanced Features

### Custom Widgets

Add custom widgets:
- Weather integration
- Solar production
- Utility rate alerts
- Smart scheduling

### Data Export

Export dashboard data:
- CSV for spreadsheets
- JSON for automation
- PDF reports
- API integration

### Automation Rules

Set up triggers:
- High power alerts
- Scheduled on/off
- Cost thresholds
- Group scenes

## Best Practices

1. **Organize Logically**: Group by room or function
2. **Name Clearly**: "Kitchen Coffee Maker" not "Plug 3"
3. **Monitor Regularly**: Check weekly patterns
4. **Set Budgets**: Use cost alerts
5. **Update Firmware**: Keep devices current

## Related Pages

- [Device Management](Device-Management) - Add and configure devices
- [Energy Monitoring](Energy-Monitoring) - Detailed consumption analysis
- [Cost Analysis](Cost-Analysis) - Understanding your costs
- [API Documentation](API-Documentation) - Integrate with dashboard

## Getting Help

- Hover over any element for tooltips
- Click ❓ icon for contextual help
- Check [FAQ](FAQ) for common questions
- Report issues on [GitHub](https://github.com/xante8088/kasa-monitor/issues)

---

**Document Version:** 0.1.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added