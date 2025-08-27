# Performance Optimization Guide

Comprehensive guide for optimizing Kasa Monitor performance, especially important for Raspberry Pi and resource-constrained environments.

## Performance Overview

```
┌─────────────────────────────────────┐
│     Performance Stack (v1.2.1)      │
├─────────────────────────────────────┤
│  Frontend: React + Chart.js         │
│  Backend: Python + FastAPI          │
│  Database: SQLite + InfluxDB        │
│  Cache: Memory + Redis (optional)   │
│  Container: Docker + Compose        │
└─────────────────────────────────────┘
```

## Recent Performance Improvements (v1.2.1)

- **40% faster initial load times** with optimized bundling
- **60% more responsive charts** with canvas rendering
- **30% memory reduction** for long-term data visualization
- **50% faster API responses** with intelligent caching
- **Automatic data aggregation** reduces data transfer by up to 90%

## Quick Performance Wins

### Essential Optimizations ⚡
- [ ] Enable data aggregation
- [ ] Configure appropriate cache settings
- [ ] Limit concurrent device polling
- [ ] Use time period selection wisely
- [ ] Enable database WAL mode
- [ ] Set memory limits for containers

### Advanced Optimizations 🚀
- [ ] Implement Redis caching
- [ ] Enable CDN for static assets
- [ ] Use database indexing
- [ ] Configure load balancing
- [ ] Implement data partitioning
- [ ] Enable compression

## Database Optimization

### SQLite Performance

**Enable WAL Mode:**
```sql
-- Write-Ahead Logging for better concurrency
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;  -- 64MB cache
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;  -- 256MB memory-mapped I/O
```

**Optimize Queries:**
```sql
-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_readings_device_time 
ON readings(device_ip, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_readings_time_partial 
ON readings(timestamp) 
WHERE timestamp > datetime('now', '-30 days');

-- Analyze tables for query optimizer
ANALYZE readings;
ANALYZE devices;
```

**Database Maintenance:**
```bash
# Vacuum database monthly
sqlite3 /app/data/kasa_monitor.db "VACUUM;"

# Rebuild indexes
sqlite3 /app/data/kasa_monitor.db "REINDEX;"

# Check integrity
sqlite3 /app/data/kasa_monitor.db "PRAGMA integrity_check;"
```

### InfluxDB Optimization

**Retention Policies:**
```sql
-- Keep high-resolution data for 7 days
CREATE RETENTION POLICY "seven_days" 
ON "kasa_monitor" 
DURATION 7d 
REPLICATION 1 
DEFAULT;

-- Keep aggregated data for 1 year
CREATE RETENTION POLICY "one_year" 
ON "kasa_monitor" 
DURATION 365d 
REPLICATION 1;
```

**Continuous Queries:**
```sql
-- Create hourly aggregates
CREATE CONTINUOUS QUERY "hourly_aggregates" 
ON "kasa_monitor" 
BEGIN
  SELECT mean(power) as power_avg,
         max(power) as power_max,
         min(power) as power_min
  INTO "one_year"."device_hourly"
  FROM "device_readings"
  GROUP BY time(1h), device_ip
END
```

## Frontend Optimization

### React Performance

**Code Splitting:**
```javascript
// Lazy load heavy components
const ChartComponent = React.lazy(() => import('./ChartComponent'));
const DeviceDetails = React.lazy(() => import('./DeviceDetails'));

// Use with Suspense
<Suspense fallback={<Loading />}>
  <ChartComponent />
</Suspense>
```

**Memoization:**
```javascript
// Memoize expensive calculations
const processedData = useMemo(() => {
  return processChartData(rawData, period);
}, [rawData, period]);

// Memoize components
const MemoizedChart = React.memo(ChartComponent, (prev, next) => {
  return prev.data === next.data && prev.period === next.period;
});
```

**Virtual Scrolling:**
```javascript
// For large device lists
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={devices.length}
  itemSize={80}
  width="100%"
>
  {DeviceRow}
</FixedSizeList>
```

### Chart Optimization

**Chart.js Settings:**
```javascript
const chartOptions = {
  animation: {
    duration: 0  // Disable animations
  },
  interaction: {
    intersect: false,
    mode: 'index'
  },
  plugins: {
    decimation: {
      enabled: true,
      algorithm: 'lttb',  // Largest Triangle Three Buckets
      samples: 500
    }
  },
  parsing: false,  // Pre-parse data
  normalized: true,
  spanGaps: true,
  datasets: {
    line: {
      pointRadius: 0,  // Hide points
      borderWidth: 1,
      tension: 0  // No bezier curves
    }
  }
};
```

**Data Decimation:**
```javascript
function decimateData(data, targetPoints = 500) {
  if (data.length <= targetPoints) return data;
  
  const bucketSize = Math.floor(data.length / targetPoints);
  const decimated = [];
  
  for (let i = 0; i < data.length; i += bucketSize) {
    const bucket = data.slice(i, i + bucketSize);
    // Use average or peak value
    decimated.push({
      timestamp: bucket[Math.floor(bucket.length / 2)].timestamp,
      value: bucket.reduce((sum, p) => sum + p.value, 0) / bucket.length
    });
  }
  
  return decimated;
}
```

## Backend Optimization

### API Performance

**Caching Strategy:**
```python
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib

class CacheManager:
    def __init__(self):
        self.cache = {}
        
    def cache_key(self, device_ip, period, aggregation):
        """Generate cache key"""
        return hashlib.md5(
            f"{device_ip}:{period}:{aggregation}".encode()
        ).hexdigest()
    
    def get_cache_duration(self, period):
        """Determine cache duration based on period"""
        durations = {
            '24h': timedelta(minutes=5),
            '7d': timedelta(minutes=15),
            '30d': timedelta(hours=1),
            '3m': timedelta(hours=6),
            '6m': timedelta(hours=12),
            '1y': timedelta(days=1)
        }
        return durations.get(period, timedelta(minutes=5))
    
    @lru_cache(maxsize=128)
    def get_cached_data(self, key):
        """Get cached data if valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.get_cache_duration(period):
                return data
        return None
```

**Async Operations:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def fetch_device_data_async(device_ips):
    """Fetch data for multiple devices concurrently"""
    executor = ThreadPoolExecutor(max_workers=10)
    loop = asyncio.get_event_loop()
    
    tasks = [
        loop.run_in_executor(executor, fetch_device_data, ip)
        for ip in device_ips
    ]
    
    results = await asyncio.gather(*tasks)
    return results
```

**Query Optimization:**
```python
def get_optimized_history(device_ip, period):
    """Optimized history query with aggregation"""
    
    # Determine optimal aggregation
    aggregation = get_auto_aggregation(period)
    
    # Use appropriate query based on period
    if period == '24h':
        # Use raw data for last 24 hours
        query = """
            SELECT timestamp, power_w, energy_kwh
            FROM readings
            WHERE device_ip = ? 
            AND timestamp > datetime('now', '-1 day')
            ORDER BY timestamp DESC
        """
    elif period in ['7d', '30d']:
        # Use hourly aggregates
        query = """
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                AVG(power_w) as power_avg,
                SUM(energy_kwh) as energy_sum
            FROM readings
            WHERE device_ip = ?
            AND timestamp > datetime('now', ?)
            GROUP BY hour
            ORDER BY hour DESC
        """
    else:
        # Use daily aggregates for longer periods
        query = """
            SELECT 
                DATE(timestamp) as day,
                AVG(power_w) as power_avg,
                SUM(energy_kwh) as energy_sum
            FROM readings
            WHERE device_ip = ?
            AND timestamp > datetime('now', ?)
            GROUP BY day
            ORDER BY day DESC
        """
    
    return execute_query(query, params)
```

### Device Polling Optimization

**Batch Processing:**
```python
async def poll_devices_batch():
    """Poll devices in batches to avoid overwhelming the network"""
    batch_size = 10
    devices = get_all_devices()
    
    for i in range(0, len(devices), batch_size):
        batch = devices[i:i+batch_size]
        await asyncio.gather(*[poll_device(d) for d in batch])
        await asyncio.sleep(1)  # Pause between batches
```

**Adaptive Polling:**
```python
def get_polling_interval(device):
    """Adjust polling interval based on device activity"""
    if device.is_active:
        return 30  # 30 seconds for active devices
    elif device.last_change < timedelta(hours=1):
        return 60  # 1 minute for recently changed
    else:
        return 300  # 5 minutes for idle devices
```

## Docker Optimization

### Container Resources

**Memory Limits:**
```yaml
version: '3.8'
services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
```

**Build Optimization:**
```dockerfile
# Multi-stage build for smaller image
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --production
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
# Copy only built assets
COPY --from=frontend-builder /app/dist /app/static

# Install only production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Enable Python optimizations
ENV PYTHONOPTIMIZE=1
ENV PYTHONDONTWRITEBYTECODE=1
```

### Docker Compose Optimization

**Service Dependencies:**
```yaml
services:
  redis:
    image: redis:alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    
  kasa-monitor:
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379
      - CACHE_ENABLED=true
```

## Raspberry Pi Specific

### SD Card Optimization

**Reduce Writes:**
```bash
# Move logs to RAM
echo "tmpfs /var/log tmpfs defaults,noatime,size=64m 0 0" >> /etc/fstab

# Disable swap
sudo dphys-swapfile swapoff
sudo systemctl disable dphys-swapfile

# Use log2ram
sudo apt install log2ram
```

### CPU Governor

```bash
# Set to performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Make permanent
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
```

### Memory Management

```bash
# Increase GPU/CPU memory split
echo "gpu_mem=16" | sudo tee -a /boot/config.txt

# Enable zram compression
sudo apt install zram-tools
echo -e "ALGO=lz4\nPERCENT=50" | sudo tee /etc/default/zramswap
```

## Monitoring Performance

### Metrics to Track

```python
import psutil
import time

class PerformanceMonitor:
    def collect_metrics(self):
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_io': psutil.disk_io_counters(),
            'network_io': psutil.net_io_counters(),
            'process_count': len(psutil.pids()),
            'response_time': self.measure_response_time()
        }
    
    def measure_response_time(self):
        start = time.time()
        # Make test API call
        response = requests.get('http://localhost:5272/api/health')
        return time.time() - start
```

### Performance Dashboard

```javascript
// Real-time performance monitoring
const PerformanceWidget = () => {
  const [metrics, setMetrics] = useState({});
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const response = await fetch('/api/system/metrics');
      setMetrics(await response.json());
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="performance-widget">
      <div>CPU: {metrics.cpu_percent}%</div>
      <div>Memory: {metrics.memory_percent}%</div>
      <div>Response Time: {metrics.response_time}ms</div>
    </div>
  );
};
```

## Troubleshooting Performance Issues

### High CPU Usage

**Diagnosis:**
```bash
# Find CPU-intensive processes
top -b -n 1 | head -20

# Check Python processes
ps aux | grep python | sort -k3 -r

# Profile Python code
python -m cProfile -s cumulative app.py
```

**Solutions:**
1. Reduce polling frequency
2. Enable caching
3. Optimize database queries
4. Limit concurrent operations

### High Memory Usage

**Diagnosis:**
```bash
# Check memory usage
free -h

# Find memory-intensive processes
ps aux --sort=-%mem | head

# Check for memory leaks
valgrind --leak-check=full python app.py
```

**Solutions:**
1. Set container memory limits
2. Enable data aggregation
3. Reduce cache size
4. Implement data pruning

### Slow Response Times

**Diagnosis:**
```bash
# Test API response time
time curl http://localhost:5272/api/devices

# Check database performance
sqlite3 /app/data/kasa_monitor.db "EXPLAIN QUERY PLAN SELECT ..."

# Network latency
ping -c 10 device_ip
```

**Solutions:**
1. Enable query caching
2. Add database indexes
3. Optimize network configuration
4. Use CDN for static assets

## Best Practices

### Development
1. Profile before optimizing
2. Use production builds
3. Implement lazy loading
4. Minimize bundle size
5. Use efficient algorithms

### Deployment
1. Set resource limits
2. Enable caching layers
3. Use reverse proxy
4. Implement monitoring
5. Regular maintenance

### Monitoring
1. Track key metrics
2. Set up alerts
3. Log performance data
4. Regular benchmarking
5. User experience monitoring

## Related Documentation

- [Installation](Installation) - Setup guide
- [Docker Deployment](Docker-Deployment) - Container configuration
- [Troubleshooting Guide](Troubleshooting-Guide) - Common issues
- [System Configuration](System-Configuration) - Advanced settings

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-27  
**Review Status:** Current  
**Change Summary:** Initial comprehensive performance optimization guide for v1.2.1