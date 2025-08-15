"""
Prometheus metrics collection for Kasa Monitor
Provides comprehensive metrics for monitoring and alerting
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
    push_to_gateway,
)
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

logger = logging.getLogger(__name__)

# Create custom registry
registry = CollectorRegistry()

# System metrics
system_info = Info(
    "kasa_monitor_info", "Kasa Monitor application information", registry=registry
)

uptime_seconds = Gauge(
    "kasa_monitor_uptime_seconds",
    "Time since application started in seconds",
    registry=registry,
)

# Device metrics
devices_total = Gauge(
    "kasa_monitor_devices_total",
    "Total number of registered devices",
    ["device_type"],
    registry=registry,
)

devices_online = Gauge(
    "kasa_monitor_devices_online",
    "Number of online devices",
    ["device_type"],
    registry=registry,
)

device_discovery_duration = Histogram(
    "kasa_monitor_device_discovery_duration_seconds",
    "Time spent discovering devices",
    registry=registry,
)

device_command_total = Counter(
    "kasa_monitor_device_commands_total",
    "Total number of device commands sent",
    ["device_id", "command", "status"],
    registry=registry,
)

device_command_duration = Histogram(
    "kasa_monitor_device_command_duration_seconds",
    "Time spent executing device commands",
    ["device_id", "command"],
    registry=registry,
)

# Energy metrics
energy_consumption_watts = Gauge(
    "kasa_monitor_energy_consumption_watts",
    "Current power consumption in watts",
    ["device_id", "device_name"],
    registry=registry,
)

energy_total_kwh = Counter(
    "kasa_monitor_energy_total_kwh",
    "Total energy consumed in kWh",
    ["device_id", "device_name"],
    registry=registry,
)

energy_cost_total = Counter(
    "kasa_monitor_energy_cost_total",
    "Total energy cost",
    ["device_id", "device_name", "currency"],
    registry=registry,
)

# API metrics
http_requests_total = Counter(
    "kasa_monitor_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration = Histogram(
    "kasa_monitor_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=registry,
)

http_requests_in_progress = Gauge(
    "kasa_monitor_http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint"],
    registry=registry,
)

# WebSocket metrics
websocket_connections = Gauge(
    "kasa_monitor_websocket_connections",
    "Number of active WebSocket connections",
    registry=registry,
)

websocket_messages_total = Counter(
    "kasa_monitor_websocket_messages_total",
    "Total number of WebSocket messages",
    ["direction", "type"],
    registry=registry,
)

# Database metrics
database_connections_active = Gauge(
    "kasa_monitor_database_connections_active",
    "Number of active database connections",
    registry=registry,
)

database_query_duration = Histogram(
    "kasa_monitor_database_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    registry=registry,
)

database_errors_total = Counter(
    "kasa_monitor_database_errors_total",
    "Total number of database errors",
    ["error_type"],
    registry=registry,
)

# Cache metrics
cache_hits_total = Counter(
    "kasa_monitor_cache_hits_total",
    "Total number of cache hits",
    ["cache_type"],
    registry=registry,
)

cache_misses_total = Counter(
    "kasa_monitor_cache_misses_total",
    "Total number of cache misses",
    ["cache_type"],
    registry=registry,
)

cache_operations_total = Counter(
    "kasa_monitor_cache_operations_total",
    "Total number of cache operations",
    ["cache_type", "operation"],
    registry=registry,
)

# Alert metrics
alerts_active = Gauge(
    "kasa_monitor_alerts_active",
    "Number of active alerts",
    ["severity", "type"],
    registry=registry,
)

alerts_triggered_total = Counter(
    "kasa_monitor_alerts_triggered_total",
    "Total number of alerts triggered",
    ["severity", "type"],
    registry=registry,
)

# Schedule metrics
schedules_active = Gauge(
    "kasa_monitor_schedules_active", "Number of active schedules", registry=registry
)

schedule_executions_total = Counter(
    "kasa_monitor_schedule_executions_total",
    "Total number of schedule executions",
    ["schedule_id", "status"],
    registry=registry,
)

# Backup metrics
backup_size_bytes = Gauge(
    "kasa_monitor_backup_size_bytes",
    "Size of backups in bytes",
    ["backup_type"],
    registry=registry,
)

backup_duration_seconds = Histogram(
    "kasa_monitor_backup_duration_seconds",
    "Time spent creating backups",
    ["backup_type"],
    registry=registry,
)

backup_total = Counter(
    "kasa_monitor_backups_total",
    "Total number of backups created",
    ["backup_type", "status"],
    registry=registry,
)


class MetricsCollector:
    """Collects and manages Prometheus metrics"""

    def __init__(self):
        self.start_time = time.time()
        self.push_gateway_url = os.getenv("PROMETHEUS_PUSHGATEWAY_URL")

        # Set initial values
        system_info.info(
            {
                "version": os.getenv("APP_VERSION", "1.0.0"),
                "environment": os.getenv("ENVIRONMENT", "production"),
                "python_version": os.sys.version,
            }
        )

    def update_uptime(self):
        """Update uptime metric"""
        uptime_seconds.set(time.time() - self.start_time)

    def track_device_metrics(self, devices: list):
        """Update device-related metrics"""
        by_type = {}
        online_by_type = {}

        for device in devices:
            device_type = device.get("device_type", "unknown")
            by_type[device_type] = by_type.get(device_type, 0) + 1

            if device.get("is_online"):
                online_by_type[device_type] = online_by_type.get(device_type, 0) + 1

        # Update metrics
        for device_type, count in by_type.items():
            devices_total.labels(device_type=device_type).set(count)
            devices_online.labels(device_type=device_type).set(
                online_by_type.get(device_type, 0)
            )

    def track_energy_metrics(
        self, device_id: str, device_name: str, data: Dict[str, Any]
    ):
        """Update energy-related metrics"""
        if "power" in data:
            energy_consumption_watts.labels(
                device_id=device_id, device_name=device_name
            ).set(data["power"])

        if "total_energy" in data:
            energy_total_kwh.labels(device_id=device_id, device_name=device_name).inc(
                data.get("energy_delta", 0)
            )

        if "cost" in data:
            energy_cost_total.labels(
                device_id=device_id,
                device_name=device_name,
                currency=data.get("currency", "USD"),
            ).inc(data["cost"])

    def track_http_request(
        self, method: str, endpoint: str, status: int, duration: float
    ):
        """Track HTTP request metrics"""
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status)
        ).inc()

        http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def track_websocket_metrics(self, connections: int, messages: Dict[str, int]):
        """Track WebSocket metrics"""
        websocket_connections.set(connections)

        for (direction, msg_type), count in messages.items():
            websocket_messages_total.labels(direction=direction, type=msg_type).inc(
                count
            )

    def track_database_metrics(self, pool_stats: Dict[str, Any]):
        """Track database metrics"""
        if "active_connections" in pool_stats:
            database_connections_active.set(pool_stats["active_connections"])

    def track_cache_metrics(self, cache_stats: Dict[str, Any]):
        """Track cache metrics"""
        if "hits" in cache_stats:
            cache_hits_total.labels(cache_type="redis").inc(cache_stats["hits"])

        if "misses" in cache_stats:
            cache_misses_total.labels(cache_type="redis").inc(cache_stats["misses"])

    def track_alert_metrics(self, alerts: list):
        """Track alert metrics"""
        by_severity_type = {}

        for alert in alerts:
            if alert.get("is_active"):
                key = (
                    alert.get("severity", "unknown"),
                    alert.get("alert_type", "unknown"),
                )
                by_severity_type[key] = by_severity_type.get(key, 0) + 1

        for (severity, alert_type), count in by_severity_type.items():
            alerts_active.labels(severity=severity, type=alert_type).set(count)

    async def push_metrics(self):
        """Push metrics to Prometheus Pushgateway"""
        if not self.push_gateway_url:
            return

        try:
            push_to_gateway(
                self.push_gateway_url, job="kasa_monitor", registry=registry
            )
            logger.debug("Metrics pushed to Pushgateway")
        except Exception as e:
            logger.error(f"Failed to push metrics: {e}")

    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format"""
        self.update_uptime()
        return generate_latest(registry)


# Decorators for tracking metrics
def track_request_metrics(endpoint: Optional[str] = None):
    """Decorator to track HTTP request metrics"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            endpoint_name = endpoint or func.__name__
            method = kwargs.get("request", {}).method if "request" in kwargs else "GET"

            # Track in-progress requests
            http_requests_in_progress.labels(
                method=method, endpoint=endpoint_name
            ).inc()

            start_time = time.time()
            status = 200

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time

                # Update metrics
                http_requests_total.labels(
                    method=method, endpoint=endpoint_name, status=str(status)
                ).inc()

                http_request_duration.labels(
                    method=method, endpoint=endpoint_name
                ).observe(duration)

                http_requests_in_progress.labels(
                    method=method, endpoint=endpoint_name
                ).dec()

        return async_wrapper

    return decorator


def track_database_query(query_type: str):
    """Decorator to track database query metrics"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                database_errors_total.labels(error_type=type(e).__name__).inc()
                raise
            finally:
                duration = time.time() - start_time
                database_query_duration.labels(query_type=query_type).observe(duration)

        return async_wrapper

    return decorator


def track_device_command(device_id: str, command: str):
    """Decorator to track device command metrics"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failure"
                raise
            finally:
                duration = time.time() - start_time

                device_command_total.labels(
                    device_id=device_id, command=command, status=status
                ).inc()

                device_command_duration.labels(
                    device_id=device_id, command=command
                ).observe(duration)

        return async_wrapper

    return decorator


# Global metrics collector
metrics_collector = MetricsCollector()

# API router for metrics endpoint
router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    metrics_data = metrics_collector.get_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Background task for periodic metric updates
async def metrics_background_task():
    """Background task for updating and pushing metrics"""
    while True:
        try:
            # Update system metrics
            metrics_collector.update_uptime()

            # Push to Pushgateway if configured
            await metrics_collector.push_metrics()

            await asyncio.sleep(60)  # Update every minute
        except Exception as e:
            logger.error(f"Metrics background task error: {e}")
            await asyncio.sleep(5)
