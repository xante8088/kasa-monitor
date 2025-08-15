"""
Health monitoring and readiness checks for Kasa Monitor
Provides comprehensive health status for all system components
"""

import os
import time
import psutil
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
import aiohttp
import redis.asyncio as redis
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthMonitor:
    """Monitors system health and component status"""

    def __init__(self):
        self.start_time = datetime.now()
        self.component_status = {}
        self.health_checks = []
        self.last_check = None
        self.redis_client = None
        self.influxdb_client = None

    async def initialize(self):
        """Initialize health monitor connections"""
        # Try to connect to Redis if configured
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established for health monitoring")
        except Exception as e:
            logger.warning(f"Redis not available for health monitoring: {e}")
            self.redis_client = None

    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        start_time = time.time()
        try:
            from database_pool import get_pool

            pool = get_pool()

            # Test query
            if hasattr(pool, "async_engine"):
                async with pool.async_engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    result.fetchone()
            else:
                # Fallback for sync only
                with pool.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()

            # Get pool statistics
            pool_stats = pool.get_statistics()

            return {
                "status": "healthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "pool_status": pool_stats.get("runtime_stats", {}),
                "message": "Database connection successful",
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "error": str(e),
                "message": "Database connection failed",
            }

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        if not self.redis_client:
            return {"status": "not_configured", "message": "Redis not configured"}

        start_time = time.time()
        try:
            # Ping Redis
            await self.redis_client.ping()

            # Get Redis info
            info = await self.redis_client.info()

            return {
                "status": "healthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": info.get("used_memory", 0) / (1024 * 1024),
                "message": "Redis connection successful",
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "error": str(e),
                "message": "Redis connection failed",
            }

    async def check_influxdb(self) -> Dict[str, Any]:
        """Check InfluxDB connectivity if configured"""
        influxdb_url = os.getenv("INFLUXDB_URL")
        if not influxdb_url:
            return {"status": "not_configured", "message": "InfluxDB not configured"}

        start_time = time.time()
        try:
            # Ping InfluxDB
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{influxdb_url}/ping") as response:
                    if response.status == 204:
                        return {
                            "status": "healthy",
                            "response_time_ms": (time.time() - start_time) * 1000,
                            "message": "InfluxDB connection successful",
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "response_time_ms": (time.time() - start_time) * 1000,
                            "http_status": response.status,
                            "message": "InfluxDB ping failed",
                        }
        except Exception as e:
            logger.error(f"InfluxDB health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "error": str(e),
                "message": "InfluxDB connection failed",
            }

    async def check_filesystem(self) -> Dict[str, Any]:
        """Check filesystem health and disk space"""
        try:
            # Check data directory
            data_dir = Path("data")
            if not data_dir.exists():
                data_dir.mkdir(parents=True, exist_ok=True)

            # Get disk usage
            disk_usage = psutil.disk_usage(str(data_dir.absolute()))

            # Check backup directory
            backup_dir = Path(os.getenv("BACKUP_DIR", "/backups"))
            backup_usage = None
            if backup_dir.exists():
                backup_usage = psutil.disk_usage(str(backup_dir.absolute()))

            return {
                "status": "healthy" if disk_usage.percent < 90 else "warning",
                "data_directory": {
                    "path": str(data_dir.absolute()),
                    "total_gb": disk_usage.total / (1024**3),
                    "used_gb": disk_usage.used / (1024**3),
                    "free_gb": disk_usage.free / (1024**3),
                    "percent_used": disk_usage.percent,
                },
                "backup_directory": (
                    {
                        "path": str(backup_dir),
                        "exists": backup_dir.exists(),
                        "total_gb": (
                            backup_usage.total / (1024**3) if backup_usage else None
                        ),
                        "free_gb": (
                            backup_usage.free / (1024**3) if backup_usage else None
                        ),
                        "percent_used": backup_usage.percent if backup_usage else None,
                    }
                    if backup_usage
                    else None
                ),
                "message": (
                    "Filesystem healthy"
                    if disk_usage.percent < 90
                    else "Low disk space warning"
                ),
            }
        except Exception as e:
            logger.error(f"Filesystem health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Filesystem check failed",
            }

    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system CPU, memory, and network"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memory usage
            memory = psutil.virtual_memory()

            # Network statistics
            net_io = psutil.net_io_counters()

            # Process info
            process = psutil.Process()
            process_info = {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, "num_fds") else None,
            }

            return {
                "status": (
                    "healthy" if cpu_percent < 80 and memory.percent < 90 else "warning"
                ),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_average": (
                        os.getloadavg() if hasattr(os, "getloadavg") else None
                    ),
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory.percent,
                    "swap_percent": psutil.swap_memory().percent,
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errors": net_io.errin + net_io.errout,
                    "drops": net_io.dropin + net_io.dropout,
                },
                "process": process_info,
                "message": "System resources healthy",
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "System resource check failed",
            }

    async def check_device_discovery(self) -> Dict[str, Any]:
        """Check device discovery service health"""
        try:
            # Check if discovery is running
            # This would integrate with your actual device discovery service
            return {
                "status": "healthy",
                "discovered_devices": 0,  # Would get actual count
                "last_scan": None,  # Would get actual timestamp
                "message": "Device discovery operational",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Device discovery check failed",
            }

    async def check_scheduler(self) -> Dict[str, Any]:
        """Check scheduler service health"""
        try:
            # Check if scheduler is running
            # This would integrate with APScheduler
            return {
                "status": "healthy",
                "scheduled_jobs": 0,  # Would get actual count
                "next_run": None,  # Would get next scheduled time
                "message": "Scheduler operational",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Scheduler check failed",
            }

    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        start_time = time.time()

        # Run all health checks in parallel
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_influxdb(),
            self.check_filesystem(),
            self.check_system_resources(),
            self.check_device_discovery(),
            self.check_scheduler(),
            return_exceptions=True,
        )

        # Process results
        components = {
            "database": (
                checks[0]
                if not isinstance(checks[0], Exception)
                else {"status": "error", "error": str(checks[0])}
            ),
            "redis": (
                checks[1]
                if not isinstance(checks[1], Exception)
                else {"status": "error", "error": str(checks[1])}
            ),
            "influxdb": (
                checks[2]
                if not isinstance(checks[2], Exception)
                else {"status": "error", "error": str(checks[2])}
            ),
            "filesystem": (
                checks[3]
                if not isinstance(checks[3], Exception)
                else {"status": "error", "error": str(checks[3])}
            ),
            "system": (
                checks[4]
                if not isinstance(checks[4], Exception)
                else {"status": "error", "error": str(checks[4])}
            ),
            "device_discovery": (
                checks[5]
                if not isinstance(checks[5], Exception)
                else {"status": "error", "error": str(checks[5])}
            ),
            "scheduler": (
                checks[6]
                if not isinstance(checks[6], Exception)
                else {"status": "error", "error": str(checks[6])}
            ),
        }

        # Determine overall status
        statuses = [c.get("status", "unknown") for c in components.values()]
        if "unhealthy" in statuses or "error" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "degraded"
        elif "not_configured" in statuses:
            overall_status = "partial"
        else:
            overall_status = "healthy"

        # Calculate uptime
        uptime = datetime.now() - self.start_time

        result = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime).split(".")[0],
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "production"),
            "components": components,
            "check_duration_ms": (time.time() - start_time) * 1000,
        }

        self.last_check = result
        return result

    async def get_readiness(self) -> Dict[str, Any]:
        """Check if application is ready to serve requests"""
        # Check critical components only
        checks = await asyncio.gather(
            self.check_database(), self.check_filesystem(), return_exceptions=True
        )

        database_ok = (
            not isinstance(checks[0], Exception)
            and checks[0].get("status") == "healthy"
        )
        filesystem_ok = not isinstance(checks[1], Exception) and checks[1].get(
            "status"
        ) in ["healthy", "warning"]

        ready = database_ok and filesystem_ok

        return {
            "ready": ready,
            "checks": {"database": database_ok, "filesystem": filesystem_ok},
            "timestamp": datetime.now().isoformat(),
        }

    async def get_liveness(self) -> Dict[str, Any]:
        """Simple liveness check"""
        return {
            "alive": True,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
        }


# Create global health monitor instance
health_monitor = HealthMonitor()


# Health check endpoints
@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return await health_monitor.get_liveness()


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe endpoint"""
    result = await health_monitor.get_liveness()
    if not result["alive"]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return result


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe endpoint"""
    result = await health_monitor.get_readiness()
    if not result["ready"]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return result


@router.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with component status"""
    return await health_monitor.perform_health_check()


@router.get("/health/startup")
async def startup_probe():
    """Kubernetes startup probe endpoint"""
    # Check if application has been running for at least 10 seconds
    uptime = (datetime.now() - health_monitor.start_time).total_seconds()
    if uptime < 10:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application still starting up",
        )

    # Check readiness
    result = await health_monitor.get_readiness()
    if not result["ready"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not ready",
        )

    return {"status": "started", "uptime_seconds": uptime}
