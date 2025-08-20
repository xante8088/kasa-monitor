# Electricity Rates Configuration

Complete guide to setting up and managing electricity rate structures in Kasa Monitor.

## Understanding Rate Types

### Simple/Flat Rate

Single rate for all consumption:

```yaml
Type: Simple
Rate: $0.12 per kWh
Total Cost = kWh × Rate

Example:
  100 kWh × $0.12 = $12.00
```

**When to use:**
- Your utility charges a flat rate
- Simplified cost tracking
- No time-based variations

### Time-of-Use (TOU) Rates

Different rates based on time of day:

```yaml
Type: Time-of-Use
Peak Hours (6 AM - 10 PM): $0.15/kWh
Off-Peak (10 PM - 6 AM): $0.08/kWh
Weekends: $0.10/kWh (all day)

Example:
  Weekday: 60 kWh peak + 40 kWh off-peak
  Cost: (60 × $0.15) + (40 × $0.08) = $12.20
```

**When to use:**
- Utility offers TOU pricing
- Ability to shift usage
- Save money by timing usage

### Tiered/Block Rates

Rates change based on total usage:

```yaml
Type: Tiered
Tier 1 (0-500 kWh): $0.10/kWh
Tier 2 (501-1000 kWh): $0.12/kWh  
Tier 3 (1000+ kWh): $0.15/kWh

Example (750 kWh total):
  First 500: 500 × $0.10 = $50.00
  Next 250: 250 × $0.12 = $30.00
  Total: $80.00
```

**When to use:**
- Progressive rate structure
- Incentivizes conservation
- Common in many regions

### Seasonal Rates

Different rates by season:

```yaml
Type: Seasonal
Summer (Jun-Sep): $0.14/kWh
Winter (Dec-Mar): $0.11/kWh
Spring/Fall: $0.12/kWh

With TOU overlay:
  Summer Peak: $0.18/kWh
  Summer Off-Peak: $0.10/kWh
  Winter Peak: $0.13/kWh
  Winter Off-Peak: $0.08/kWh
```

## Configuration Guide

### Accessing Rate Settings

1. Click Settings (⚙️) in header
2. Select "Electricity Rates"
3. Choose your rate structure
4. Enter rate details
5. Save configuration

### Simple Rate Setup

```
1. Select "Simple/Flat Rate"
2. Enter rate per kWh: [0.12]
3. Select currency: [USD]
4. Add taxes/fees: [8.5%] (optional)
5. Click "Save"
```

### Time-of-Use Setup

```
1. Select "Time-of-Use"
2. Define time periods:
   
   Peak Hours:
   - Start: [06:00]
   - End: [22:00]
   - Rate: [0.15]
   - Days: [Mon-Fri]
   
   Off-Peak Hours:
   - Start: [22:00]
   - End: [06:00]
   - Rate: [0.08]
   - Days: [Mon-Sun]
   
   Weekend Rate:
   - Rate: [0.10]
   - Days: [Sat-Sun]
   
3. Click "Save"
```

### Tiered Rate Setup

```
1. Select "Tiered/Block"
2. Configure tiers:
   
   Tier 1:
   - From: [0] kWh
   - To: [500] kWh
   - Rate: [0.10]
   
   Tier 2:
   - From: [501] kWh
   - To: [1000] kWh
   - Rate: [0.12]
   
   Tier 3:
   - From: [1001] kWh
   - To: [Unlimited]
   - Rate: [0.15]
   
3. Billing cycle: [Monthly]
4. Reset day: [1st]
5. Click "Save"
```

## Advanced Configuration

### Demand Charges

For commercial accounts:

```yaml
Configuration:
  Energy Charge: $0.08/kWh
  Demand Charge: $15/kW
  Measurement: 15-minute peak
  Billing: Monthly maximum

Example:
  Energy: 1000 kWh × $0.08 = $80
  Peak Demand: 5.2 kW × $15 = $78
  Total: $158
```

### Taxes and Fees

Add additional charges:

```yaml
Base Rate: $0.12/kWh
Taxes:
  State Tax: 5%
  Local Tax: 3.5%
  
Fees:
  Delivery: $0.02/kWh
  Renewable Energy: $0.005/kWh
  Grid Maintenance: $5/month (fixed)

Total Rate: $0.145/kWh + $5
```

### Net Metering

For solar installations:

```yaml
Configuration:
  Buy Rate: $0.12/kWh
  Sell Rate: $0.08/kWh
  True-up Period: Annual
  Banking: Yes

Calculation:
  Consumed: 500 kWh × $0.12 = $60
  Generated: 300 kWh × $0.08 = -$24
  Net Bill: $36
```

## Rate Schedules

### Holiday Rates

Configure special day rates:

```yaml
Holidays:
  - New Year's Day: Off-peak all day
  - July 4th: Off-peak all day
  - Thanksgiving: Off-peak all day
  - Christmas: Off-peak all day

Override: Regular TOU schedule
```

### Critical Peak Pricing

Event-based pricing:

```yaml
CPP Events:
  Trigger: Utility notification
  Rate: $0.50/kWh
  Duration: 2-6 PM
  Max Events: 15/year
  Notice: 24 hours

Regular Days: Standard TOU
```

### Real-Time Pricing

Dynamic hourly rates:

```yaml
Source: Utility API
Update: Hourly
Display: Current and next hour
Alerts: When > $0.15/kWh
History: 30 days
```

## Finding Your Rates

### Utility Bill

Locate on your bill:

```
Your Electric Charges:
Generation: $0.0654/kWh
Transmission: $0.0234/kWh
Distribution: $0.0298/kWh
Other: $0.0014/kWh
━━━━━━━━━━━━━━━━━━
Total: $0.12/kWh
```

### Utility Website

Steps to find rates:

1. Visit utility website
2. Search "electric rates" or "tariffs"
3. Find residential rates
4. Look for rate schedule (PDF)
5. Note your rate plan name

### Common Utilities

Quick links to major utilities:

- [PG&E](https://www.pge.com/tariffs/)
- [ConEd](https://www.coned.com/rates)
- [ComEd](https://www.comed.com/rates)
- [Duke Energy](https://www.duke-energy.com/rates)
- [FPL](https://www.fpl.com/rates)

## Rate Comparison

### Analyzing Rate Options

Compare different plans:

```
Current: Flat Rate
  Monthly Cost: $120
  
Option 1: TOU
  If shift 30% to off-peak: $108
  Savings: $12/month
  
Option 2: Tiered
  At current usage: $115
  Savings: $5/month
```

### Optimization Calculator

Built-in tool calculates:

1. Best rate for your usage
2. Potential savings
3. Required behavior changes
4. Break-even points

## Examples by Region

### California (PG&E)

```yaml
Plan: TOU-C
Peak (4-9 PM): $0.40/kWh
Off-Peak: $0.28/kWh
Super Off-Peak (12-6 AM): $0.18/kWh
Baseline Credit: -$0.08/kWh (first 300 kWh)
```

### Texas (Deregulated)

```yaml
Provider: Various
Fixed Rate: $0.09-0.12/kWh
Variable Rate: Market-based
Free Nights: $0.15 day, $0 night
Solar Buyback: Available
```

### New York (ConEd)

```yaml
Service Class: SC-1
Summer (Jun-Sep): $0.24/kWh
Winter (Oct-May): $0.18/kWh
Delivery: $0.08/kWh
Taxes: ~8%
```

## Rate Management

### Updating Rates

When to update:

- Utility rate change (usually annual)
- Plan change
- Seasonal transitions
- Moving to new location

How to update:

1. Go to Settings → Electricity Rates
2. Click "Edit Current Rate"
3. Update values
4. Set effective date
5. Save changes

### Rate History

Track rate changes:

```
History:
2024-01-01: $0.11/kWh → $0.12/kWh
2023-06-01: TOU implemented
2023-01-01: $0.10/kWh → $0.11/kWh
```

### Multiple Rates

For multiple locations:

```yaml
Location 1 (Home):
  Rate: TOU
  Peak: $0.15/kWh
  
Location 2 (Office):
  Rate: Commercial
  Demand: Yes
  
Location 3 (Rental):
  Rate: Flat
  Include: In rent
```

## Troubleshooting

### Common Issues

**Costs don't match bill:**
1. Check rate configuration
2. Verify billing period alignment
3. Include all taxes/fees
4. Check for proration

**TOU not calculating correctly:**
1. Verify time zone setting
2. Check peak hour definition
3. Confirm weekday/weekend rules
4. Review holiday schedule

**Tiered rates wrong:**
1. Check tier boundaries
2. Verify reset date
3. Confirm cumulative calculation
4. Check billing cycle

### Rate Validation

Test your configuration:

```bash
# API test
curl -X POST http://localhost:8000/api/rates/test \
  -H "Content-Type: application/json" \
  -d '{
    "kwh": 750,
    "date": "2024-01-15",
    "time": "18:00"
  }'

# Expected: $XX.XX
```

## Best Practices

1. **Accuracy**: Use exact rates from bill
2. **Updates**: Check rates quarterly
3. **Documentation**: Save rate schedules
4. **Validation**: Compare with actual bills
5. **Optimization**: Review usage patterns

## API Configuration

### Get Current Rates
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rates
```

### Update Rates
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rate_type": "tiered",
    "currency": "USD",
    "rate_structure": {
      "tier1_limit": 500,
      "tier1_rate": 0.10,
      "tier2_limit": 1000,
      "tier2_rate": 0.12,
      "tier3_rate": 0.15
    }
  }' \
  http://localhost:8000/api/rates
```

## Related Pages

- [Cost Analysis](Cost-Analysis) - Using rate data
- [Energy Monitoring](Energy-Monitoring) - Consumption tracking
- [Dashboard Overview](Dashboard-Overview) - Cost display
- [API Documentation](API-Documentation) - Rate endpoints

## Resources

- [EIA Electricity Data](https://www.eia.gov/electricity/)
- [OpenEI Utility Rates](https://openei.org/wiki/Utility_Rate_Database)
- [Energy.gov Rate Info](https://www.energy.gov/rates)

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial version tracking added