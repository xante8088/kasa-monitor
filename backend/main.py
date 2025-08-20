"""
Main application entry point for Kasa Monitor
Integrates all implemented features for local testing
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from data_management_api import router as data_management_router
from database_api import router as database_router
from database_pool import init_pool
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from health_monitor import health_monitor
from health_monitor import router as health_router
from prometheus_metrics import metrics_background_task
from prometheus_metrics import router as metrics_router
from redis_cache import close_redis_cache, init_redis_cache

# from ssl_api import router as ssl_router
from websocket_manager import websocket_background_task, websocket_endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import existing server functionality
try:
    from server import app as existing_app

    USE_EXISTING = True
except ImportError:
    USE_EXISTING = False
    logger.warning("Could not import existing server.py, creating new app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Kasa Monitor application...")

    # Initialize database pool
    try:
        db_pool = init_pool()  # Use defaults
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")

    # Initialize Redis cache
    try:
        await init_redis_cache(default_ttl=3600, max_connections=50)
        logger.info("Redis cache initialized")
    except Exception as e:
        logger.warning(f"Redis cache not available: {e}")

    # Initialize health monitor
    try:
        await health_monitor.initialize()
        logger.info("Health monitor initialized")
    except Exception as e:
        logger.error(f"Failed to initialize health monitor: {e}")

    # Start background tasks
    tasks = []
    tasks.append(asyncio.create_task(metrics_background_task()))
    tasks.append(asyncio.create_task(websocket_background_task()))
    logger.info("Background tasks started")

    yield

    # Cleanup
    logger.info("Shutting down Kasa Monitor application...")

    # Cancel background tasks
    for task in tasks:
        task.cancel()

    # Close Redis cache
    await close_redis_cache()

    # Close database pool
    if "db_pool" in locals():
        await db_pool.async_close()

    logger.info("Cleanup completed")


# Create FastAPI app
if not USE_EXISTING:
    app = FastAPI(
        title="Kasa Monitor",
        description="Smart home device monitoring system with comprehensive features",
        version="2.0.0",
        lifespan=lifespan,
    )
else:
    app = existing_app

# Add secure CORS middleware
try:
    from security_fixes.critical.cors_fix import setup_cors_security
    cors_config = setup_cors_security(app)
    logger.info(f"Secure CORS configured for environment: {cors_config.environment}")
except ImportError:
    logger.warning("CORS security fix not available, using basic CORS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Include all routers
app.include_router(health_router, tags=["health"])
app.include_router(metrics_router, prefix="", tags=["metrics"])
app.include_router(database_router, tags=["database"])
app.include_router(data_management_router, tags=["data"])
# app.include_router(ssl_router, tags=["ssl"])


# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_route(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket_endpoint(websocket, client_id)


# Test page for WebSocket
@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """Simple test page for WebSocket and features"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kasa Monitor Test Page</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 { color: #333; }
            h2 { color: #666; }
            .status {
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
            }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .message {
                padding: 8px;
                margin: 5px 0;
                background: #f8f9fa;
                border-left: 3px solid #007bff;
                font-family: monospace;
                font-size: 12px;
            }
            button {
                background: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                margin: 5px;
            }
            button:hover { background: #0056b3; }
            button:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
                margin: 20px 0;
            }
            .metric {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 4px;
                text-align: center;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #007bff;
            }
            .metric-label {
                color: #666;
                margin-top: 5px;
            }
            #messages {
                max-height: 300px;
                overflow-y: auto;
                border: 1px solid #dee2e6;
                padding: 10px;
                border-radius: 4px;
            }
            .endpoints {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 10px;
            }
            .endpoint {
                background: #e9ecef;
                padding: 10px;
                border-radius: 4px;
            }
            .endpoint a {
                color: #007bff;
                text-decoration: none;
            }
            .endpoint a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <h1>🏠 Kasa Monitor Test Page</h1>

        <div class="container">
            <h2>System Status</h2>
            <div class="metrics" id="metrics">
                <div class="metric">
                    <div class="metric-value" id="uptime">-</div>
                    <div class="metric-label">Uptime</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="connections">0</div>
                    <div class="metric-label">WebSocket Connections</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="health">-</div>
                    <div class="metric-label">Health Status</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="cache">-</div>
                    <div class="metric-label">Cache Hit Rate</div>
                </div>
            </div>
        </div>

        <div class="container">
            <h2>API Endpoints</h2>
            <div class="endpoints">
                <div class="endpoint">
                    <strong>Health & Monitoring</strong><br>
                    <a href="/health" target="_blank">Basic Health</a><br>
                    <a href="/health/ready" target="_blank">Readiness</a><br>
                    <a href="/health/detailed" target="_blank">Detailed Health</a>
                </div>
                <div class="endpoint">
                    <strong>Metrics</strong><br>
                    <a href="/metrics" target="_blank">Prometheus Metrics</a>
                </div>
                <div class="endpoint">
                    <strong>Database</strong><br>
                    <a href="/api/database/health" target="_blank">DB Health</a><br>
                    <a href="/api/database/stats" target="_blank">DB Stats</a><br>
                    <a href="/api/database/backups" target="_blank">Backups</a>
                </div>
                <div class="endpoint">
                    <strong>Data Management</strong><br>
                    <a href="/api/data/export/devices/csv" target="_blank">
                    Export Devices CSV</a><br>
                    <a href="/api/data/cache/stats" target="_blank">Cache Stats</a><br>
                    <a href="/api/data/aggregation/status" target="_blank">
                    Aggregation Status</a>
                </div>
                <div class="endpoint">
                    <strong>Documentation</strong><br>
                    <a href="/docs" target="_blank">Swagger UI</a><br>
                    <a href="/redoc" target="_blank">ReDoc</a>
                </div>
            </div>
        </div>

        <div class="container">
            <h2>WebSocket Test</h2>
            <div class="status disconnected" id="status">Disconnected</div>
            <div>
                <button id="connect">Connect</button>
                <button id="disconnect" disabled>Disconnect</button>
                <button id="subscribe" disabled>Subscribe to All</button>
                <button id="ping" disabled>Send Ping</button>
                <button id="clear">Clear Messages</button>
            </div>
            <h3>Messages</h3>
            <div id="messages"></div>
        </div>

        <div class="container">
            <h2>Test Operations</h2>
            <div>
                <button onclick="testHealthCheck()">Test Health Check</button>
                <button onclick="testBackup()">Create Test Backup</button>
                <button onclick="testCache()">Test Cache Operation</button>
                <button onclick="testMetrics()">Fetch Metrics</button>
            </div>
            <div id="testResults" style="margin-top: 20px;"></div>
        </div>

        <script>
            let ws = null;
            let clientId = 'test-' + Math.random().toString(36).substr(2, 9);

            function updateMetrics() {
                // Fetch health status
                fetch('/health/detailed')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('health').textContent = data.status;
                        if (data.uptime_human) {
                            document.getElementById('uptime').textContent =
                                data.uptime_human;
                        }
                    });

                // Fetch cache stats
                fetch('/api/data/cache/stats')
                    .then(r => r.json())
                    .then(data => {
                        if (data.hit_ratio !== undefined) {
                            document.getElementById('cache').textContent =
                                (data.hit_ratio * 100).toFixed(1) + '%';
                        }
                    })
                    .catch(() => {
                        document.getElementById('cache').textContent = 'N/A';
                    });
            }

            function addMessage(message, type = 'message') {
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                messageDiv.textContent = new Date().toLocaleTimeString() +
                    ' - ' + message;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            document.getElementById('connect').onclick = function() {
                ws = new WebSocket('ws://localhost:5272/ws/' + clientId);

                ws.onopen = function() {
                    document.getElementById('status').textContent =
                        'Connected (ID: ' + clientId + ')';
                    document.getElementById('status').className =
                        'status connected';
                    document.getElementById('connect').disabled = true;
                    document.getElementById('disconnect').disabled = false;
                    document.getElementById('subscribe').disabled = false;
                    document.getElementById('ping').disabled = false;
                    addMessage('Connected to WebSocket');
                    document.getElementById('connections').textContent = '1';
                };

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage(JSON.stringify(data, null, 2));
                };

                ws.onerror = function(error) {
                    addMessage('Error: ' + error, 'error');
                };

                ws.onclose = function() {
                    document.getElementById('status').textContent =
                        'Disconnected';
                    document.getElementById('status').className =
                        'status disconnected';
                    document.getElementById('connect').disabled = false;
                    document.getElementById('disconnect').disabled = true;
                    document.getElementById('subscribe').disabled = true;
                    document.getElementById('ping').disabled = true;
                    addMessage('Disconnected from WebSocket');
                    document.getElementById('connections').textContent = '0';
                };
            };

            document.getElementById('disconnect').onclick = function() {
                if (ws) {
                    ws.close();
                }
            };

            document.getElementById('subscribe').onclick = function() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'subscribe',
                        topics: ['devices:all', 'energy:all', 'alerts:all',
                                'system:events']
                    }));
                    addMessage('Subscribed to all topics');
                }
            };

            document.getElementById('ping').onclick = function() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type: 'ping'}));
                    addMessage('Sent ping');
                }
            };

            document.getElementById('clear').onclick = function() {
                document.getElementById('messages').innerHTML = '';
            };

            function testHealthCheck() {
                const results = document.getElementById('testResults');
                results.innerHTML = '<p>Running health check...</p>';

                fetch('/health/detailed')
                    .then(r => r.json())
                    .then(data => {
                        results.innerHTML = '<h3>Health Check Results</h3><pre>' +
                            JSON.stringify(data, null, 2) + '</pre>';
                    })
                    .catch(err => {
                        results.innerHTML = '<p style="color: red;">Error: ' +
                            err + '</p>';
                    });
            }

            function testBackup() {
                const results = document.getElementById('testResults');
                results.innerHTML = '<p>Creating backup...</p>';

                fetch('/api/database/backup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        backup_type: 'manual',
                        description: 'Test backup from web interface',
                        compress: true,
                        encrypt: false
                    })
                })
                .then(r => r.json())
                .then(data => {
                    results.innerHTML = '<h3>Backup Created</h3><pre>' +
                        JSON.stringify(data, null, 2) + '</pre>';
                })
                .catch(err => {
                    results.innerHTML = '<p style="color: red;">Error: ' +
                        err + '</p>';
                });
            }

            function testCache() {
                const results = document.getElementById('testResults');
                results.innerHTML = '<p>Testing cache...</p>';

                fetch('/api/data/cache/stats')
                    .then(r => r.json())
                    .then(data => {
                        results.innerHTML = '<h3>Cache Statistics</h3><pre>' +
                            JSON.stringify(data, null, 2) + '</pre>';
                    })
                    .catch(err => {
                        results.innerHTML = '<p style="color: red;">Error: ' +
                            err + '</p>';
                    });
            }

            function testMetrics() {
                const results = document.getElementById('testResults');
                results.innerHTML = '<p>Fetching metrics...</p>';

                fetch('/metrics')
                    .then(r => r.text())
                    .then(data => {
                        // Show first 50 lines of metrics
                        const lines = data.split('\\n').slice(0, 50);
                        results.innerHTML =
                            '<h3>Prometheus Metrics (first 50 lines)</h3><pre>' +
                            lines.join('\\n') + '\\n...</pre>';
                    })
                    .catch(err => {
                        results.innerHTML = '<p style="color: red;">Error: ' +
                            err + '</p>';
                    });
            }

            // Update metrics every 5 seconds
            updateMetrics();
            setInterval(updateMetrics, 5000);
        </script>
    </body>
    </html>
    """


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with links to all features"""
    return {
        "message": "Welcome to Kasa Monitor v2.0",
        "features": {
            "health": "/health/detailed",
            "metrics": "/metrics",
            "test_page": "/test",
            "api_docs": "/docs",
            "websocket": "ws://localhost:5272/ws/{client_id}",
        },
        "implemented_sections": [
            "Core Infrastructure (Health, Redis, WebSocket, Prometheus, Grafana)",
            "Database Features (Backup/Restore, Migrations, Connection Pooling)",
            "Data Management Features (Export, Aggregation, Caching)",
        ],
    }


if __name__ == "__main__":
    # Set environment variables for local testing
    os.environ.setdefault("DATABASE_PATH", "data/kasa_monitor.db")
    os.environ.setdefault("BACKUP_DIR", "backups")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("APP_VERSION", "2.0.0")
    os.environ.setdefault("ENVIRONMENT", "development")

    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("backups", exist_ok=True)
    os.makedirs("ssl", exist_ok=True)

    # Run the application
    uvicorn.run("main:app", host="0.0.0.0", port=5272, reload=True, log_level="info")
