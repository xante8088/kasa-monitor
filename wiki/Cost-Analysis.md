# Cost Analysis

Understanding and optimizing your electricity costs with Kasa Monitor.

## Cost Calculation Basics

### How Costs Are Calculated

```
Basic Formula:
Cost = Energy (kWh) × Rate ($/kWh)

With Time-of-Use:
Cost = Σ(Energy in Period × Rate for Period)

With Tiered Rates:
Cost = Σ(Energy in Tier × Rate for Tier)
```

### Factors Affecting Cost

1. **Energy Consumption** (kWh)
2. **Rate Structure** (Simple/TOU/Tiered)
3. **Time of Use** (Peak/Off-peak)
4. **Demand Charges** (Commercial)
5. **Taxes & Fees** (Additional charges)

## Rate Structures

### Simple Rate

Flat rate per kWh:
```yaml
Type: Simple
Rate: $0.12/kWh
Example: 100 kWh × $0.12 = $12.00
```

### Time-of-Use (TOU)

Different rates by time:
```yaml
Peak (6 AM - 10 PM): $0.15/kWh
Off-Peak (10 PM - 6 AM): $0.08/kWh
Example:
  Day: 60 kWh × $0.15 = $9.00
  Night: 40 kWh × $0.08 = $3.20
  Total: $12.20
```

### Tiered/Block Rates

Rates change with usage:
```yaml
Tier 1 (0-500 kWh): $0.10/kWh
Tier 2 (501-1000 kWh): $0.12/kWh
Tier 3 (1000+ kWh): $0.15/kWh
Example (750 kWh):
  First 500: 500 × $0.10 = $50.00
  Next 250: 250 × $0.12 = $30.00
  Total: $80.00
```

### Demand Charges

Peak demand pricing (commercial):
```yaml
Energy Charge: $0.08/kWh
Demand Charge: $15/kW peak
Example:
  Energy: 1000 kWh × $0.08 = $80
  Peak Demand: 5 kW × $15 = $75
  Total: $155
```

## Dashboard Cost Display

### Cost Summary Widget

Located at top of dashboard:
```
┌─────────────────────────────┐
│ Today: $2.45 ↑ 12%         │
│ MTD: $45.67                 │
│ Projected: $92.34           │
│ Budget: $100 (OK)           │
└─────────────────────────────┘
```

### Device Cost Cards

Each device shows:
- **Today's Cost**: Running total
- **Monthly Cost**: Month-to-date
- **Cost/Hour**: Current rate
- **% of Total**: Proportion of bill

### Cost Trends Graph

Visual representation showing:
- Daily cost bars
- 7-day moving average
- Month-over-month comparison
- Budget line (if set)

## Detailed Cost Analysis

### By Device

Ranked list of cost contributors:

| Rank | Device | Monthly | % Total | Trend |
|------|--------|---------|---------|-------|
| 1 | AC Unit | $28.45 | 31.2% | ↑ 5% |
| 2 | Water Heater | $18.20 | 20.0% | → 0% |
| 3 | Refrigerator | $12.15 | 13.3% | ↓ 2% |
| 4 | TV/Entertainment | $9.80 | 10.8% | ↑ 8% |

### By Time Period

Cost breakdown by time:

```
Morning (6 AM - 12 PM): $15.20 (25%)
Afternoon (12 PM - 6 PM): $24.50 (40%)
Evening (6 PM - 12 AM): $18.30 (30%)
Night (12 AM - 6 AM): $3.05 (5%)
```

### By Category

Group devices by type:

```
Lighting:        $8.50 (14%)
Heating/Cooling: $28.45 (47%)
Appliances:      $15.20 (25%)
Electronics:     $8.52 (14%)
```

## Budget Management

### Setting Budgets

Configure budget alerts:

1. **Monthly Budget**: Total spending limit
2. **Daily Budget**: Daily average target
3. **Device Budgets**: Per-device limits
4. **Category Budgets**: Group limits

### Budget Tracking

Monitor budget status:

```
Monthly Budget: $100
Current Spend: $67.89
Remaining: $32.11
Days Left: 12
Projected: $95.45 ✓
```

### Budget Alerts

Configure notifications:

- 50% of budget reached
- 75% of budget reached
- 90% of budget reached
- Budget exceeded
- Unusual spike detected

## Cost Optimization

### Identify High-Cost Devices

Find expensive devices:

1. **Sort by cost**: Highest first
2. **Cost per hour**: Expensive when on
3. **Always-on cost**: Baseline expense
4. **Efficiency ratio**: Cost per function

### Time-Shifting Opportunities

Move usage to cheaper periods:

```
Current Schedule:
  Dishwasher: 6 PM (Peak) - $0.45/run
  
Optimized Schedule:
  Dishwasher: 11 PM (Off-peak) - $0.24/run
  
Annual Savings: $76.65
```

### Peak Shaving

Reduce peak usage:

```
Current Peak: 5.2 kW
Target Peak: 4.0 kW
Actions:
  - Stagger AC cycles
  - Delay water heater
  - Schedule pool pump
Savings: $18/month demand charge
```

### Device Replacement ROI

Calculate upgrade savings:

```
Old Device: 150W bulb
  Annual Cost: $19.71
  
New Device: 15W LED
  Annual Cost: $1.97
  Purchase Price: $8.00
  
Payback Period: 5.4 months
10-Year Savings: $169.40
```

## Reports & Insights

### Daily Cost Report

```
Date: January 15, 2024
━━━━━━━━━━━━━━━━━━━━
Morning:    $0.82
Afternoon:  $1.15
Evening:    $0.95
Night:      $0.18
━━━━━━━━━━━━━━━━━━━━
Total:      $3.10

Top Devices:
1. AC Unit: $1.20
2. Kitchen: $0.65
3. Office: $0.45
```

### Monthly Cost Report

Comprehensive monthly analysis:

- Total cost with breakdown
- Daily average and trends
- Comparison to previous months
- Device rankings
- Optimization opportunities
- Budget performance

### Annual Summary

Year-end analysis includes:

- Monthly cost chart
- Seasonal patterns
- Year-over-year comparison
- Total savings achieved
- Device lifecycle costs

## Advanced Analytics

### Cost Forecasting

Predict future costs:

```python
# Based on:
- Historical patterns
- Weather forecast
- Seasonal trends
- Rate changes

Next Month Estimate: $92.34 ± $5.20
```

### What-If Analysis

Model different scenarios:

```
Scenario 1: Add solar panels
  Monthly Savings: $45
  ROI Period: 7 years

Scenario 2: Switch to TOU rates
  Monthly Change: -$8 (savings)
  Best if shift 30% to off-peak

Scenario 3: Upgrade appliances
  Monthly Savings: $22
  Investment: $2,400
```

### Comparative Analysis

Compare costs:

- vs. Previous period
- vs. Similar homes
- vs. Utility average
- vs. Seasonal baseline

## Utility Bill Validation

### Compare with Utility

Verify accuracy:

```
Utility Bill: $124.56
Kasa Monitor: $121.89
Difference: $2.67 (2.1%)

Common differences:
- Meter reading dates
- Taxes and fees
- Rounding differences
```

### Reconciliation

Match utility charges:

1. Export monthly data
2. Align billing periods
3. Add taxes/fees
4. Compare totals
5. Investigate discrepancies

## Cost Saving Tips

### Quick Wins

Immediate savings:

1. **Eliminate phantom loads**: $5-10/month
2. **Adjust thermostat 2°**: $10-15/month
3. **Use timers/schedules**: $8-12/month
4. **LED replacements**: $15-20/month

### Medium-Term

3-6 month projects:

1. **Smart thermostat**: $20-30/month
2. **Efficient appliances**: $25-40/month
3. **Insulation upgrades**: $30-50/month
4. **Solar consideration**: $50-100/month

### Behavioral Changes

Habit modifications:

- Turn off when leaving
- Batch similar tasks
- Use natural light
- Maintain equipment
- Monitor regularly

## Export & Integration

### Export Options

| Format | Contents | Use Case |
|--------|----------|----------|
| CSV | Raw cost data | Spreadsheet analysis |
| PDF | Formatted report | Sharing/filing |
| Excel | Charts & graphs | Detailed analysis |
| JSON | Structured data | API integration |

### Integration

Connect with:

- **Accounting Software**: QuickBooks, Xero
- **Spreadsheets**: Google Sheets, Excel
- **Utilities**: Some utility APIs
- **Smart Home**: Home Assistant

## API Access

### Get Cost Summary
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/costs?start_date=2024-01-01"
```

### Get Device Costs
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/device/192.168.1.100/stats"
```

### Export Cost Report
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/costs/export?format=pdf" \
  -o cost-report.pdf
```

## Troubleshooting

### Incorrect Costs

1. Verify rate configuration
2. Check time zone settings
3. Confirm billing period
4. Validate energy readings

### Missing Cost Data

1. Ensure rates are configured
2. Check device monitoring
3. Verify database storage
4. Review calculation logs

### Budget Alert Issues

1. Check alert settings
2. Verify email configuration
3. Test notification system
4. Review threshold values

## Best Practices

1. **Regular Review**: Weekly cost check
2. **Update Rates**: When utility changes
3. **Set Budgets**: Monthly targets
4. **Track Savings**: Document improvements
5. **Validate**: Compare with bills

## Related Pages

- [Electricity Rates](Electricity-Rates) - Rate configuration
- [Energy Monitoring](Energy-Monitoring) - Consumption tracking
- [Dashboard Overview](Dashboard-Overview) - Cost displays
- [Reports](Reports) - Detailed reporting

## Getting Help

- [FAQ](FAQ) - Common questions
- [Support](https://github.com/xante8088/kasa-monitor/issues)
- [Community](https://github.com/xante8088/kasa-monitor/discussions)

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added