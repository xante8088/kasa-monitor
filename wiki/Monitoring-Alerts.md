# Monitoring & Alerts

Comprehensive guide for monitoring Kasa Monitor system health and configuring alerts.

## Monitoring Overview

```
┌─────────────────────────────────────┐
│      Monitoring Components          │
├─────────────────────────────────────┤
│  1. System Metrics                  │
│  2. Device Monitoring               │
│  3. Energy Alerts                   │
│  4. Cost Notifications              │
│  5. Health Checks                   │
└─────────────────────────────────────┘
```

## Quick Setup

### Enable Basic Monitoring

```bash
# Environment variables
MONITORING_ENABLED=true
METRICS_PORT=9090
ALERT_EMAIL=admin@example.com
ALERT_THRESHOLD_WATTS=1500
```

### Docker Compose with Monitoring

```yaml
services:
  kasa-monitor:
    environment:
      - MONITORING_ENABLED=true
      - METRICS_PORT=9090
    
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## System Metrics

### Health Check Endpoints

```python
# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "uptime": get_uptime(),
        "version": "1.0.0"
    }

# Detailed health
@app.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "components": {
            "database": check_database(),
            "redis": check_redis(),
            "influxdb": check_influxdb(),
            "devices": check_devices()
        },
        "metrics": {
            "memory_usage_mb": get_memory_usage(),
            "cpu_percent": get_cpu_usage(),
            "disk_usage_gb": get_disk_usage(),
            "active_connections": get_connection_count()
        }
    }

# Readiness check
@app.get("/ready")
async def readiness_check():
    if not all([database_ready(), cache_ready()]):
        raise HTTPException(status_code=503)
    return {"ready": True}
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
http_requests = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
http_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_devices = Gauge('kasa_devices_active', 'Number of active devices')
total_power = Gauge('kasa_total_power_watts', 'Total power consumption')

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")

# Track metrics
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    http_requests.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    http_duration.observe(duration)
    
    return response
```

### Custom Metrics

```python
# Device metrics
device_power = Gauge('device_power_watts', 'Device power consumption', ['device_ip', 'device_name'])
device_energy = Counter('device_energy_kwh', 'Device energy consumption', ['device_ip', 'device_name'])
device_uptime = Gauge('device_uptime_seconds', 'Device uptime', ['device_ip', 'device_name'])

# Update metrics
async def update_device_metrics(device_ip, data):
    device_power.labels(
        device_ip=device_ip,
        device_name=data['name']
    ).set(data['power_w'])
    
    device_energy.labels(
        device_ip=device_ip,
        device_name=data['name']
    ).inc(data['energy_kwh'])
```

## Alert Configuration

### Alert Rules

**config/alerts.yml:**
```yaml
alerts:
  # Power alerts
  high_power:
    enabled: true
    threshold: 1500  # watts
    duration: 300  # seconds
    severity: warning
    channels: [email, push]
    message: "Device {device_name} exceeding {threshold}W for {duration}s"
  
  # Energy alerts
  daily_limit:
    enabled: true
    threshold: 50  # kWh
    severity: info
    channels: [email]
    message: "Daily energy limit exceeded: {current_kwh} kWh"
  
  # Cost alerts
  cost_threshold:
    enabled: true
    daily_limit: 10  # currency
    monthly_limit: 300
    severity: warning
    channels: [email, sms]
    message: "Cost alert: ${current_cost} (limit: ${limit})"
  
  # Device alerts
  device_offline:
    enabled: true
    timeout: 300  # seconds
    severity: error
    channels: [email, push]
    message: "Device {device_name} is offline"
  
  # System alerts
  high_cpu:
    enabled: true
    threshold: 80  # percent
    duration: 300
    severity: critical
    channels: [email, sms]
    message: "High CPU usage: {cpu_percent}%"
```

### Alert Manager

```python
import asyncio
from datetime import datetime, timedelta

class AlertManager:
    def __init__(self):
        self.alerts = {}
        self.alert_history = []
        self.channels = {
            'email': EmailChannel(),
            'sms': SMSChannel(),
            'push': PushChannel(),
            'webhook': WebhookChannel()
        }
    
    async def check_alerts(self):
        """Main alert checking loop"""
        while True:
            try:
                await self.check_power_alerts()
                await self.check_device_alerts()
                await self.check_cost_alerts()
                await self.check_system_alerts()
            except Exception as e:
                logging.error(f"Alert check error: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def check_power_alerts(self):
        """Check power consumption alerts"""
        devices = await get_all_devices()
        
        for device in devices:
            if device['power_w'] > config['high_power']['threshold']:
                await self.trigger_alert(
                    alert_type='high_power',
                    device=device,
                    value=device['power_w']
                )
    
    async def trigger_alert(self, alert_type, **kwargs):
        """Trigger an alert"""
        alert_config = config['alerts'][alert_type]
        
        if not alert_config['enabled']:
            return
        
        # Check if already alerted
        alert_key = f"{alert_type}_{kwargs.get('device', {}).get('device_ip', 'system')}"
        if alert_key in self.alerts:
            last_alert = self.alerts[alert_key]
            if (datetime.now() - last_alert['timestamp']).seconds < 3600:
                return  # Don't re-alert within an hour
        
        # Format message
        message = alert_config['message'].format(**kwargs)
        
        # Send to channels
        for channel in alert_config['channels']:
            await self.channels[channel].send(
                message=message,
                severity=alert_config['severity'],
                data=kwargs
            )
        
        # Record alert
        self.alerts[alert_key] = {
            'timestamp': datetime.now(),
            'type': alert_type,
            'message': message,
            'data': kwargs
        }
        
        # Save to database
        await self.save_alert(alert_type, message, kwargs)
```

## Notification Channels

### Email Notifications

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailChannel:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL')
        self.to_emails = os.getenv('ALERT_EMAILS', '').split(',')
    
    async def send(self, message, severity, data):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{severity.upper()}] Kasa Monitor Alert"
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to_emails)
        
        # HTML email body
        html = f"""
        <html>
          <body>
            <h2>Kasa Monitor Alert</h2>
            <p><strong>Severity:</strong> {severity}</p>
            <p><strong>Message:</strong> {message}</p>
            <p><strong>Time:</strong> {datetime.now()}</p>
            <hr>
            <p><small>Sent from Kasa Monitor</small></p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
```

### Push Notifications

```python
import requests

class PushChannel:
    def __init__(self):
        self.pushover_token = os.getenv('PUSHOVER_TOKEN')
        self.pushover_user = os.getenv('PUSHOVER_USER')
    
    async def send(self, message, severity, data):
        if not self.pushover_token:
            return
        
        priority = {
            'info': -1,
            'warning': 0,
            'error': 1,
            'critical': 2
        }.get(severity, 0)
        
        requests.post('https://api.pushover.net/1/messages.json', data={
            'token': self.pushover_token,
            'user': self.pushover_user,
            'message': message,
            'title': 'Kasa Monitor Alert',
            'priority': priority,
            'timestamp': int(datetime.now().timestamp())
        })
```

### Webhook Notifications

```python
class WebhookChannel:
    def __init__(self):
        self.webhook_url = os.getenv('WEBHOOK_URL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    
    async def send(self, message, severity, data):
        # Generic webhook
        if self.webhook_url:
            requests.post(self.webhook_url, json={
                'message': message,
                'severity': severity,
                'timestamp': datetime.now().isoformat(),
                'data': data
            })
        
        # Slack
        if self.slack_webhook:
            color = {
                'info': '#36a64f',
                'warning': '#ff9900',
                'error': '#ff0000',
                'critical': '#990000'
            }.get(severity, '#808080')
            
            requests.post(self.slack_webhook, json={
                'attachments': [{
                    'color': color,
                    'title': 'Kasa Monitor Alert',
                    'text': message,
                    'timestamp': int(datetime.now().timestamp())
                }]
            })
        
        # Discord
        if self.discord_webhook:
            requests.post(self.discord_webhook, json={
                'embeds': [{
                    'title': 'Kasa Monitor Alert',
                    'description': message,
                    'color': 0xff0000 if severity in ['error', 'critical'] else 0x00ff00
                }]
            })
```

## Grafana Dashboards

### Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Kasa Monitor Dashboard",
    "panels": [
      {
        "id": 1,
        "title": "Total Power Consumption",
        "type": "graph",
        "targets": [{
          "expr": "sum(device_power_watts)"
        }]
      },
      {
        "id": 2,
        "title": "Device Status",
        "type": "stat",
        "targets": [{
          "expr": "kasa_devices_active"
        }]
      },
      {
        "id": 3,
        "title": "Daily Energy Cost",
        "type": "gauge",
        "targets": [{
          "expr": "sum(rate(device_energy_kwh[24h])) * 0.12"
        }]
      },
      {
        "id": 4,
        "title": "Alert History",
        "type": "table",
        "targets": [{
          "expr": "increase(alerts_triggered_total[1h])"
        }]
      }
    ]
  }
}
```

### Import Dashboard

```bash
# Via API
curl -X POST http://admin:admin@localhost:3001/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboard.json

# Via UI
# 1. Go to Grafana → Dashboards → Import
# 2. Upload JSON file or paste JSON
# 3. Select data source (Prometheus)
# 4. Click Import
```

## Alert Templates

### Power Spike Alert

```python
async def check_power_spike(device_ip):
    # Get recent readings
    history = await get_device_history(device_ip, minutes=5)
    
    if not history:
        return
    
    avg_power = sum(h['power_w'] for h in history) / len(history)
    current_power = history[-1]['power_w']
    
    # Check for 50% spike
    if current_power > avg_power * 1.5:
        await trigger_alert(
            'power_spike',
            device_ip=device_ip,
            current=current_power,
            average=avg_power,
            spike_percent=((current_power - avg_power) / avg_power) * 100
        )
```

### Daily Report

```python
async def send_daily_report():
    """Send daily energy report"""
    report_data = await generate_daily_report()
    
    html = f"""
    <h2>Daily Energy Report - {datetime.now().date()}</h2>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Total Energy</td><td>{report_data['total_kwh']:.2f} kWh</td></tr>
      <tr><td>Total Cost</td><td>${report_data['total_cost']:.2f}</td></tr>
      <tr><td>Peak Power</td><td>{report_data['peak_power']:.0f} W</td></tr>
      <tr><td>Active Devices</td><td>{report_data['active_devices']}</td></tr>
    </table>
    
    <h3>Top Consumers</h3>
    <ol>
    {"".join(f"<li>{d['name']}: {d['kwh']:.2f} kWh</li>" for d in report_data['top_consumers'][:5])}
    </ol>
    """
    
    await send_email(
        subject="Daily Energy Report",
        body=html,
        recipients=config['report_recipients']
    )
```

## Monitoring Scripts

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

URL="http://localhost:8000/health"
MAX_RETRIES=3
RETRY_DELAY=5

for i in $(seq 1 $MAX_RETRIES); do
    response=$(curl -s -o /dev/null -w "%{http_code}" $URL)
    
    if [ $response -eq 200 ]; then
        echo "✅ Health check passed"
        exit 0
    fi
    
    echo "⚠️ Health check failed (attempt $i/$MAX_RETRIES)"
    
    if [ $i -lt $MAX_RETRIES ]; then
        sleep $RETRY_DELAY
    fi
done

echo "❌ Health check failed after $MAX_RETRIES attempts"
# Send alert
curl -X POST $ALERT_WEBHOOK -d '{"message": "Kasa Monitor health check failed"}'
exit 1
```

### Metrics Collection

```python
#!/usr/bin/env python3
# collect-metrics.py

import psutil
import sqlite3
import json
from datetime import datetime

def collect_system_metrics():
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'network_io': psutil.net_io_counters()._asdict(),
        'process_count': len(psutil.pids())
    }
    
    # Save to database
    conn = sqlite3.connect('/app/data/metrics.db')
    conn.execute("""
        INSERT INTO system_metrics (timestamp, data)
        VALUES (?, ?)
    """, (metrics['timestamp'], json.dumps(metrics)))
    conn.commit()
    
    # Check thresholds
    if metrics['cpu_percent'] > 80:
        send_alert('High CPU usage', metrics)
    
    if metrics['memory_percent'] > 90:
        send_alert('High memory usage', metrics)
    
    return metrics

if __name__ == '__main__':
    metrics = collect_system_metrics()
    print(json.dumps(metrics, indent=2))
```

## Alert History

### Database Schema

```sql
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    device_ip TEXT,
    data JSON,
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_by INTEGER,
    acknowledged_at TIMESTAMP,
    resolved BOOLEAN DEFAULT 0,
    resolved_at TIMESTAMP,
    
    FOREIGN KEY (acknowledged_by) REFERENCES users(id)
);

CREATE INDEX idx_alerts_timestamp ON alert_history(timestamp);
CREATE INDEX idx_alerts_type ON alert_history(alert_type);
CREATE INDEX idx_alerts_device ON alert_history(device_ip);
```

### Alert API

```python
# Get alerts
@app.get("/api/alerts")
async def get_alerts(
    limit: int = 100,
    offset: int = 0,
    severity: str = None,
    device_ip: str = None
):
    query = "SELECT * FROM alert_history WHERE 1=1"
    params = []
    
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    
    if device_ip:
        query += " AND device_ip = ?"
        params.append(device_ip)
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    alerts = db.execute(query, params).fetchall()
    return alerts

# Acknowledge alert
@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    user: User = Depends(get_current_user)
):
    db.execute("""
        UPDATE alert_history 
        SET acknowledged = 1,
            acknowledged_by = ?,
            acknowledged_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (user.id, alert_id))
    
    return {"status": "acknowledged"}
```

## Monitoring Best Practices

1. **Set Appropriate Thresholds** - Avoid alert fatigue
2. **Use Alert Priorities** - Critical vs informational
3. **Implement Rate Limiting** - Prevent alert storms
4. **Test Alert Channels** - Ensure notifications work
5. **Regular Review** - Adjust thresholds based on patterns
6. **Document Runbooks** - Response procedures for alerts
7. **Archive Old Alerts** - Maintain performance

## Troubleshooting

### Alerts Not Firing

```bash
# Check alert configuration
cat /app/config/alerts.yml

# Test alert channel
docker exec kasa-monitor python -c "
from alert_manager import test_alert
test_alert('email')
"

# Check logs
docker logs kasa-monitor | grep -i alert
```

### Missing Metrics

```bash
# Verify metrics endpoint
curl http://localhost:9090/metrics

# Check Prometheus scraping
curl http://localhost:9090/api/v1/targets

# Test metric generation
docker exec kasa-monitor python -c "
from metrics import update_metrics
update_metrics()
"
```

## Related Pages

- [System Configuration](System-Configuration) - Alert configuration
- [Dashboard Overview](Dashboard-Overview) - Monitoring UI
- [API Documentation](API-Documentation) - Alert APIs
- [Performance Tuning](Performance-Tuning) - Metric optimization