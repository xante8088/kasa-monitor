# Time Period Selector - Backend API Requirements

## Overview

The Time Period Selector system requires backend API enhancements to support time-filtered data queries. The frontend now sends time range parameters that need to be processed by the backend.

## API Endpoint Modifications Required

### Device History Endpoint

**Endpoint:** `GET /api/device/{deviceIp}/history`

**New Query Parameters:**

```
start_time: string (ISO 8601 datetime)
  - Optional: Start of time range filter
  - Example: "2024-08-20T00:00:00.000Z"

end_time: string (ISO 8601 datetime)  
  - Optional: End of time range filter
  - Example: "2024-08-27T23:59:59.999Z"

time_period: string (enum)
  - Optional: Predefined time period type
  - Values: "1h", "6h", "24h", "3d", "7d", "30d", "custom"
  - Used for optimization and caching
```

**Example Requests:**

```bash
# Last 24 hours
GET /api/device/192.168.1.100/history?time_period=24h&start_time=2024-08-26T10:00:00.000Z&end_time=2024-08-27T10:00:00.000Z

# Custom date range
GET /api/device/192.168.1.100/history?time_period=custom&start_time=2024-08-01T00:00:00.000Z&end_time=2024-08-15T23:59:59.999Z

# No filter (backward compatibility)
GET /api/device/192.168.1.100/history
```

## Backend Implementation Requirements

### 1. Database Query Filtering

```python
# Example pseudocode for filtering
def get_device_history(device_ip, start_time=None, end_time=None, time_period=None):
    query = "SELECT * FROM device_readings WHERE device_ip = ?"
    params = [device_ip]
    
    if start_time:
        query += " AND timestamp >= ?"
        params.append(start_time)
        
    if end_time:
        query += " AND timestamp <= ?"
        params.append(end_time)
        
    query += " ORDER BY timestamp ASC"
    
    return execute_query(query, params)
```

### 2. Data Aggregation for Performance

For longer time periods, consider data aggregation to reduce payload size:

```python
def get_aggregated_data(device_ip, time_period, start_time, end_time):
    if time_period in ['30d', 'custom'] and days_difference > 7:
        # Aggregate to hourly data points
        return aggregate_hourly(device_ip, start_time, end_time)
    elif time_period in ['7d', '3d']:
        # Aggregate to 15-minute intervals
        return aggregate_15min(device_ip, start_time, end_time)
    else:
        # Return raw data for shorter periods
        return get_raw_data(device_ip, start_time, end_time)
```

### 3. Response Format

The response should maintain the existing format but with filtered data:

```json
{
  "data": [
    {
      "timestamp": "2024-08-27T10:00:00.000Z",
      "current_power_w": 125.5,
      "current": 1.04,
      "voltage": 120.2,
      "today_energy_kwh": 2.45,
      "month_energy_kwh": 45.67,
      "total_energy_kwh": 1234.56
    }
  ],
  "metadata": {
    "time_period": "24h",
    "start_time": "2024-08-26T10:00:00.000Z",
    "end_time": "2024-08-27T10:00:00.000Z",
    "data_points": 1440,
    "aggregated": false
  }
}
```

### 4. Caching Strategy

Implement caching for better performance:

```python
# Cache key examples
cache_keys = {
    "1h": f"device_history_{device_ip}_1h_{current_hour}",
    "24h": f"device_history_{device_ip}_24h_{current_date}",
    "7d": f"device_history_{device_ip}_7d_{current_week}",
    "custom": f"device_history_{device_ip}_{start_date}_{end_date}"
}
```

### 5. Error Handling

```python
def validate_time_parameters(start_time, end_time, time_period):
    errors = []
    
    if start_time and end_time:
        if start_time >= end_time:
            errors.append("start_time must be before end_time")
            
        # Check maximum range (e.g., 90 days)
        if (end_time - start_time).days > 90:
            errors.append("Time range cannot exceed 90 days")
    
    if time_period and time_period not in VALID_TIME_PERIODS:
        errors.append(f"Invalid time_period: {time_period}")
        
    return errors
```

## Database Optimization

### 1. Index Recommendations

```sql
-- Composite index for efficient time-based filtering
CREATE INDEX idx_device_readings_time 
ON device_readings(device_ip, timestamp);

-- Consider partitioning for large datasets
CREATE TABLE device_readings_2024_08 PARTITION OF device_readings
FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
```

### 2. Data Retention Policy

Consider implementing data retention:
- Raw data: Keep for 7 days
- 15-minute aggregates: Keep for 30 days  
- Hourly aggregates: Keep for 1 year
- Daily aggregates: Keep indefinitely

## Performance Considerations

1. **Data Volume**: Limit returned data points to prevent large payloads
2. **Query Timeout**: Set reasonable timeouts for long-running queries
3. **Rate Limiting**: Implement rate limiting for time-filtered queries
4. **Compression**: Use response compression for large datasets

## Backward Compatibility

The API must remain backward compatible:
- Existing calls without time parameters should work as before
- Default behavior should return the same data as currently

## Testing Requirements

1. **Unit Tests**: Time parameter validation
2. **Integration Tests**: End-to-end time filtering
3. **Performance Tests**: Large time range queries
4. **Edge Case Tests**: Invalid date ranges, timezone handling

## Security Considerations

1. **Parameter Validation**: Sanitize all time parameters
2. **Access Control**: Ensure users can only access authorized device data
3. **Resource Limits**: Prevent excessive data requests

## Monitoring & Logging

Add monitoring for:
- Query execution times by time period
- Cache hit/miss rates
- Most frequently requested time ranges
- API response sizes

## Implementation Priority

1. **Phase 1**: Basic time filtering (start_time, end_time)
2. **Phase 2**: Data aggregation for performance
3. **Phase 3**: Advanced caching and optimization
4. **Phase 4**: Monitoring and analytics

This completes the backend requirements for the Time Period Selector functionality.