# Kasa Monitor - Local Testing Guide

## 🚀 Quick Start

### Option 1: Using the Shell Script (Recommended)
```bash
# Make sure you're in the kasa-monitor directory
cd /Users/ryan.hein/kasaweb/kasa-monitor

# Run the startup script
./start-local.sh
```

### Option 2: Using Docker Compose
```bash
# Start all services with Docker
docker-compose -f docker-compose.local.yml up

# Or run in background
docker-compose -f docker-compose.local.yml up -d
```

### Option 3: Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (optional, for caching)
redis-server

# Run the application
cd backend
python main.py
```

## 📍 Access Points

Once running, access the application at:

- **Test Interface**: http://localhost:5272/test
  - Interactive WebSocket testing
  - API endpoint testing
  - Real-time metrics display

- **API Documentation**: http://localhost:5272/docs
  - Interactive Swagger UI
  - Try out all API endpoints

- **Health Dashboard**: http://localhost:5272/health/detailed
  - Comprehensive system health status
  - Component health checks

- **Metrics**: http://localhost:5272/metrics
  - Prometheus-format metrics
  - Performance statistics

## 🧪 Testing Features

### 1. Health Monitoring
Visit http://localhost:5272/test and click "Test Health Check" to see:
- Database connectivity
- Redis status
- Filesystem health
- System resources

### 2. WebSocket Real-time Updates
1. Open http://localhost:5272/test
2. Click "Connect" to establish WebSocket connection
3. Click "Subscribe to All" to receive all events
4. Click "Send Ping" to test bi-directional communication

### 3. Database Backup
Click "Create Test Backup" on the test page to:
- Create a compressed backup
- View backup metadata
- Test backup/restore functionality

### 4. Caching
Click "Test Cache Operation" to:
- View cache statistics
- See hit/miss ratios
- Monitor cache performance

### 5. API Endpoints

#### Health Endpoints
```bash
# Basic health check
curl http://localhost:5272/health

# Detailed health status
curl http://localhost:5272/health/detailed

# Readiness probe
curl http://localhost:5272/health/ready
```

#### Database Management
```bash
# List backups
curl http://localhost:5272/api/database/backups

# Create backup
curl -X POST http://localhost:5272/api/database/backup \
  -H "Content-Type: application/json" \
  -d '{"backup_type": "manual", "compress": true}'

# Database statistics
curl http://localhost:5272/api/database/stats
```

#### Data Management
```bash
# Export devices to CSV
curl http://localhost:5272/api/data/export/devices/csv -o devices.csv

# Cache statistics
curl http://localhost:5272/api/data/cache/stats

# Data aggregation status
curl http://localhost:5272/api/data/aggregation/status
```

## 🐛 Troubleshooting

### Port Already in Use
If port 5272 is already in use:
```bash
# Find process using port 5272
lsof -i :5272

# Kill the process
kill -9 <PID>
```

### Redis Connection Failed
Cache features will work without Redis, but with reduced functionality:
```bash
# Install Redis (macOS)
brew install redis
brew services start redis

# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server
sudo systemctl start redis
```

### Module Import Errors
```bash
# Ensure you're in virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## 📊 Monitoring Stack (Optional)

To run the full monitoring stack with Prometheus and Grafana:

```bash
# Start monitoring services
docker-compose -f docker-compose.monitoring.yml up -d

# Access points:
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
# - Redis Commander: http://localhost:8081
```

## 🔍 What to Test

1. **WebSocket Connections**
   - Real-time message delivery
   - Topic subscriptions
   - Connection stability

2. **Health Checks**
   - All components reporting
   - Resource usage monitoring
   - Error detection

3. **Database Operations**
   - Backup creation
   - Backup restoration
   - Connection pooling

4. **Cache Performance**
   - Hit/miss ratios
   - Cache invalidation
   - Multi-level caching

5. **Data Export**
   - CSV generation
   - PDF reports
   - Excel exports

6. **Metrics Collection**
   - Prometheus scraping
   - Custom metrics
   - Performance tracking

## 📝 Notes

- The test environment uses SQLite by default
- Redis is optional but recommended for full functionality
- All data is stored in `./data` and `./backups` directories
- Logs are available in the console output
- The application auto-reloads on code changes (when using start-local.sh)

## 🛑 Stopping the Application

- **Shell Script**: Press `Ctrl+C`
- **Docker Compose**: `docker-compose -f docker-compose.local.yml down`
- **Manual**: Press `Ctrl+C` in the terminal running the application

## 📚 Next Steps

1. Explore the API documentation at http://localhost:5272/docs
2. Test WebSocket functionality at http://localhost:5272/test
3. Monitor metrics at http://localhost:5272/metrics
4. Check system health at http://localhost:5272/health/detailed
5. Review the implemented features in MISSING_FEATURES.md