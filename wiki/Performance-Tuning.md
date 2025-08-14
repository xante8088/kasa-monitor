# Performance Tuning

Complete guide for optimizing Kasa Monitor performance for various deployment scenarios.

## Performance Overview

```
┌─────────────────────────────────────┐
│    Performance Optimization Areas   │
├─────────────────────────────────────┤
│  1. Database Optimization           │
│  2. Polling Efficiency              │
│  3. Caching Strategy                │
│  4. Resource Management             │
│  5. Network Optimization            │
└─────────────────────────────────────┘
```

## Quick Optimization

### Basic Performance Settings

```bash
# Environment variables for performance
POLLING_THREADS=4
POLLING_BATCH_SIZE=10
CACHE_TTL=300
DATABASE_POOL_SIZE=10
WORKERS=4
```

### Docker Resource Limits

```yaml
services:
  kasa-monitor:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Database Optimization

### SQLite Performance

```sql
-- Optimize database
PRAGMA journal_mode = WAL;  -- Write-Ahead Logging
PRAGMA synchronous = NORMAL;  -- Faster writes
PRAGMA cache_size = -64000;  -- 64MB cache
PRAGMA temp_store = MEMORY;  -- Use memory for temp tables
PRAGMA mmap_size = 30000000000;  -- Memory-mapped I/O

-- Analyze tables for query optimization
ANALYZE;

-- Optimize database file
VACUUM;
PRAGMA optimize;
```

### Index Optimization

```sql
-- Essential indexes for performance
CREATE INDEX IF NOT EXISTS idx_readings_device_time 
ON readings(device_ip, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
ON readings(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_daily_device_date 
ON daily_summaries(device_ip, date DESC);

CREATE INDEX IF NOT EXISTS idx_devices_active 
ON devices(is_active, is_monitored);

-- Compound index for common queries
CREATE INDEX IF NOT EXISTS idx_readings_device_power 
ON readings(device_ip, timestamp DESC, power_w);

-- Analyze index usage
SELECT name, tbl_name, sql 
FROM sqlite_master 
WHERE type = 'index';
```

### Query Optimization

```python
# Inefficient query
def get_device_history_slow(device_ip):
    return db.execute("""
        SELECT * FROM readings 
        WHERE device_ip = ? 
        ORDER BY timestamp DESC
    """, (device_ip,)).fetchall()

# Optimized query
def get_device_history_fast(device_ip, limit=100):
    return db.execute("""
        SELECT timestamp, power_w, energy_kwh 
        FROM readings 
        WHERE device_ip = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (device_ip, limit)).fetchall()

# Batch query optimization
def get_multiple_devices_fast(device_ips):
    placeholders = ','.join('?' * len(device_ips))
    return db.execute(f"""
        SELECT device_ip, MAX(timestamp) as last_seen, 
               AVG(power_w) as avg_power
        FROM readings 
        WHERE device_ip IN ({placeholders})
        AND timestamp > datetime('now', '-1 hour')
        GROUP BY device_ip
    """, device_ips).fetchall()
```

### Data Retention Strategy

```python
async def optimize_data_retention():
    """Implement tiered data retention"""
    
    # Keep raw data for 7 days
    await db.execute("""
        DELETE FROM readings 
        WHERE timestamp < datetime('now', '-7 days')
    """)
    
    # Aggregate older data
    await db.execute("""
        INSERT OR REPLACE INTO hourly_summaries 
        SELECT 
            device_ip,
            strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
            AVG(power_w) as avg_power,
            MAX(power_w) as max_power,
            SUM(energy_kwh) as total_energy
        FROM readings
        WHERE timestamp < datetime('now', '-7 days')
        AND timestamp >= datetime('now', '-30 days')
        GROUP BY device_ip, hour
    """)
    
    # Keep hourly for 30 days, daily for 1 year
    await db.execute("""
        DELETE FROM hourly_summaries 
        WHERE hour < datetime('now', '-30 days')
    """)
```

## Polling Optimization

### Efficient Polling Strategy

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OptimizedPoller:
    def __init__(self, max_workers=4, batch_size=10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.batch_size = batch_size
        self.device_cache = {}
        self.last_poll_times = {}
    
    async def poll_devices(self, devices):
        """Poll devices in batches"""
        batches = [devices[i:i + self.batch_size] 
                  for i in range(0, len(devices), self.batch_size)]
        
        tasks = []
        for batch in batches:
            task = asyncio.create_task(self.poll_batch(batch))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for batch in results for r in batch if not isinstance(r, Exception)]
    
    async def poll_batch(self, batch):
        """Poll a batch of devices concurrently"""
        loop = asyncio.get_event_loop()
        
        tasks = []
        for device in batch:
            # Skip if recently polled
            if self.should_skip_poll(device):
                tasks.append(self.get_cached_data(device))
            else:
                task = loop.run_in_executor(
                    self.executor, 
                    self.poll_device, 
                    device
                )
                tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def should_skip_poll(self, device):
        """Check if device was recently polled"""
        last_poll = self.last_poll_times.get(device['device_ip'], 0)
        min_interval = device.get('min_poll_interval', 30)
        
        return (time.time() - last_poll) < min_interval
    
    async def get_cached_data(self, device):
        """Return cached device data"""
        return self.device_cache.get(device['device_ip'])
```

### Adaptive Polling

```python
class AdaptivePoller:
    """Adjust polling frequency based on device activity"""
    
    def __init__(self):
        self.poll_intervals = {}  # Device-specific intervals
        self.activity_scores = {}  # Track device activity
    
    def calculate_poll_interval(self, device_ip, recent_changes):
        """Calculate optimal polling interval"""
        
        # Base interval
        base_interval = 60
        
        # Adjust based on recent activity
        if len(recent_changes) == 0:
            # No changes, increase interval
            return min(base_interval * 4, 300)  # Max 5 minutes
        
        # Calculate variance in readings
        variance = self.calculate_variance(recent_changes)
        
        if variance < 0.01:
            # Very stable, poll less frequently
            return base_interval * 2
        elif variance > 0.1:
            # High variance, poll more frequently
            return base_interval // 2
        else:
            return base_interval
    
    def calculate_variance(self, changes):
        """Calculate variance in power readings"""
        if len(changes) < 2:
            return 0
        
        values = [c['power_w'] for c in changes]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        # Normalize by mean to get coefficient of variation
        return variance / (mean ** 2) if mean > 0 else 0
```

## Caching Strategy

### Redis Caching

```python
import redis
import json
import pickle
from functools import wraps

redis_client = redis.Redis(
    host='redis',
    port=6379,
    decode_responses=False,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 5,  # TCP_KEEPINTVL
        3: 5,  # TCP_KEEPCNT
    }
)

def cache_result(ttl=300):
    """Cache function results in Redis"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return pickle.loads(cached)
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            redis_client.setex(
                cache_key, 
                ttl, 
                pickle.dumps(result)
            )
            
            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=60)
async def get_device_stats(device_ip):
    return await expensive_calculation(device_ip)
```

### Multi-Level Caching

```python
class MultiLevelCache:
    """Implement L1 (memory) and L2 (Redis) caching"""
    
    def __init__(self, l1_size=100, l1_ttl=60, l2_ttl=300):
        self.l1_cache = {}  # Memory cache
        self.l1_size = l1_size
        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.access_times = {}
    
    async def get(self, key):
        # Check L1 cache
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if time.time() - entry['time'] < self.l1_ttl:
                return entry['value']
            else:
                del self.l1_cache[key]
        
        # Check L2 cache (Redis)
        cached = redis_client.get(key)
        if cached:
            value = pickle.loads(cached)
            # Promote to L1
            self.set_l1(key, value)
            return value
        
        return None
    
    async def set(self, key, value):
        # Set in both caches
        self.set_l1(key, value)
        redis_client.setex(key, self.l2_ttl, pickle.dumps(value))
    
    def set_l1(self, key, value):
        # Implement LRU eviction
        if len(self.l1_cache) >= self.l1_size:
            # Remove least recently used
            lru_key = min(self.access_times, key=self.access_times.get)
            del self.l1_cache[lru_key]
            del self.access_times[lru_key]
        
        self.l1_cache[key] = {
            'value': value,
            'time': time.time()
        }
        self.access_times[key] = time.time()
```

## API Optimization

### Response Caching

```python
from fastapi import FastAPI, Request
from fastapi.responses import Response
import hashlib

app = FastAPI()

@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    # Only cache GET requests
    if request.method != "GET":
        return await call_next(request)
    
    # Generate cache key
    cache_key = hashlib.md5(
        f"{request.url.path}:{request.url.query}".encode()
    ).hexdigest()
    
    # Check cache
    cached = redis_client.get(f"response:{cache_key}")
    if cached:
        return Response(
            content=cached,
            media_type="application/json",
            headers={"X-Cache": "HIT"}
        )
    
    # Process request
    response = await call_next(request)
    
    # Cache successful responses
    if response.status_code == 200:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        redis_client.setex(
            f"response:{cache_key}",
            60,  # 1 minute TTL
            body
        )
        
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
    
    return response
```

### Pagination and Filtering

```python
@app.get("/api/readings")
async def get_readings(
    device_ip: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0,
    fields: str = "timestamp,power_w,energy_kwh"
):
    """Optimized endpoint with pagination and field selection"""
    
    # Build optimized query
    selected_fields = fields.split(',')
    query = f"SELECT {fields} FROM readings WHERE 1=1"
    params = []
    
    if device_ip:
        query += " AND device_ip = ?"
        params.append(device_ip)
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
    
    # Use index
    query += " ORDER BY timestamp DESC"
    
    # Pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    # Execute with row factory
    cursor = db.execute(query, params)
    cursor.row_factory = lambda cursor, row: dict(
        zip(selected_fields, row)
    )
    
    return cursor.fetchall()
```

## Resource Management

### Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Create connection pool
engine = create_engine(
    'sqlite:////app/data/kasa_monitor.db',
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    connect_args={
        'check_same_thread': False,
        'timeout': 30
    }
)

# Use connection from pool
with engine.connect() as conn:
    result = conn.execute("SELECT * FROM devices")
```

### Memory Management

```python
import gc
import tracemalloc

class MemoryManager:
    def __init__(self, threshold_mb=500):
        self.threshold_bytes = threshold_mb * 1024 * 1024
        tracemalloc.start()
    
    def check_memory(self):
        """Check and clean memory if needed"""
        current, peak = tracemalloc.get_traced_memory()
        
        if current > self.threshold_bytes:
            # Force garbage collection
            gc.collect()
            
            # Clear caches
            self.clear_caches()
            
            # Log memory usage
            logging.warning(f"High memory usage: {current / 1024 / 1024:.2f} MB")
            
            # Get top memory consumers
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')[:10]
            
            for stat in top_stats:
                logging.debug(f"{stat}")
    
    def clear_caches(self):
        """Clear various caches"""
        # Clear query cache
        db.execute("PRAGMA shrink_memory")
        
        # Clear Python caches
        gc.collect()
        
        # Clear Redis cache if needed
        if redis_client.dbsize() > 10000:
            redis_client.flushdb()
```

### Thread Pool Optimization

```python
import concurrent.futures
import threading

class OptimizedThreadPool:
    def __init__(self, max_workers=None):
        if max_workers is None:
            # Optimal thread count
            max_workers = min(32, (os.cpu_count() or 1) * 4)
        
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="kasa-worker"
        )
        self.semaphore = threading.Semaphore(max_workers * 2)
    
    async def submit_task(self, func, *args, **kwargs):
        """Submit task with backpressure"""
        self.semaphore.acquire()
        try:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.executor, 
                func, 
                *args, 
                **kwargs
            )
            result = await future
            return result
        finally:
            self.semaphore.release()
```

## Network Optimization

### Batch API Requests

```python
@app.post("/api/batch")
async def batch_request(requests: List[dict]):
    """Process multiple API requests in one call"""
    results = []
    
    for req in requests:
        method = req.get('method', 'GET')
        path = req.get('path')
        data = req.get('data')
        
        # Process each request
        if method == 'GET':
            result = await process_get(path)
        elif method == 'POST':
            result = await process_post(path, data)
        else:
            result = {"error": "Unsupported method"}
        
        results.append({
            'id': req.get('id'),
            'result': result
        })
    
    return results
```

### WebSocket Optimization

```python
import asyncio
from typing import Set

class OptimizedWebSocketManager:
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.message_queue = asyncio.Queue()
        self.batch_size = 10
        self.batch_interval = 0.1  # 100ms
    
    async def broadcast_batch(self):
        """Batch WebSocket messages for efficiency"""
        while True:
            messages = []
            
            # Collect messages for batch_interval seconds
            try:
                deadline = asyncio.get_event_loop().time() + self.batch_interval
                while asyncio.get_event_loop().time() < deadline:
                    timeout = deadline - asyncio.get_event_loop().time()
                    message = await asyncio.wait_for(
                        self.message_queue.get(), 
                        timeout=timeout
                    )
                    messages.append(message)
                    
                    if len(messages) >= self.batch_size:
                        break
            except asyncio.TimeoutError:
                pass
            
            if messages:
                # Broadcast batch
                await self.send_batch(messages)
    
    async def send_batch(self, messages):
        """Send batched messages to all connections"""
        if not self.connections:
            return
        
        batch_data = json.dumps({
            'type': 'batch',
            'messages': messages
        })
        
        # Send to all connections concurrently
        tasks = [
            conn.send_text(batch_data) 
            for conn in self.connections
        ]
        
        # Handle disconnected clients
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for conn, result in zip(list(self.connections), results):
            if isinstance(result, Exception):
                self.connections.discard(conn)
```

## Performance Monitoring

### Performance Metrics

```python
import time
from contextlib import contextmanager

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    @contextmanager
    def measure(self, operation):
        """Measure operation performance"""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            
            if operation not in self.metrics:
                self.metrics[operation] = {
                    'count': 0,
                    'total_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0
                }
            
            stats = self.metrics[operation]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['min_time'] = min(stats['min_time'], duration)
            stats['max_time'] = max(stats['max_time'], duration)
    
    def get_stats(self):
        """Get performance statistics"""
        results = {}
        for operation, stats in self.metrics.items():
            results[operation] = {
                'count': stats['count'],
                'avg_time': stats['total_time'] / stats['count'],
                'min_time': stats['min_time'],
                'max_time': stats['max_time'],
                'total_time': stats['total_time']
            }
        return results

# Usage
monitor = PerformanceMonitor()

async def poll_device(device_ip):
    with monitor.measure(f"poll_{device_ip}"):
        # Perform polling
        pass
```

## Optimization Checklist

### Database
- [ ] Enable WAL mode
- [ ] Create appropriate indexes
- [ ] Implement data retention policy
- [ ] Use connection pooling
- [ ] Optimize queries with EXPLAIN

### Caching
- [ ] Implement Redis caching
- [ ] Use appropriate TTL values
- [ ] Cache API responses
- [ ] Implement cache warming
- [ ] Monitor cache hit rates

### Polling
- [ ] Use concurrent polling
- [ ] Implement adaptive intervals
- [ ] Batch device requests
- [ ] Cache recent readings
- [ ] Skip unchanged devices

### API
- [ ] Enable response compression
- [ ] Implement pagination
- [ ] Use field filtering
- [ ] Add request caching
- [ ] Optimize serialization

### Resources
- [ ] Set container limits
- [ ] Monitor memory usage
- [ ] Optimize thread pools
- [ ] Implement backpressure
- [ ] Profile CPU usage

## Troubleshooting

### High CPU Usage

```bash
# Profile CPU usage
docker exec kasa-monitor python -m cProfile -o profile.stats server.py

# Analyze profile
python -m pstats profile.stats
> sort cumulative
> stats 20

# Check process threads
docker exec kasa-monitor ps -eLf
```

### Memory Leaks

```python
# Memory profiling
import tracemalloc
import linecache

tracemalloc.start()

# ... run application ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

### Slow Queries

```sql
-- Enable query profiling
.timer on
EXPLAIN QUERY PLAN 
SELECT * FROM readings 
WHERE device_ip = '192.168.1.100' 
ORDER BY timestamp DESC 
LIMIT 100;

-- Check slow queries
SELECT 
    sql,
    COUNT(*) as executions,
    SUM(elapsed_time) as total_time,
    AVG(elapsed_time) as avg_time
FROM query_log
GROUP BY sql
ORDER BY total_time DESC
LIMIT 10;
```

## Related Pages

- [System Configuration](System-Configuration) - Performance settings
- [Database Schema](Database-Schema) - Database optimization
- [Monitoring & Alerts](Monitoring-Alerts) - Performance monitoring
- [Docker Deployment](Docker-Deployment) - Container optimization