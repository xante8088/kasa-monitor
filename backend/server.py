"""Backend server for Kasa device monitoring.

Copyright (C) 2025 Kasa Monitor Contributors

This file is part of Kasa Monitor.

Kasa Monitor is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Kasa Monitor is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Kasa Monitor. If not, see <https://www.gnu.org/licenses/>.
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyotp
import qrcode
import socketio
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write_api import SYNCHRONOUS
from kasa import Credentials, Device, Discover, SmartDevice
from pydantic import BaseModel, Field

from auth import (
    AuthManager,
    get_auth_security_status,
    get_current_user,
    get_network_access_config,
    is_local_network_ip,
    require_admin,
    require_auth,
    require_permission,
    security,
)
from database import DatabaseManager
from models import (
    DeviceData,
    DeviceReading,
    ElectricityRate,
    Permission,
    RefreshTokenRequest,
    Token,
    User,
    UserCreate,
    UserLogin,
    UserRole,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sanitize_for_log(input_str: str) -> str:
    """Sanitize user input for safe logging to prevent log injection attacks."""
    if not isinstance(input_str, str):
        input_str = str(input_str)
    # Remove or replace control characters that could be used for log injection
    # This includes newlines, carriage returns, tabs, and other control chars
    sanitized = re.sub(r"[\r\n\t\x00-\x1f\x7f-\x9f]", "_", input_str)
    # Limit length to prevent log flooding
    return sanitized[:200] + "..." if len(sanitized) > 200 else sanitized


def patch_timezone_handling():
    """Patch timezone handling to work around CST6CDT and similar issues."""
    import sys

    import pytz

    # Create a mapping for common problematic timezone strings
    timezone_mapping = {
        "CST6CDT": "America/Chicago",
        "EST5EDT": "America/New_York",
        "MST7MDT": "America/Denver",
        "PST8PDT": "America/Los_Angeles",
        "HST10": "Pacific/Honolulu",
        "AKST9AKDT": "America/Anchorage",
    }

    # Monkey patch pytz.timezone to handle these cases
    original_timezone = pytz.timezone

    def patched_timezone(zone):
        try:
            return original_timezone(zone)
        except pytz.exceptions.UnknownTimeZoneError:
            # Try to map common problematic timezone strings
            if zone in timezone_mapping:
                logger.info(f"Mapping timezone {zone} to {timezone_mapping[zone]}")
                return original_timezone(timezone_mapping[zone])
            # If no mapping exists, default to UTC
            logger.warning(f"Unknown timezone {zone}, defaulting to UTC")
            return original_timezone("UTC")

    pytz.timezone = patched_timezone
    logger.info("Timezone handling patched to handle CST6CDT and similar formats")


# Apply the timezone patch immediately
patch_timezone_handling()

# Import data management modules
try:
    from cache_manager import CacheManager
    from data_aggregation import DataAggregator
    from data_export import BulkOperations, DataExporter

    data_management_available = True
except ImportError:
    logger.warning(
        "Data management modules not available. Some features will be disabled."
    )
    data_management_available = False

# Import additional modules
try:
    from alert_management import AlertManager
    from audit_logging import AuditEvent, AuditEventType, AuditLogger, AuditSeverity
    from backup_manager import BackupManager
    from device_groups import DeviceGroupManager
    from health_monitor import HealthMonitor
    from prometheus_metrics import MetricsCollector as PrometheusMetrics

    monitoring_available = True
except ImportError as e:
    logger.warning(f"Monitoring modules not available: {e}")
    monitoring_available = False

# Import plugin system modules
try:
    from data_export_api import DataExportAPIRouter
    from plugin_api import PluginAPIRouter

    from hook_system import HookManager
    from plugin_system import PluginLoader

    plugin_system_available = True
except ImportError as e:
    logger.warning(f"Plugin system modules not available: {e}")
    plugin_system_available = False

# Conditional import for rate limiting
try:
    from slowapi.errors import RateLimitExceeded
except ImportError:
    # Create a dummy class if slowapi is not available
    class RateLimitExceeded(Exception):
        def __init__(
            self,
            detail="Rate limit exceeded",
            limit=None,
            retry_after=None,
            reset_time=None,
        ):
            self.detail = detail
            self.limit = limit
            self.retry_after = retry_after
            self.reset_time = reset_time
            super().__init__(detail)


class DeviceManager:
    """Manages Kasa device connections and polling."""

    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.credentials: Optional[Credentials] = None
        self.last_discovery: Optional[datetime] = None

    async def discover_devices(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> Dict[str, Device]:
        """Discover all Kasa devices on the network."""
        try:
            if username and password:
                self.credentials = Credentials(username, password)
                devices = await Discover.discover(credentials=self.credentials)
            else:
                devices = await Discover.discover()

            self.devices = devices
            self.last_discovery = datetime.now(timezone.utc)
            logger.info(f"Discovered {len(devices)} devices")
            return devices
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
            raise

    async def connect_to_device(self, ip: str) -> Optional[Device]:
        """Connect to a specific device by IP address."""
        try:
            # Try to discover single device
            device = await Discover.discover_single(ip, credentials=self.credentials)
            if device:
                await device.update()
                self.devices[ip] = device
                logger.info(f"Connected to device at {ip}: {device.alias}")
                return device
        except Exception as e:
            logger.error(f"Error connecting to device at {ip}: {e}")
        return None

    async def get_device_data(self, device_ip: str) -> Optional[DeviceData]:
        """Get current data from a specific device."""
        device = self.devices.get(device_ip)
        if not device:
            logger.warning(f"Device {device_ip} not found")
            return None

        try:
            # Handle timezone issues that may occur during device update
            try:
                await device.update()
            except Exception as update_error:
                error_msg = str(update_error)
                if "time zone" in error_msg.lower() or "timezone" in error_msg.lower():
                    logger.warning(
                        f"Timezone error for device {device_ip}: {error_msg}"
                    )
                    # Try to work around timezone issues by using a minimal update
                    try:
                        # Force refresh without relying on timezone-dependent operations
                        await device.protocol.query("system", "get_sysinfo")
                        logger.info(
                            f"Fallback update successful for device {device_ip}"
                        )
                    except Exception as fallback_error:
                        logger.error(
                            f"Fallback update failed for device {device_ip}: {fallback_error}"
                        )
                        # Continue with existing data if update fails
                        pass
                else:
                    # Re-raise non-timezone errors
                    raise update_error

            # Extract power consumption data
            power_data = {}
            try:
                if hasattr(device, "modules") and "Energy" in device.modules:
                    energy_module = device.modules["Energy"]
                    power_data = {
                        "current_power_w": getattr(
                            energy_module, "current_consumption", 0
                        ),
                        "today_energy_kwh": getattr(
                            energy_module, "consumption_today", 0
                        ),
                        "month_energy_kwh": getattr(
                            energy_module, "consumption_this_month", 0
                        ),
                        "voltage": getattr(energy_module, "voltage", 0),
                        "current": getattr(energy_module, "current", 0),
                    }
                elif hasattr(device, "emeter_realtime"):
                    try:
                        emeter = await device.emeter_realtime
                        power_data = {
                            "current_power_w": getattr(emeter, "power", 0),
                            "voltage": getattr(emeter, "voltage", 0),
                            "current": getattr(emeter, "current", 0),
                            "total_energy_kwh": getattr(emeter, "total", 0),
                        }
                    except Exception as emeter_error:
                        logger.warning(
                            f"Failed to get emeter data for {device_ip}: {emeter_error}"
                        )
                        power_data = {
                            "current_power_w": 0,
                            "voltage": 0,
                            "current": 0,
                            "total_energy_kwh": 0,
                        }
            except Exception as power_error:
                logger.warning(
                    f"Failed to extract power data for {device_ip}: {power_error}"
                )
                power_data = {}

            return DeviceData(
                ip=device_ip,
                alias=getattr(device, "alias", f"Device {device_ip}"),
                model=getattr(device, "model", "Unknown"),
                device_type=str(getattr(device, "device_type", "Unknown")),
                is_on=getattr(device, "is_on", False),
                rssi=getattr(device, "rssi", 0),
                mac=getattr(device, "mac", ""),
                **power_data,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Error getting data from device {device_ip}: {e}")
            return None

    async def poll_all_devices(self) -> List[DeviceData]:
        """Poll all discovered devices for current data."""
        tasks = [self.get_device_data(ip) for ip in self.devices.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for result in results:
            if isinstance(result, DeviceData):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error polling device: {result}")

        return valid_results


class KasaMonitorApp:
    """Main application class for Kasa monitoring."""

    def __init__(self):
        self.device_manager = DeviceManager()
        self.db_manager = DatabaseManager()
        self.scheduler = AsyncIOScheduler()
        # Initialize Socket.IO with secure CORS configuration
        self.sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])
        self.app = FastAPI(lifespan=self.lifespan)

        # Initialize data management services if available
        self.data_exporter = None
        self.data_aggregator = None
        self.cache_manager = None
        if data_management_available:
            self.data_exporter = DataExporter(self.db_manager)
            self.data_aggregator = DataAggregator(self.db_manager)
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.cache_manager = CacheManager(redis_url=redis_url)

        # Initialize monitoring services if available
        self.health_monitor = None
        self.prometheus_metrics = None
        self.alert_manager = None
        self.device_group_manager = None
        self.backup_manager = None
        self.audit_logger = None
        if monitoring_available:
            self.audit_logger = AuditLogger(
                db_path="kasa_monitor.db", log_dir="./logs/audit"
            )
            self.health_monitor = HealthMonitor(audit_logger=self.audit_logger)
            self.prometheus_metrics = PrometheusMetrics()
            self.alert_manager = AlertManager(db_path="kasa_monitor.db")
            self.device_group_manager = DeviceGroupManager(db_path="kasa_monitor.db")
            self.backup_manager = BackupManager(
                db_path="kasa_monitor.db",
                backup_dir="./backups",
                audit_logger=self.audit_logger,
            )

        # Initialize plugin system if available
        self.plugin_loader = None
        self.hook_manager = None
        self.plugin_api_router = None
        if plugin_system_available:
            self.hook_manager = HookManager()
            self.plugin_loader = PluginLoader(
                plugin_dir="./plugins", db_path="kasa_monitor.db", app_version="1.0.0"
            )
            self.plugin_api_router = PluginAPIRouter(
                app=self.app,
                plugin_loader=self.plugin_loader,
                hook_manager=self.hook_manager,
                db_path="kasa_monitor.db",
            )
            self.data_export_router = DataExportAPIRouter(
                app=self.app, db_path="kasa_monitor.db"
            )

        self.setup_middleware()
        self.setup_rate_limiter()
        self.setup_routes()
        self.setup_data_management_routes()
        self.setup_monitoring_routes()
        self.setup_plugin_routes()
        self.setup_socketio()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage application lifecycle."""
        startup_time = datetime.now()

        # Startup
        await self.db_manager.initialize()

        # Load saved devices on startup
        await self.load_saved_devices()

        self.scheduler.start()

        # Schedule device polling every 30 seconds
        self.scheduler.add_job(
            self.poll_and_store_data,
            trigger=IntervalTrigger(seconds=30),
            id="device_polling",
            replace_existing=True,
        )

        # Start data aggregation service if available
        if self.data_aggregator:
            await self.data_aggregator.start()
            logger.info("Data aggregation service started")

        # Initialize and load plugins if available
        if self.plugin_loader:
            # Plugin loader is initialized in constructor, just log that it's ready
            logger.info("Plugin system ready")

            # Log plugin system initialization
            if self.audit_logger:
                plugin_startup_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_STARTUP,
                    severity=AuditSeverity.INFO,
                    user_id=None,
                    username=None,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="system",
                    resource_id="plugin_system",
                    action="Plugin system initialized",
                    details={
                        "plugin_system": "enabled",
                        "plugin_directory": "./plugins",
                        "hook_manager": "enabled",
                        "plugin_api_router": "enabled",
                    },
                    timestamp=startup_time,
                    success=True,
                )
                await self.audit_logger.log_event_async(plugin_startup_event)

        # Log successful system startup
        if self.audit_logger:
            startup_event = AuditEvent(
                event_type=AuditEventType.SYSTEM_STARTUP,
                severity=AuditSeverity.INFO,
                user_id=None,
                username=None,
                ip_address=None,
                user_agent=None,
                session_id=None,
                resource_type="system",
                resource_id="kasa_monitor",
                action="Kasa Monitor system startup completed",
                details={
                    "startup_timestamp": startup_time.isoformat(),
                    "components_started": [
                        "database_manager",
                        "scheduler",
                        "device_polling",
                        "data_aggregator" if self.data_aggregator else None,
                        "plugin_system" if self.plugin_loader else None,
                        "audit_logger",
                    ],
                    "startup_duration_ms": (
                        datetime.now() - startup_time
                    ).total_seconds()
                    * 1000,
                    "scheduler_jobs": ["device_polling"],
                },
                timestamp=startup_time,
                success=True,
            )
            await self.audit_logger.log_event_async(startup_event)

        yield

        # Shutdown
        shutdown_time = datetime.now()

        # Log system shutdown initiation
        if self.audit_logger:
            shutdown_init_event = AuditEvent(
                event_type=AuditEventType.SYSTEM_SHUTDOWN,
                severity=AuditSeverity.INFO,
                user_id=None,
                username=None,
                ip_address=None,
                user_agent=None,
                session_id=None,
                resource_type="system",
                resource_id="kasa_monitor",
                action="Kasa Monitor system shutdown initiated",
                details={
                    "shutdown_timestamp": shutdown_time.isoformat(),
                    "components_to_shutdown": [
                        "plugin_system" if self.plugin_loader else None,
                        "data_aggregator" if self.data_aggregator else None,
                        "cache_manager" if self.cache_manager else None,
                        "scheduler",
                        "database_manager",
                    ],
                },
                timestamp=shutdown_time,
                success=True,
            )
            await self.audit_logger.log_event_async(shutdown_init_event)

        if self.plugin_loader:
            await self.plugin_loader.shutdown_all_plugins()
            logger.info("Plugin system shutdown complete")

            # Log plugin system shutdown
            if self.audit_logger:
                plugin_shutdown_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_SHUTDOWN,
                    severity=AuditSeverity.INFO,
                    user_id=None,
                    username=None,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="system",
                    resource_id="plugin_system",
                    action="Plugin system shutdown completed",
                    details={"plugin_system": "shutdown", "all_plugins_shutdown": True},
                    timestamp=shutdown_time,
                    success=True,
                )
                await self.audit_logger.log_event_async(plugin_shutdown_event)
        if self.data_aggregator:
            await self.data_aggregator.stop()
        if self.cache_manager:
            await self.cache_manager.close()

        self.scheduler.shutdown()
        await self.db_manager.close()

        # Log completed system shutdown
        if self.audit_logger:
            shutdown_complete_event = AuditEvent(
                event_type=AuditEventType.SYSTEM_SHUTDOWN,
                severity=AuditSeverity.INFO,
                user_id=None,
                username=None,
                ip_address=None,
                user_agent=None,
                session_id=None,
                resource_type="system",
                resource_id="kasa_monitor",
                action="Kasa Monitor system shutdown completed",
                details={
                    "shutdown_duration_ms": (
                        datetime.now() - shutdown_time
                    ).total_seconds()
                    * 1000,
                    "final_shutdown_timestamp": datetime.now().isoformat(),
                    "clean_shutdown": True,
                },
                timestamp=shutdown_time,
                success=True,
            )
            await self.audit_logger.log_event_async(shutdown_complete_event)

    def setup_middleware(self):
        """Configure CORS and API monitoring middleware."""

        # Add API performance monitoring middleware
        @self.app.middleware("http")
        async def api_monitoring_middleware(request: Request, call_next):
            """Monitor API usage patterns and performance."""
            import time

            start_time = time.time()

            # Extract basic request info
            method = request.method
            url_path = request.url.path
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            # Process the request
            try:
                response = await call_next(request)
                duration_ms = (time.time() - start_time) * 1000

                # Log slow API calls (>2 seconds)
                if duration_ms > 2000 and self.audit_logger:
                    slow_api_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.WARNING,
                        user_id=None,
                        username=None,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        session_id=None,
                        resource_type="api",
                        resource_id=url_path,
                        action="Slow API response detected",
                        details={
                            "api_monitoring": True,
                            "method": method,
                            "path": url_path,
                            "duration_ms": duration_ms,
                            "status_code": response.status_code,
                            "client_ip": client_ip,
                            "user_agent": user_agent,
                            "threshold_exceeded": "2000ms",
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=f"API response time exceeded threshold: {duration_ms}ms > 2000ms",
                    )
                    await self.audit_logger.log_event_async(slow_api_event)

                # Log high-frequency endpoints (more than 100 requests per minute)
                # This would need request counting logic, implementing basic version
                if url_path.startswith("/api/") and self.audit_logger:
                    # Log successful API usage for analysis
                    api_usage_event = AuditEvent(
                        event_type=AuditEventType.API_REQUEST,
                        severity=AuditSeverity.INFO,
                        user_id=None,  # API monitoring, no specific user context
                        username=None,  # API monitoring, no specific user context
                        ip_address=client_ip,
                        user_agent=user_agent,
                        session_id=None,  # API monitoring, no session context
                        resource_type="api",
                        resource_id=url_path,
                        action="API endpoint accessed",
                        details={
                            "api_monitoring": True,
                            "method": method,
                            "path": url_path,
                            "duration_ms": duration_ms,
                            "status_code": response.status_code,
                            "client_ip": client_ip,
                            "response_size": response.headers.get(
                                "content-length", "unknown"
                            ),
                        },
                        timestamp=datetime.now(),
                        success=response.status_code < 400,
                        error_message=(
                            None
                            if response.status_code < 400
                            else f"HTTP {response.status_code}"
                        ),
                    )
                    # Only log significant API calls to avoid spam
                    if duration_ms > 500 or response.status_code >= 400:
                        await self.audit_logger.log_event_async(api_usage_event)

                return response

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                # Log API request failures
                if self.audit_logger:
                    api_error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=None,  # System error, no specific user
                        username=None,  # System error, no specific user
                        ip_address=client_ip,
                        user_agent=user_agent,
                        session_id=None,  # System error, no session
                        resource_type="api",
                        resource_id=url_path,
                        action="API request failed",
                        details={
                            "api_monitoring": True,
                            "method": method,
                            "path": url_path,
                            "duration_ms": duration_ms,
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "client_ip": client_ip,
                            "user_agent": user_agent,
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(api_error_event)

                raise  # Re-raise the exception

        # Add secure CORS middleware
        try:
            from security_fixes.critical.cors_fix import setup_cors_security

            self.cors_config = setup_cors_security(self.app)
            logger.info(
                f"Secure CORS configured for environment: {self.cors_config.environment}"
            )

            # Update Socket.IO CORS to match app CORS
            if self.cors_config.allowed_origins:
                self.sio = socketio.AsyncServer(
                    async_mode="asgi",
                    cors_allowed_origins=self.cors_config.allowed_origins,
                )
                logger.info(
                    f"Socket.IO CORS origins: {self.cors_config.allowed_origins}"
                )
        except ImportError:
            logger.warning("CORS security fix not available, using restricted CORS")
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["*"],
            )
            # Update Socket.IO CORS to match fallback CORS
            self.sio = socketio.AsyncServer(
                async_mode="asgi",
                cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            )

        # Add global exception handler for authentication errors
        @self.app.exception_handler(HTTPException)
        async def auth_exception_handler(request: Request, exc: HTTPException):
            """Global handler for HTTP exceptions, particularly authentication errors."""

            # Handle authentication errors (401) with structured response
            if exc.status_code == 401:
                # If detail is already structured (from our enhanced auth), return as-is
                if isinstance(exc.detail, dict):
                    return JSONResponse(
                        status_code=401, content=exc.detail, headers=exc.headers or {}
                    )
                else:
                    # Legacy string detail - convert to structured format
                    error_code = "AUTH_ERROR"
                    if "expired" in str(exc.detail).lower():
                        error_code = "TOKEN_EXPIRED"
                    elif "invalid" in str(exc.detail).lower():
                        error_code = "TOKEN_INVALID"
                    elif "required" in str(exc.detail).lower():
                        error_code = "AUTH_REQUIRED"

                    structured_error = {
                        "error": "authentication_error",
                        "message": str(exc.detail),
                        "error_code": error_code,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "redirect_to": "/login",
                    }

                    return JSONResponse(
                        status_code=401,
                        content=structured_error,
                        headers=exc.headers or {"WWW-Authenticate": "Bearer"},
                    )

            # Handle other HTTP exceptions normally
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers or {},
            )

        # Add comprehensive authentication middleware
        @self.app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            """Enhanced authentication middleware with session validation."""

            # Skip authentication middleware for public endpoints
            public_paths = {
                "/",
                "/health",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/api/auth/login",
                "/api/auth/setup",
                "/api/auth/setup-required",
                "/api/auth/refresh",
            }

            if request.url.path in public_paths or request.url.path.startswith(
                "/static"
            ):
                return await call_next(request)

            # Extract authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

                try:
                    # Validate JWT token
                    payload = AuthManager.verify_token(token)
                    user_data = payload.get("user")

                    if user_data:
                        # Add session validation if available
                        try:
                            from session_management import (
                                DatabaseSessionStore,
                                SessionManager,
                            )

                            session_store = DatabaseSessionStore()
                            session_manager = SessionManager(session_store)

                            # Get client info
                            client_ip = (
                                request.client.host if request.client else "unknown"
                            )
                            user_agent = request.headers.get("user-agent", "unknown")

                            # For now, we'll just validate the token exists
                            # Full session validation would require storing session_id in JWT
                            user = User(**user_data)

                            # Add user context to request state
                            request.state.user = user
                            request.state.auth_method = "jwt_token"

                        except Exception as e:
                            logger.debug(f"Session validation failed: {e}")
                            # Continue with just JWT validation
                            user = User(**user_data)
                            request.state.user = user
                            request.state.auth_method = "jwt_only"

                except HTTPException:
                    # Token validation failed - will be handled by endpoint auth
                    pass
                except Exception as e:
                    logger.error(f"Authentication middleware error: {e}")

            return await call_next(request)

    def enhanced_require_auth(self, request: Request):
        """Enhanced authentication with session timeout logging."""

        def auth_dependency(
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        ) -> User:
            if not credentials:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                payload = AuthManager.verify_token(credentials.credentials)
                user_data = payload.get("user")
                if not user_data:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                user = User(**user_data)
                user.permissions = AuthManager.get_user_permissions(user.role)
                return user

            except HTTPException as e:
                # Log session timeout if token expired
                if "Token expired" in str(e.detail):
                    asyncio.create_task(
                        self._log_session_timeout(request, credentials.credentials)
                    )
                raise e

        return auth_dependency

    async def _log_session_timeout(self, request: Request, token: str):
        """Log session timeout event."""
        if not self.audit_logger:
            return

        try:
            # Try to extract user info from expired token (unsafe decode)
            import jose.jwt as jwt

            payload = jwt.get_unverified_claims(token)
            user_data = payload.get("user", {})

            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            audit_event = AuditEvent(
                event_type=AuditEventType.LOGOUT,
                severity=AuditSeverity.INFO,
                user_id=user_data.get("id"),
                username=user_data.get("username"),
                ip_address=client_ip,
                user_agent=user_agent,
                session_id=None,
                resource_type=None,
                resource_id=None,
                action="Session timeout",
                details={
                    "logout_method": "session_timeout",
                    "token_expired": True,
                    "expiration_time": payload.get("exp"),
                },
                timestamp=datetime.now(timezone.utc),
                success=True,
            )
            await self.audit_logger.log_event_async(audit_event)
        except Exception as e:
            logger.error(f"Failed to log session timeout: {e}")

    def enhanced_require_permission(self, permission: Permission, request: Request):
        """Enhanced permission check with denial logging."""

        def permission_dependency(
            user: User = Depends(self.enhanced_require_auth(request)),
        ) -> User:
            if not AuthManager.check_permission(user.permissions, permission):
                # Log permission denied
                asyncio.create_task(
                    self._log_permission_denied(request, user, permission)
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission.value}",
                )
            return user

        return permission_dependency

    async def _log_permission_denied(
        self, request: Request, user: User, permission: Permission
    ):
        """Log permission denied event."""
        if not self.audit_logger:
            return

        try:
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            audit_event = AuditEvent(
                event_type=AuditEventType.PERMISSION_DENIED,
                severity=AuditSeverity.WARNING,
                user_id=user.id,
                username=user.username,
                ip_address=client_ip,
                user_agent=user_agent,
                session_id=None,
                resource_type="permission",
                resource_id=permission.value,
                action="Permission denied",
                details={
                    "required_permission": permission.value,
                    "user_permissions": [p.value for p in user.permissions],
                    "user_role": user.role.value if user.role else None,
                    "request_path": str(request.url.path),
                    "request_method": request.method,
                },
                timestamp=datetime.now(timezone.utc),
                success=False,
                error_message=f"User lacks required permission: {permission.value}",
            )
            await self.audit_logger.log_event_async(audit_event)
        except Exception as e:
            logger.error(f"Failed to log permission denied: {e}")

    def setup_rate_limiter(self):
        """Setup rate limiting with audit logging."""
        try:
            from rate_limiter import RateLimiter
            from slowapi import Limiter
            from slowapi.middleware import SlowAPIMiddleware
            from slowapi.util import get_remote_address

            # Initialize rate limiter
            self.rate_limiter = RateLimiter(
                redis_client=None
            )  # Using memory storage for now

            # Create limiter for SlowAPI
            limiter = Limiter(
                key_func=get_remote_address, default_limits=["100 per minute"]
            )

            # Add middleware
            self.app.add_middleware(SlowAPIMiddleware)

            # Custom rate limit exceeded handler with audit logging
            @self.app.exception_handler(RateLimitExceeded)
            async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
                """Handle rate limit exceeded with audit logging."""
                await self._log_rate_limit_exceeded(request, exc)

                response = Response(
                    content=f"Rate limit exceeded: {exc.detail}",
                    status_code=429,
                    headers={
                        "Retry-After": str(exc.retry_after),
                        "X-RateLimit-Limit": str(exc.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(exc.reset_time),
                    },
                )
                return response

            # Assign limiter to app state for SlowAPIMiddleware
            self.app.state.limiter = limiter
            self.limiter = limiter
            logger.info("Rate limiting configured with audit logging")

        except ImportError as e:
            logger.warning(f"Rate limiting not available: {e}")
            self.rate_limiter = None
            self.limiter = None

    async def _log_rate_limit_exceeded(self, request: Request, exc: RateLimitExceeded):
        """Log rate limit exceeded event."""
        if not self.audit_logger:
            return

        try:
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            # Try to get user info if authenticated
            user = getattr(request.state, "user", None)
            user_id = user.get("id") if user else None
            username = user.get("username") if user else None

            audit_event = AuditEvent(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                severity=AuditSeverity.WARNING,
                user_id=user_id,
                username=username,
                ip_address=client_ip,
                user_agent=user_agent,
                session_id=None,
                resource_type="api_endpoint",
                resource_id=str(request.url.path),
                action="Rate limit exceeded",
                details={
                    "request_path": str(request.url.path),
                    "request_method": request.method,
                    "limit": exc.limit,
                    "retry_after": exc.retry_after,
                    "reset_time": exc.reset_time,
                    "rate_limit_key": get_remote_address(request),
                    "query_params": (
                        dict(request.query_params) if request.query_params else None
                    ),
                },
                timestamp=datetime.now(timezone.utc),
                success=False,
                error_message=f"Rate limit of {exc.limit} exceeded for {request.url.path}",
            )
            await self.audit_logger.log_event_async(audit_event)
        except Exception as e:
            logger.error(f"Failed to log rate limit exceeded: {e}")

    async def _log_suspicious_activity(
        self, request: Request, activity_type: str, details: dict
    ):
        """Log suspicious activity."""
        if not self.audit_logger:
            return

        try:
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            # Try to get user info if authenticated
            user = getattr(request.state, "user", None)
            user_id = user.get("id") if user else None
            username = user.get("username") if user else None

            audit_event = AuditEvent(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.WARNING,
                user_id=user_id,
                username=username,
                ip_address=client_ip,
                user_agent=user_agent,
                session_id=None,
                resource_type="security_event",
                resource_id=activity_type,
                action=f"Suspicious activity detected: {activity_type}",
                details={
                    "activity_type": activity_type,
                    "request_path": str(request.url.path),
                    "request_method": request.method,
                    "detection_details": details,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                timestamp=datetime.now(timezone.utc),
                success=False,
                error_message=f"Suspicious activity detected: {activity_type}",
            )
            await self.audit_logger.log_event_async(audit_event)
        except Exception as e:
            logger.error(f"Failed to log suspicious activity: {e}")

    def setup_routes(self):
        """Set up FastAPI routes."""

        @self.app.get("/health")
        async def simple_health_check():
            """Simple health check endpoint for integration tests."""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @self.app.get("/api/devices")
        async def get_devices():
            """Get list of all discovered devices."""
            devices_data = []
            for ip, device in self.device_manager.devices.items():
                devices_data.append(
                    {
                        "ip": ip,
                        "alias": device.alias,
                        "model": device.model,
                        "device_type": str(device.device_type),
                        "is_on": device.is_on,
                        "mac": device.mac,
                    }
                )
            return devices_data

        @self.app.post("/api/discover")
        async def discover_devices(
            credentials: Optional[Dict[str, str]] = None,
            current_user: User = Depends(
                require_permission(Permission.DEVICES_DISCOVER)
            ),
        ):
            """Trigger device discovery and save to database."""
            username = credentials.get("username") if credentials else None
            password = credentials.get("password") if credentials else None

            devices = await self.device_manager.discover_devices(username, password)

            # Save discovered devices to database
            for ip, device in devices.items():
                try:
                    device_data = await self.device_manager.get_device_data(ip)
                    if device_data:
                        await self.db_manager.store_device_reading(device_data)
                        logger.info(f"Saved device {device.alias} ({ip}) to database")
                except Exception as e:
                    logger.error(f"Error saving device {ip}: {e}")

            # Audit log device discovery
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.DEVICE_DISCOVERED,
                    severity=AuditSeverity.INFO,
                    user_id=current_user.id,
                    username=current_user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="device_discovery",
                    resource_id=None,
                    action=f"Discovered {len(devices)} devices",
                    details={
                        "device_count": len(devices),
                        "device_ips": list(devices.keys()),
                    },
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            return {"discovered": len(devices)}

        @self.app.post("/api/devices/manual")
        async def add_manual_device(device_config: dict):
            """Manually add a device by IP address."""
            ip = device_config.get("ip")
            alias = device_config.get("alias", f"Device at {ip}")

            if not ip:
                raise HTTPException(status_code=400, detail="IP address required")

            try:
                # Try to connect to the device
                device = await self.device_manager.connect_to_device(ip)
                if device:
                    # Store in database
                    device_data = await self.device_manager.get_device_data(ip)
                    if device_data:
                        await self.db_manager.store_device_reading(device_data)
                        logger.info(
                            "Manually added device %s (%s)",
                            sanitize_for_log(alias),
                            sanitize_for_log(ip),
                        )

                        # Audit log device addition
                        if self.audit_logger:
                            audit_event = AuditEvent(
                                event_type=AuditEventType.DEVICE_ADDED,
                                severity=AuditSeverity.INFO,
                                user_id=None,  # Could get from auth context
                                username=None,
                                ip_address=None,
                                user_agent=None,
                                session_id=None,
                                resource_type="device",
                                resource_id=ip,
                                action="manual_device_added",
                                details={
                                    "alias": alias,
                                    "ip": ip,
                                    "model": device_data.model,
                                },
                                timestamp=datetime.now(),
                                success=True,
                            )
                            await self.audit_logger.log_event_async(audit_event)

                        return {"status": "success", "device": device_data.dict()}
                else:
                    raise HTTPException(
                        status_code=404, detail=f"Cannot connect to device at {ip}"
                    )
            except Exception as e:
                logger.error(
                    "Error adding manual device %s: %s",
                    sanitize_for_log(ip),
                    sanitize_for_log(str(e)),
                )

                # Audit log failed device addition
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=None,
                        username=None,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="device",
                        resource_id=ip,
                        action="Manual device addition failed",
                        details={
                            "operation": "manual_device_addition",
                            "target_ip": ip,
                            "target_alias": alias,
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "connection_attempted": True,
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/devices/{device_ip}")
        async def remove_device(device_ip: str):
            """Remove a device from monitoring."""
            try:
                # Remove from device manager
                if device_ip in self.device_manager.devices:
                    del self.device_manager.devices[device_ip]

                # Mark as inactive in database (don't delete history)
                await self.db_manager.mark_device_inactive(device_ip)

                # Audit log device removal
                if self.audit_logger:
                    audit_event = AuditEvent(
                        event_type=AuditEventType.DEVICE_REMOVED,
                        severity=AuditSeverity.INFO,
                        user_id=None,  # Could get from auth context
                        username=None,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="device",
                        resource_id=device_ip,
                        action="device_removed",
                        details={"device_ip": device_ip, "method": "mark_inactive"},
                        timestamp=datetime.now(),
                        success=True,
                    )
                    await self.audit_logger.log_event_async(audit_event)

                logger.info("Removed device %s", sanitize_for_log(device_ip))
                return {"status": "success", "message": f"Device {device_ip} removed"}
            except Exception as e:
                logger.error(
                    "Error removing device %s: %s",
                    sanitize_for_log(device_ip),
                    sanitize_for_log(str(e)),
                )

                # Audit log failed device removal
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=None,
                        username=None,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="device",
                        resource_id=device_ip,
                        action="Device removal failed",
                        details={
                            "operation": "device_removal",
                            "target_device_ip": device_ip,
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "removal_attempted": True,
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/devices/saved")
        async def get_saved_devices():
            """Get list of saved device IPs from database."""
            saved_devices = await self.db_manager.get_saved_devices()
            return saved_devices

        @self.app.get("/api/settings/network")
        async def get_network_settings():
            """Get network configuration settings."""
            return {
                "network_mode": os.getenv("NETWORK_MODE", "bridge"),
                "discovery_enabled": os.getenv("DISCOVERY_ENABLED", "false").lower()
                == "true",
                "manual_devices_enabled": os.getenv(
                    "MANUAL_DEVICES_ENABLED", "true"
                ).lower()
                == "true",
                "host_ip": os.getenv("DOCKER_HOST_IP", None),
            }

        @self.app.get("/api/device/{device_ip}")
        async def get_device_data(device_ip: str):
            """Get current data for a specific device."""
            data = await self.device_manager.get_device_data(device_ip)
            if not data:
                raise HTTPException(status_code=404, detail="Device not found")
            return data.dict()

        @self.app.get("/api/device/{device_ip}/history")
        async def get_device_history(
            device_ip: str,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
            interval: Optional[str] = None,
            time_period: Optional[str] = None,
            response: Response = None,
        ):
            """Get historical data for a device with time period filtering."""
            try:
                # Validate time parameters
                if start_time and end_time and start_time >= end_time:
                    raise HTTPException(
                        status_code=400, 
                        detail="start_time must be before end_time"
                    )
                
                # Check maximum range (90 days)
                if start_time and end_time:
                    time_diff = end_time - start_time
                    if time_diff.days > 90:
                        raise HTTPException(
                            status_code=400, 
                            detail="Time range cannot exceed 90 days"
                        )
                
                # Validate time_period if provided
                valid_periods = ['1h', '6h', '24h', '3d', '7d', '30d', 'custom']
                if time_period and time_period not in valid_periods:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid time_period. Must be one of: {valid_periods}"
                    )
                
                # Auto-select interval based on time range if not provided
                if not interval:
                    interval = self._get_optimal_interval(start_time, end_time, time_period)
                
                history = await self.db_manager.get_device_history(
                    device_ip, start_time, end_time, interval
                )
                
                # Add caching headers for better performance
                if response and time_period:
                    cache_duration = self._get_cache_duration(time_period)
                    response.headers["Cache-Control"] = f"public, max-age={cache_duration}"
                
                return {
                    "data": history,
                    "metadata": {
                        "time_period": time_period,
                        "start_time": start_time.isoformat() if start_time else None,
                        "end_time": end_time.isoformat() if end_time else None,
                        "interval": interval,
                        "data_points": len(history) if history else 0
                    }
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting device history for {device_ip}: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.get("/api/device/{device_ip}/history/range")
        async def get_device_history_range(device_ip: str):
            """Get available data range for a device."""
            try:
                data_range = await self.db_manager.get_device_data_range(device_ip)
                if not data_range:
                    raise HTTPException(
                        status_code=404, 
                        detail="No historical data found for this device"
                    )
                return data_range
            except Exception as e:
                logger.error(f"Error getting data range for device {device_ip}: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.get("/api/device/{device_ip}/stats")
        async def get_device_stats(device_ip: str):
            """Get statistics for a device."""
            stats = await self.db_manager.get_device_stats(device_ip)
            return stats

        @self.app.post("/api/device/{device_ip}/control")
        async def control_device(
            device_ip: str,
            action: str = Query(...),
            current_user: User = Depends(
                require_permission(Permission.DEVICES_CONTROL)
            ),
        ):
            """Control a device (turn on/off)."""
            device = self.device_manager.devices.get(device_ip)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            try:
                if action == "on":
                    await device.turn_on()
                elif action == "off":
                    await device.turn_off()
                else:
                    raise HTTPException(status_code=400, detail="Invalid action")

                await device.update()

                # Audit log device control
                if self.audit_logger:
                    audit_event = AuditEvent(
                        event_type=AuditEventType.DEVICE_CONTROLLED,
                        severity=AuditSeverity.INFO,
                        user_id=current_user.id,
                        username=current_user.username,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="device",
                        resource_id=device_ip,
                        action=f"device_control_{action}",
                        details={
                            "device_ip": device_ip,
                            "action": action,
                            "is_on": device.is_on,
                        },
                        timestamp=datetime.now(),
                        success=True,
                    )
                    await self.audit_logger.log_event_async(audit_event)

                return {"status": "success", "is_on": device.is_on}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/rates")
        async def get_electricity_rates():
            """Get electricity rate configuration."""
            rates = await self.db_manager.get_electricity_rates()
            return rates

        @self.app.post("/api/rates")
        async def set_electricity_rate(rate: ElectricityRate):
            """Set electricity rate configuration."""
            await self.db_manager.set_electricity_rate(rate)
            return {"status": "success"}

        @self.app.get("/api/costs")
        async def get_electricity_costs(
            start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
        ):
            """Calculate electricity costs for all devices."""
            costs = await self.db_manager.calculate_costs(start_date, end_date)
            return costs

        @self.app.get("/api/devices/saved")
        async def get_saved_devices():
            """Get all saved devices from database."""
            devices = await self.db_manager.get_saved_devices()
            return devices

        @self.app.put("/api/devices/{device_ip}/monitoring")
        async def update_device_monitoring(
            device_ip: str,
            request: Dict[str, bool],
            current_user: User = Depends(require_permission(Permission.DEVICES_EDIT)),
        ):
            """Enable or disable monitoring for a device."""
            enabled = request.get("enabled", True)
            success = await self.db_manager.update_device_monitoring(device_ip, enabled)

            # Audit log monitoring change
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.DEVICE_UPDATED,
                    severity=AuditSeverity.INFO,
                    user_id=current_user.id,
                    username=current_user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="device",
                    resource_id=device_ip,
                    action=f"Monitoring {'enabled' if enabled else 'disabled'}",
                    details={
                        "device_ip": device_ip,
                        "monitoring_enabled": enabled,
                        "success": success,
                    },
                    timestamp=datetime.now(timezone.utc),
                    success=success,
                )
                await self.audit_logger.log_event_async(audit_event)

            if success:
                return {
                    "message": f"Monitoring {'enabled' if enabled else 'disabled'} for device {device_ip}"
                }
            else:
                raise HTTPException(
                    status_code=400, detail="Failed to update monitoring status"
                )

        @self.app.put("/api/devices/{device_ip}/ip")
        async def update_device_ip(
            device_ip: str,
            request: Dict[str, str],
            current_user: User = Depends(require_permission(Permission.DEVICES_EDIT)),
        ):
            """Update a device's IP address."""
            new_ip = request.get("new_ip")
            if not new_ip:
                raise HTTPException(status_code=400, detail="New IP is required")

            success = await self.db_manager.update_device_ip(device_ip, new_ip)

            # Audit log IP update
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.DEVICE_UPDATED,
                    severity=AuditSeverity.INFO,
                    user_id=current_user.id,
                    username=current_user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="device",
                    resource_id=device_ip,
                    action=f"IP address updated",
                    details={"old_ip": device_ip, "new_ip": new_ip, "success": success},
                    timestamp=datetime.now(timezone.utc),
                    success=success,
                )
                await self.audit_logger.log_event_async(audit_event)

            if success:
                # Update device manager
                if device_ip in self.device_manager.devices:
                    device = self.device_manager.devices.pop(device_ip)
                    self.device_manager.devices[new_ip] = device
                return {"message": f"Device IP updated from {device_ip} to {new_ip}"}
            else:
                raise HTTPException(
                    status_code=400, detail="Failed to update IP (may already exist)"
                )

        @self.app.delete("/api/devices/{device_ip}")
        async def remove_device(device_ip: str):
            """Remove a device from monitoring."""
            success = await self.db_manager.remove_device(device_ip)
            if success:
                # Remove from device manager
                if device_ip in self.device_manager.devices:
                    del self.device_manager.devices[device_ip]
                return {"message": f"Device {device_ip} removed"}
            else:
                raise HTTPException(status_code=400, detail="Failed to remove device")

        @self.app.put("/api/devices/{device_ip}/notes")
        async def update_device_notes(
            device_ip: str,
            request: Dict[str, str],
            user: User = Depends(require_permission(Permission.DEVICES_EDIT)),
        ):
            """Update notes for a device."""
            notes = request.get("notes", "")
            success = await self.db_manager.update_device_notes(device_ip, notes)

            # Audit log notes update
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.DEVICE_UPDATED,
                    severity=AuditSeverity.INFO,
                    user_id=user.id,
                    username=user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="device",
                    resource_id=device_ip,
                    action="Notes updated",
                    details={
                        "device_ip": device_ip,
                        "notes_length": len(notes),
                        "success": success,
                    },
                    timestamp=datetime.now(timezone.utc),
                    success=success,
                )
                await self.audit_logger.log_event_async(audit_event)

            if success:
                return {"message": "Notes updated"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update notes")

        # Authentication endpoints
        @self.app.post("/api/auth/login", response_model=Token)
        async def login(login_data: UserLogin, request: Request):
            """Authenticate user and return JWT token."""

            # Check for test credentials in development mode (not production)
            is_development = (
                os.getenv("NODE_ENV") != "production"
                and os.getenv("ENVIRONMENT") != "production"
            )
            test_creds_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                ".auth",
                "test_credentials.json",
            )

            if is_development and os.path.exists(test_creds_path):
                try:
                    with open(test_creds_path, "r") as f:
                        test_data = json.load(f)

                    # Check if this matches test credentials
                    for test_user_key, test_user_data in test_data.items():
                        if login_data.username == test_user_data.get(
                            "username"
                        ) and login_data.password == test_user_data.get("password"):

                            # Create a User object from test data
                            test_user = User(
                                id=test_user_data.get("id", 99999),
                                username=test_user_data.get("username"),
                                email=test_user_data.get("email"),
                                full_name=test_user_data.get("full_name"),
                                role=UserRole(test_user_data.get("role", "admin")),
                                is_active=test_user_data.get("is_active", True),
                                created_at=datetime.now(timezone.utc),
                                last_login=datetime.now(timezone.utc),
                                permissions=test_user_data.get("permissions", ["*"]),
                            )

                            # Create access token and refresh token for test user
                            user_data = {"user": test_user.model_dump()}
                            access_token = AuthManager.create_access_token(
                                data=user_data
                            )
                            refresh_token = AuthManager.create_refresh_token(
                                data=user_data
                            )

                            # Log successful test user authentication
                            if self.audit_logger:
                                client_ip = (
                                    request.client.host if request.client else "unknown"
                                )
                                user_agent = request.headers.get(
                                    "user-agent", "unknown"
                                )

                                audit_event = AuditEvent(
                                    event_type=AuditEventType.LOGIN_SUCCESS,
                                    severity=AuditSeverity.INFO,
                                    user_id=test_user.id,
                                    username=test_user.username,
                                    ip_address=client_ip,
                                    user_agent=user_agent,
                                    session_id=None,
                                    resource_type=None,
                                    resource_id=None,
                                    action="Test user login successful",
                                    details={
                                        "login_method": "test_credentials",
                                        "development_mode": True,
                                    },
                                    timestamp=datetime.now(timezone.utc),
                                    success=True,
                                )
                                await self.audit_logger.log_event_async(audit_event)

                            logger.info(
                                "Test user authenticated: %s",
                                sanitize_for_log(login_data.username),
                            )
                            return Token(
                                access_token=access_token,
                                expires_in=1800,  # 30 minutes
                                user=test_user,
                                refresh_token=refresh_token,
                            )

                except Exception as e:
                    logger.warning(f"Error reading test credentials: {e}")

            # Fall back to normal database authentication
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            user = await self.db_manager.get_user_by_username(login_data.username)
            if not user:
                # Log failed login attempt - user not found
                if self.audit_logger:
                    audit_event = AuditEvent(
                        event_type=AuditEventType.LOGIN_FAILURE,
                        severity=AuditSeverity.WARNING,
                        user_id=None,
                        username=login_data.username,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        session_id=None,
                        resource_type=None,
                        resource_id=None,
                        action="Login failed - user not found",
                        details={
                            "login_method": "password",
                            "failure_reason": "user_not_found",
                        },
                        timestamp=datetime.now(timezone.utc),
                        success=False,
                        error_message="Invalid username or password",
                    )
                    await self.audit_logger.log_event_async(audit_event)

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )

            password_hash = await self.db_manager.get_user_password_hash(
                login_data.username
            )
            if not password_hash or not AuthManager.verify_password(
                login_data.password, password_hash
            ):
                # Log failed login attempt - invalid password
                if self.audit_logger:
                    audit_event = AuditEvent(
                        event_type=AuditEventType.LOGIN_FAILURE,
                        severity=AuditSeverity.WARNING,
                        user_id=user.id,
                        username=user.username,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        session_id=None,
                        resource_type=None,
                        resource_id=None,
                        action="Login failed - invalid password",
                        details={
                            "login_method": "password",
                            "failure_reason": "invalid_password",
                        },
                        timestamp=datetime.now(timezone.utc),
                        success=False,
                        error_message="Invalid username or password",
                    )
                    await self.audit_logger.log_event_async(audit_event)

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )

            # Check if user has 2FA enabled
            totp_secret = await self.db_manager.get_user_totp_secret(user.id)
            if totp_secret:
                # User has 2FA enabled - require TOTP code
                if not login_data.totp_code:
                    # Return a special response indicating 2FA is required
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="2FA verification required",
                        headers={"X-2FA-Required": "true"},
                    )

                # Verify TOTP code
                import pyotp

                totp = pyotp.TOTP(totp_secret)
                if not totp.verify(login_data.totp_code, valid_window=1):
                    # Log failed 2FA attempt
                    if self.audit_logger:
                        audit_event = AuditEvent(
                            event_type=AuditEventType.LOGIN_FAILURE,
                            severity=AuditSeverity.WARNING,
                            user_id=user.id,
                            username=user.username,
                            ip_address=client_ip,
                            user_agent=user_agent,
                            session_id=None,
                            resource_type=None,
                            resource_id=None,
                            action="Login failed - invalid 2FA code",
                            details={
                                "login_method": "password+2fa",
                                "failure_reason": "invalid_2fa_code",
                            },
                            timestamp=datetime.now(timezone.utc),
                            success=False,
                            error_message="Invalid 2FA code",
                        )
                        await self.audit_logger.log_event_async(audit_event)

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid 2FA code",
                    )

            # Update last login
            await self.db_manager.update_user_login(login_data.username)

            # Log successful database authentication
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.LOGIN_SUCCESS,
                    severity=AuditSeverity.INFO,
                    user_id=user.id,
                    username=user.username,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    session_id=None,
                    resource_type=None,
                    resource_id=None,
                    action="User login successful",
                    details={
                        "login_method": (
                            "password" if not totp_secret else "password+2fa"
                        )
                    },
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            # Create access token and refresh token
            user_data = {"user": user.model_dump()}
            access_token = AuthManager.create_access_token(data=user_data)
            refresh_token = AuthManager.create_refresh_token(data=user_data)

            # Initialize session management if available
            session_info = None
            try:
                from session_management import DatabaseSessionStore, SessionManager

                session_store = DatabaseSessionStore()
                session_manager = SessionManager(session_store)

                # Create a session for this login
                session_info = session_manager.create_session(
                    user_id=user.id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    remember_me=False,  # Could be a login parameter
                    device_name=None,  # Could extract from user agent
                )

                logger.info(
                    f"Session created for user {user.username}: {session_info['session_id']}"
                )

            except Exception as e:
                logger.warning(f"Failed to create session: {e}")
                # Continue without session management
                pass

            return Token(
                access_token=access_token,
                expires_in=1800,  # 30 minutes
                user=user,
                refresh_token=refresh_token,
            )

        @self.app.post("/api/auth/refresh", response_model=Token)
        async def refresh_token(refresh_request: RefreshTokenRequest, request: Request):
            """Refresh an expired access token using a valid refresh token."""
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            try:
                # Verify the refresh token
                payload = AuthManager.verify_refresh_token(
                    refresh_request.refresh_token
                )
                user_data = payload.get("user")

                if not user_data:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "error": "refresh_token_invalid",
                            "message": "Invalid refresh token structure. Please log in again.",
                            "error_code": "REFRESH_TOKEN_INVALID",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "redirect_to": "/login",
                        },
                    )

                # Recreate user object
                user = User(**user_data)

                # Verify user still exists and is active in database
                db_user = await self.db_manager.get_user_by_username(user.username)
                if not db_user or not db_user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "error": "user_inactive",
                            "message": "User account is no longer active. Please contact administrator.",
                            "error_code": "USER_INACTIVE",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "redirect_to": "/login",
                        },
                    )

                # Update user data with latest from database
                user = db_user

                # Create new tokens
                new_user_data = {"user": user.model_dump()}
                new_access_token = AuthManager.create_access_token(data=new_user_data)
                new_refresh_token = AuthManager.create_refresh_token(data=new_user_data)

                # Log successful token refresh
                if self.audit_logger:
                    audit_event = AuditEvent(
                        event_type=AuditEventType.LOGIN_SUCCESS,
                        severity=AuditSeverity.INFO,
                        user_id=user.id,
                        username=user.username,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        session_id=None,
                        resource_type=None,
                        resource_id=None,
                        action="Token refreshed successfully",
                        details={
                            "auth_method": "refresh_token",
                            "refresh_source": "client_request",
                        },
                        timestamp=datetime.now(timezone.utc),
                        success=True,
                    )
                    await self.audit_logger.log_event_async(audit_event)

                return Token(
                    access_token=new_access_token,
                    expires_in=1800,  # 30 minutes
                    user=user,
                    refresh_token=new_refresh_token,
                )

            except HTTPException as e:
                # Log failed token refresh attempt
                if self.audit_logger:
                    audit_event = AuditEvent(
                        event_type=AuditEventType.LOGIN_FAILURE,
                        severity=AuditSeverity.WARNING,
                        user_id=None,
                        username="unknown",
                        ip_address=client_ip,
                        user_agent=user_agent,
                        session_id=None,
                        resource_type=None,
                        resource_id=None,
                        action="Token refresh failed",
                        details={
                            "failure_reason": str(e.detail),
                            "status_code": e.status_code,
                        },
                        timestamp=datetime.now(timezone.utc),
                        success=False,
                        error_message=str(e.detail),
                    )
                    await self.audit_logger.log_event_async(audit_event)

                # Re-raise the HTTPException
                raise e

        @self.app.post("/api/auth/logout")
        async def logout(request: Request, user: User = Depends(require_auth)):
            """Logout user and invalidate session."""
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            # Invalidate all user sessions if available
            try:
                from session_management import DatabaseSessionStore, SessionManager

                session_store = DatabaseSessionStore()
                session_manager = SessionManager(session_store)

                # Invalidate all sessions for this user
                session_manager.invalidate_all_sessions(user.id)
                logger.info(f"All sessions invalidated for user {user.username}")

            except Exception as e:
                logger.warning(f"Failed to invalidate sessions: {e}")
                # Continue without session management

            # Log successful logout
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.LOGOUT,
                    severity=AuditSeverity.INFO,
                    user_id=user.id,
                    username=user.username,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    session_id=None,
                    resource_type=None,
                    resource_id=None,
                    action="User logged out",
                    details={
                        "logout_method": "explicit",
                        "session_invalidated": True,
                        "all_sessions_cleared": True,
                    },
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            # Note: With JWT, we can't truly invalidate the token server-side
            # without implementing a token blacklist. For now, we just log the logout.
            # The client should discard the token.

            return {"message": "Logged out successfully", "status": "success"}

        @self.app.get("/api/auth/security-status")
        async def get_authentication_security_status(
            request: Request, admin: User = Depends(require_admin)
        ):
            """Get comprehensive authentication security status (Admin only)."""
            try:
                security_status = get_auth_security_status()

                # Add runtime information
                security_status["runtime_info"] = {
                    "server_uptime": (
                        str(datetime.now(timezone.utc) - admin.created_at)
                        if admin.created_at
                        else "unknown"
                    ),
                    "total_admin_users": await self.db_manager.count_admin_users(),
                    "authentication_middleware_enabled": True,
                    "session_management_integrated": True,
                }

                # Log security status check
                if self.audit_logger:
                    audit_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ACCESS,
                        severity=AuditSeverity.INFO,
                        user_id=admin.id,
                        username=admin.username,
                        ip_address=request.client.host if request.client else "unknown",
                        user_agent=request.headers.get("user-agent", "unknown"),
                        session_id=None,
                        resource_type="security",
                        resource_id="auth_status",
                        action="Authentication security status viewed",
                        details={
                            "admin_action": True,
                            "security_review": True,
                        },
                        timestamp=datetime.now(timezone.utc),
                        success=True,
                    )
                    await self.audit_logger.log_event_async(audit_event)

                return security_status

            except Exception as e:
                logger.error(f"Error getting authentication security status: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve authentication security status",
                )

        @self.app.post("/api/auth/setup", response_model=User)
        async def initial_setup(admin_data: UserCreate):
            """Create initial admin user."""
            setup_required = await self.db_manager.is_setup_required()
            if not setup_required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Setup already completed",
                )

            # Force admin role for initial setup
            admin_data.role = UserRole.ADMIN

            success = await self.db_manager.create_admin_user(
                admin_data.username,
                admin_data.email,
                admin_data.full_name,
                admin_data.password,
            )

            if success:
                # Return the created user object
                user = await self.db_manager.get_user_by_username(admin_data.username)
                if user:
                    return user
                else:
                    return User(
                        id=1,
                        username=admin_data.username,
                        email=admin_data.email,
                        full_name=admin_data.full_name,
                        role=UserRole.ADMIN,
                        is_admin=True,
                        is_active=True,
                        permissions=[],
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create admin user",
                )

        @self.app.get("/api/auth/me", response_model=User)
        async def get_current_user_info(user: User = Depends(require_auth)):
            """Get current authenticated user information."""
            return user

        @self.app.get("/api/auth/setup-required")
        async def check_setup_required():
            """Check if initial setup is required."""
            required = await self.db_manager.is_setup_required()
            return {"setup_required": required}

        # Profile management endpoints
        @self.app.put("/api/auth/profile")
        async def update_profile(
            updates: Dict[str, Any], user: User = Depends(require_auth)
        ):
            """Update user profile (name and email)."""
            allowed_fields = {"full_name", "email"}
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

            if not filtered_updates:
                raise HTTPException(status_code=400, detail="No valid fields to update")

            success = await self.db_manager.update_user_profile(
                user.id, filtered_updates
            )
            if not success:
                raise HTTPException(status_code=400, detail="Failed to update profile")

            # Audit log profile update
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.USER_UPDATED,
                    severity=AuditSeverity.INFO,
                    user_id=user.id,
                    username=user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="user",
                    resource_id=str(user.id),
                    action="Profile updated",
                    details={"updated_fields": list(filtered_updates.keys())},
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            return {"message": "Profile updated successfully"}

        @self.app.post("/api/auth/change-password")
        async def change_password(
            password_data: Dict[str, str], user: User = Depends(require_auth)
        ):
            """Change user password."""
            current_password = password_data.get("current_password")
            new_password = password_data.get("new_password")

            if not current_password or not new_password:
                raise HTTPException(
                    status_code=400, detail="Both current and new passwords required"
                )

            # Verify current password
            stored_user = await self.db_manager.get_user_by_username(user.username)
            if not stored_user or not AuthManager.verify_password(
                current_password, stored_user.password
            ):
                raise HTTPException(
                    status_code=401, detail="Current password is incorrect"
                )

            # Update password
            hashed_password = AuthManager.hash_password(new_password)
            success = await self.db_manager.update_user_password(
                user.id, hashed_password
            )

            if not success:
                raise HTTPException(status_code=500, detail="Failed to update password")

            # Audit log password change
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.PASSWORD_CHANGE,
                    severity=AuditSeverity.WARNING,
                    user_id=user.id,
                    username=user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="user",
                    resource_id=str(user.id),
                    action="Password changed",
                    details={},
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            return {"message": "Password changed successfully"}

        @self.app.delete("/api/auth/account")
        async def delete_account(user: User = Depends(require_auth)):
            """Delete user account."""
            # Don't allow deleting the last admin account
            if user.role == UserRole.ADMIN:
                admin_count = await self.db_manager.count_admin_users()
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot delete the last administrator account",
                    )

            success = await self.db_manager.delete_user(user.id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete account")

            # Audit log account deletion
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.USER_DELETED,
                    severity=AuditSeverity.CRITICAL,
                    user_id=user.id,
                    username=user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="user",
                    resource_id=str(user.id),
                    action="Account deleted by user",
                    details={},
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            return {"message": "Account deleted successfully"}

        # 2FA endpoints
        @self.app.get("/api/auth/2fa/status")
        async def get_2fa_status(user: User = Depends(require_auth)):
            """Check if 2FA is enabled for the user."""
            totp_secret = await self.db_manager.get_user_totp_secret(user.id)
            return {"enabled": bool(totp_secret)}

        @self.app.post("/api/auth/2fa/setup")
        async def setup_2fa(user: User = Depends(require_auth)):
            """Setup 2FA for the user."""
            # Check if already enabled
            existing_secret = await self.db_manager.get_user_totp_secret(user.id)
            if existing_secret:
                raise HTTPException(status_code=400, detail="2FA is already enabled")

            # Generate secret
            secret = pyotp.random_base32()

            # Create TOTP URI for QR code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user.email or user.username, issuer_name="Kasa Monitor"
            )

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            # Store secret temporarily (not confirmed yet)
            await self.db_manager.store_temp_totp_secret(user.id, secret)

            return {"qr_code": f"data:image/png;base64,{img_str}", "secret": secret}

        @self.app.post("/api/auth/2fa/verify")
        async def verify_2fa(
            verification_data: Dict[str, str], user: User = Depends(require_auth)
        ):
            """Verify 2FA setup."""
            token = verification_data.get("token")
            if not token:
                raise HTTPException(
                    status_code=400, detail="Verification token required"
                )

            # Get temporary secret
            temp_secret = await self.db_manager.get_temp_totp_secret(user.id)
            if not temp_secret:
                raise HTTPException(status_code=400, detail="No 2FA setup in progress")

            # Verify token
            totp = pyotp.TOTP(temp_secret)
            if not totp.verify(token, valid_window=1):
                raise HTTPException(status_code=400, detail="Invalid verification code")

            # Save confirmed secret
            success = await self.db_manager.confirm_totp_secret(user.id, temp_secret)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to enable 2FA")

            # Audit log 2FA enabled
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.MFA_ENABLED,
                    severity=AuditSeverity.INFO,
                    user_id=user.id,
                    username=user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="user",
                    resource_id=str(user.id),
                    action="2FA enabled",
                    details={},
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            return {"message": "2FA enabled successfully"}

        @self.app.post("/api/auth/2fa/disable")
        async def disable_2fa(user: User = Depends(require_auth)):
            """Disable 2FA for the user."""
            success = await self.db_manager.disable_totp(user.id)
            if not success:
                raise HTTPException(status_code=400, detail="2FA is not enabled")

            # Audit log 2FA disabled
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.MFA_DISABLED,
                    severity=AuditSeverity.WARNING,
                    user_id=user.id,
                    username=user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="user",
                    resource_id=str(user.id),
                    action="2FA disabled",
                    details={},
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            return {"message": "2FA disabled successfully"}

        # User management endpoints
        @self.app.get("/api/users", response_model=List[User])
        async def get_users(
            user: User = Depends(require_permission(Permission.USERS_VIEW)),
        ):
            """Get all users."""
            users = await self.db_manager.get_all_users()
            # Remove password-related data for security
            for user_item in users:
                user_item.permissions = AuthManager.get_user_permissions(user_item.role)
            return users

        @self.app.post("/api/users", response_model=User)
        async def create_user(
            user_data: UserCreate,
            current_user: User = Depends(require_permission(Permission.USERS_INVITE)),
        ):
            """Create a new user."""
            new_user = await self.db_manager.create_user(user_data)
            if not new_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user (username or email may already exist)",
                )
            new_user.permissions = AuthManager.get_user_permissions(new_user.role)

            # Audit log user creation
            if self.audit_logger:
                audit_event = AuditEvent(
                    event_type=AuditEventType.USER_CREATED,
                    severity=AuditSeverity.INFO,
                    user_id=current_user.id,
                    username=current_user.username,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="user",
                    resource_id=str(new_user.id),
                    action="user_created",
                    details={
                        "created_username": new_user.username,
                        "role": new_user.role,
                        "email": new_user.email,
                    },
                    timestamp=datetime.now(),
                    success=True,
                )
                await self.audit_logger.log_event_async(audit_event)

            return new_user

        @self.app.put("/api/users/{user_id}")
        async def update_user(
            user_id: int,
            updates: Dict[str, Any],
            current_user: User = Depends(require_permission(Permission.USERS_EDIT)),
        ):
            """Update user information."""
            success = await self.db_manager.update_user(user_id, updates)
            if success:
                return {"message": "User updated successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update user")

        @self.app.patch("/api/users/{user_id}")
        async def patch_user(
            user_id: int,
            updates: Dict[str, Any],
            current_user: User = Depends(require_permission(Permission.USERS_EDIT)),
        ):
            """Partially update user information."""
            success = await self.db_manager.update_user(user_id, updates)
            if success:
                return {"message": "User updated successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update user")

        @self.app.delete("/api/users/{user_id}")
        async def delete_user(
            user_id: int,
            current_user: User = Depends(require_permission(Permission.USERS_REMOVE)),
        ):
            """Delete a user."""
            if user_id == current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete your own account",
                )

            # Get user info before deletion for audit log
            target_user = await self.db_manager.get_user_by_id(user_id)

            success = await self.db_manager.delete_user(user_id)
            if success:
                # Log successful user deletion
                if self.audit_logger and target_user:
                    deletion_event = AuditEvent(
                        event_type=AuditEventType.USER_DELETED,
                        severity=AuditSeverity.WARNING,
                        user_id=current_user.id,
                        username=current_user.username,
                        action="User deleted by admin",
                        details={
                            "deleted_user_id": user_id,
                            "deleted_username": target_user.username,
                            "deleted_user_role": (
                                target_user.role.value
                                if target_user.role
                                else "unknown"
                            ),
                            "deleted_user_email": target_user.email,
                            "deleted_by_admin": True,
                        },
                    )
                    await self.audit_logger.log_event_async(deletion_event)

                return {"message": "User deleted successfully"}
            else:
                # Log failed user deletion
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=current_user.id,
                        username=current_user.username,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="user",
                        resource_id=str(user_id),
                        action="User deletion failed",
                        details={
                            "target_user_id": user_id,
                            "error_message": "Database deletion failed",
                            "attempted_by_admin": True,
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message="Database deletion failed",
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(status_code=400, detail="Failed to delete user")

        # System configuration endpoints
        @self.app.get("/api/system/config")
        async def get_system_config(
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Get system configuration."""
            # Get configuration from database or use defaults
            config = {
                "ssl": {
                    "enabled": False,
                    "cert_path": "",
                    "key_path": "",
                    "force_https": False,
                    "port": int(os.getenv("HTTPS_PORT", "5273")),
                },
                "network": {
                    "host": "0.0.0.0",
                    "port": 5272,
                    "allowed_hosts": [],
                    "local_only": False,
                    "cors_origins": [],
                },
                "database_path": "kasa_monitor.db",
                "influxdb_enabled": False,
                "polling_interval": 30,
            }

            # Try to load saved config from database
            try:
                saved_config = await self.db_manager.get_all_system_config()
                for key, value in saved_config.items():
                    if "." in key:
                        # Handle nested keys like "ssl.enabled"
                        parts = key.split(".", 1)
                        if parts[0] in config and isinstance(config[parts[0]], dict):
                            # Convert string values to appropriate types
                            if value.lower() in ["true", "false"]:
                                config[parts[0]][parts[1]] = value.lower() == "true"
                            elif value.isdigit():
                                config[parts[0]][parts[1]] = int(value)
                            elif value.startswith("[") and value.endswith("]"):
                                # Handle array values
                                try:
                                    import json

                                    config[parts[0]][parts[1]] = json.loads(value)
                                except:
                                    config[parts[0]][parts[1]] = []
                            else:
                                config[parts[0]][parts[1]] = value
                    else:
                        # Handle top-level keys
                        if value.lower() in ["true", "false"]:
                            config[key] = value.lower() == "true"
                        elif value.isdigit():
                            config[key] = int(value)
                        else:
                            config[key] = value
            except Exception as e:
                logger.warning(f"Could not load saved config: {e}")

            return config

        @self.app.post("/api/system/config")
        async def update_system_config(
            config: Dict[str, Any],
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Update system configuration."""
            for key, value in config.items():
                await self.db_manager.set_system_config(key, str(value))
            return {"message": "Configuration updated"}

        @self.app.put("/api/system/config")
        async def update_system_config_put(
            config: Dict[str, Any],
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Update system configuration (PUT method)."""
            # Store configuration in database
            for key, value in config.items():
                if isinstance(value, dict):
                    # Handle nested configs like ssl, network
                    for sub_key, sub_value in value.items():
                        await self.db_manager.set_system_config(
                            f"{key}.{sub_key}", str(sub_value)
                        )
                else:
                    await self.db_manager.set_system_config(key, str(value))
            return {"message": "Configuration updated successfully"}

        # SSL/TLS Certificate management endpoints
        @self.app.get("/api/ssl/files")
        async def get_ssl_files(
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Get list of SSL files in the ssl directory."""
            try:
                # Use relative path for development, absolute path for production
                ssl_dir = Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                ssl_dir.mkdir(exist_ok=True)

                files = []
                for file_path in ssl_dir.iterdir():
                    if file_path.is_file():
                        stat = file_path.stat()
                        file_type = "Unknown"

                        # Determine file type based on extension
                        ext = file_path.suffix.lower()
                        if ext in [".crt", ".cer", ".pem"]:
                            file_type = "Certificate"
                        elif ext in [".key"]:
                            file_type = "Private Key"
                        elif ext in [".csr"]:
                            file_type = "Certificate Request"
                        elif ext in [".p12", ".pfx"]:
                            file_type = "PKCS#12"

                        files.append(
                            {
                                "filename": file_path.name,
                                "path": str(file_path),
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(
                                    stat.st_mtime
                                ).isoformat(),
                                "type": file_type,
                            }
                        )

                return {"files": files}

            except Exception as e:
                logger.error(f"Error listing SSL files: {e}")
                raise HTTPException(status_code=500, detail="Failed to list SSL files")

        @self.app.post("/api/ssl/generate-csr")
        async def generate_csr(
            csr_data: Dict[str, Any],
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Generate a Certificate Signing Request (CSR) and private key."""
            try:
                # Extract CSR parameters
                country = csr_data.get("country", "US")
                state = csr_data.get("state", "")
                city = csr_data.get("city", "")
                organization = csr_data.get("organization", "")
                organizational_unit = csr_data.get("organizational_unit", "")
                common_name = csr_data.get("common_name", "")
                email = csr_data.get("email", "")
                san_domains = csr_data.get("san_domains", [])
                key_size = csr_data.get("key_size", 2048)

                if not all([country, state, city, organization, common_name, email]):
                    raise HTTPException(
                        status_code=400, detail="Missing required CSR fields"
                    )

                # Create ssl directory
                ssl_dir = Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                ssl_dir.mkdir(exist_ok=True)

                # Generate timestamp for unique filenames
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                key_filename = f"{common_name}_{timestamp}.key"
                csr_filename = f"{common_name}_{timestamp}.csr"

                key_path = ssl_dir / key_filename
                csr_path = ssl_dir / csr_filename

                # Generate private key and CSR using OpenSSL
                import subprocess

                # Generate private key
                key_cmd = ["openssl", "genrsa", "-out", str(key_path), str(key_size)]

                result = subprocess.run(key_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Failed to generate private key: {result.stderr}")

                # Create config file for CSR
                config_content = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = {country}
ST = {state}
L = {city}
O = {organization}
OU = {organizational_unit}
CN = {common_name}
emailAddress = {email}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment"""

                if san_domains:
                    san_list = ", ".join([f"DNS:{domain}" for domain in san_domains])
                    config_content += f"\nsubjectAltName = {san_list}"

                config_path = ssl_dir / f"temp_config_{timestamp}.conf"
                with open(config_path, "w") as f:
                    f.write(config_content)

                try:
                    # Generate CSR
                    csr_cmd = [
                        "openssl",
                        "req",
                        "-new",
                        "-key",
                        str(key_path),
                        "-out",
                        str(csr_path),
                        "-config",
                        str(config_path),
                    ]

                    result = subprocess.run(csr_cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        raise Exception(f"Failed to generate CSR: {result.stderr}")

                finally:
                    # Clean up temporary config file
                    if config_path.exists():
                        config_path.unlink()

                return {
                    "message": "CSR and private key generated successfully",
                    "key_file": key_filename,
                    "csr_file": csr_filename,
                }

            except subprocess.CalledProcessError as e:
                logger.error(f"OpenSSL error: {e}")
                raise HTTPException(status_code=500, detail="OpenSSL command failed")
            except Exception as e:
                logger.error(f"Error generating CSR: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/ssl/download/{filename}")
        async def download_ssl_file(
            filename: str,
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Download an SSL file."""
            try:
                # Validate filename to prevent path traversal
                if (
                    not filename
                    or ".." in filename
                    or "/" in filename
                    or "\\" in filename
                ):
                    raise HTTPException(status_code=400, detail="Invalid filename")

                # Use safe basename only
                safe_filename = os.path.basename(filename)
                ssl_dir = Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                file_path = ssl_dir / safe_filename

                # Validate file exists and is within ssl directory
                if not file_path.exists():
                    raise HTTPException(status_code=404, detail="File not found")

                # Ensure the resolved path is still within ssl directory
                if not str(file_path.resolve()).startswith(str(ssl_dir.resolve())):
                    raise HTTPException(status_code=400, detail="Invalid file path")

                return FileResponse(
                    path=str(file_path),
                    filename=filename,
                    media_type="application/octet-stream",
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error downloading SSL file: {e}")
                raise HTTPException(status_code=500, detail="Failed to download file")

        @self.app.post("/api/ssl/download-multiple")
        async def download_multiple_ssl_files(
            file_data: Dict[str, List[str]],
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Download multiple SSL files as a ZIP archive."""
            try:
                filenames = file_data.get("filenames", [])
                if not filenames:
                    raise HTTPException(status_code=400, detail="No files specified")

                ssl_dir = Path("ssl") if not Path("/app").exists() else Path("/app/ssl")

                # Create temporary ZIP file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".zip"
                ) as tmp_zip:
                    with zipfile.ZipFile(tmp_zip.name, "w") as zf:
                        for filename in filenames:
                            file_path = ssl_dir / filename

                            if file_path.exists() and str(file_path).startswith(
                                str(ssl_dir)
                            ):
                                zf.write(file_path, filename)

                def cleanup_temp_file():
                    try:
                        os.unlink(tmp_zip.name)
                    except:
                        pass

                def file_generator():
                    try:
                        with open(tmp_zip.name, "rb") as f:
                            while True:
                                chunk = f.read(8192)
                                if not chunk:
                                    break
                                yield chunk
                    finally:
                        cleanup_temp_file()

                return StreamingResponse(
                    file_generator(),
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename=ssl_files.zip"
                    },
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating ZIP file: {e}")
                raise HTTPException(status_code=500, detail="Failed to create ZIP file")

        @self.app.delete("/api/ssl/files/{filename}")
        async def delete_ssl_file(
            filename: str,
            request_data: Dict[str, str],
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Delete an SSL file."""
            try:
                confirmation = request_data.get("confirmation", "")
                if confirmation.lower() != "delete":
                    raise HTTPException(status_code=400, detail="Invalid confirmation")

                # Validate filename to prevent path traversal
                if (
                    not filename
                    or ".." in filename
                    or "/" in filename
                    or "\\" in filename
                ):
                    raise HTTPException(status_code=400, detail="Invalid filename")

                # Use safe basename only
                safe_filename = os.path.basename(filename)
                ssl_dir = Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                file_path = ssl_dir / safe_filename

                # Validate file exists and is within ssl directory
                if not file_path.exists():
                    raise HTTPException(status_code=404, detail="File not found")

                # Ensure the resolved path is still within ssl directory
                if not str(file_path.resolve()).startswith(str(ssl_dir.resolve())):
                    raise HTTPException(status_code=400, detail="Invalid file path")

                # Delete the file
                file_path.unlink()

                # Log successful SSL file deletion
                if self.audit_logger:
                    config_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                        severity=AuditSeverity.WARNING,
                        user_id=user.id,
                        username=user.username,
                        action="SSL file deleted",
                        details={
                            "config_type": "ssl_file",
                            "deleted_filename": filename,
                            "deleted_path": str(file_path),
                            "confirmation_provided": confirmation.lower() == "delete",
                            "operation": "ssl_file_deletion",
                        },
                    )
                    await self.audit_logger.log_event_async(config_event)

                return {"message": f"File {filename} deleted successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error deleting SSL file: {e}")

                # Log SSL file deletion failure
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=user.id,
                        username=user.username,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="config",
                        resource_id=f"ssl_file_{filename}",
                        action="SSL file deletion failed",
                        details={
                            "config_type": "ssl_file",
                            "target_filename": filename,
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "operation": "ssl_file_deletion_failed",
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(status_code=500, detail="Failed to delete file")

        @self.app.post("/api/system/ssl/upload-cert")
        async def upload_ssl_certificate(
            file: UploadFile = File(...),
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Upload SSL certificate file."""
            try:
                # Secure file upload validation
                try:
                    from security_fixes.critical.file_upload_security import (
                        SecureFileUploadManager,
                    )

                    upload_manager = SecureFileUploadManager()
                    upload_result = await upload_manager.handle_upload(file, "ssl_cert")

                    # Move approved file to SSL directory
                    ssl_dir = (
                        Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                    )
                    ssl_dir.mkdir(exist_ok=True)
                    file_path = ssl_dir / file.filename

                    if upload_manager.approve_quarantined_file(
                        upload_result["quarantine_path"], str(file_path)
                    ):
                        logger.info(
                            f"SSL certificate uploaded successfully: {file.filename}"
                        )

                        # Store certificate path in database
                        await self.db_manager.set_system_config(
                            "ssl.cert_path", str(file_path)
                        )
                        logger.info(
                            f"SSL certificate path stored in database: {file_path}"
                        )

                        # Check if both cert and key exist, then enable SSL
                        ssl_key_path = await self.db_manager.get_system_config(
                            "ssl.key_path"
                        )
                        if ssl_key_path and Path(ssl_key_path).exists():
                            await self.db_manager.set_system_config(
                                "ssl.enabled", "true"
                            )
                            logger.info(
                                "SSL enabled - both certificate and key are present"
                            )
                    else:
                        raise HTTPException(
                            status_code=500, detail="Failed to move certificate file"
                        )

                except ImportError:
                    logger.warning(
                        "Secure file upload not available, using basic validation"
                    )
                    # Fallback to basic validation
                    if not file.filename or not file.filename.endswith(
                        (".crt", ".cer", ".pem")
                    ):
                        raise HTTPException(
                            status_code=400, detail="Invalid certificate file type"
                        )

                    # Basic size check
                    content = await file.read()
                    if len(content) > 5 * 1024 * 1024:  # 5MB limit for certificates
                        raise HTTPException(
                            status_code=400, detail="Certificate file too large"
                        )

                    # Validate certificate format
                    if (
                        b"-----BEGIN CERTIFICATE-----" not in content
                        or b"-----END CERTIFICATE-----" not in content
                    ):
                        raise HTTPException(
                            status_code=400, detail="Invalid certificate format"
                        )

                    ssl_dir = (
                        Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                    )
                    ssl_dir.mkdir(exist_ok=True)
                    file_path = ssl_dir / file.filename

                    with open(file_path, "wb") as f:
                        f.write(content)

                    # Store certificate path in database
                    await self.db_manager.set_system_config(
                        "ssl.cert_path", str(file_path)
                    )
                    logger.info(f"SSL certificate path stored in database: {file_path}")

                    # Check if both cert and key exist, then enable SSL
                    ssl_key_path = await self.db_manager.get_system_config(
                        "ssl.key_path"
                    )
                    if ssl_key_path and Path(ssl_key_path).exists():
                        await self.db_manager.set_system_config("ssl.enabled", "true")
                        logger.info(
                            "SSL enabled - both certificate and key are present"
                        )

                # Log successful certificate upload
                if self.audit_logger:
                    config_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                        severity=AuditSeverity.INFO,
                        user_id=user.id,
                        username=user.username,
                        action="SSL certificate uploaded",
                        details={
                            "config_type": "ssl_certificate",
                            "certificate_filename": file.filename,
                            "certificate_path": str(file_path),
                            "file_size_bytes": len(content),
                            "operation": "certificate_upload",
                        },
                    )
                    await self.audit_logger.log_event_async(config_event)

                return {
                    "message": "Certificate uploaded successfully",
                    "path": str(file_path),
                    "filename": file.filename,
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error uploading certificate: {e}")

                # Log certificate upload failure
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=user.id,
                        username=user.username,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="config",
                        resource_id=f"ssl_certificate_{getattr(file, 'filename', 'unknown')}",
                        action="SSL certificate upload failed",
                        details={
                            "config_type": "ssl_certificate",
                            "certificate_filename": getattr(
                                file, "filename", "unknown"
                            ),
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "operation": "certificate_upload_failed",
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(
                    status_code=500, detail="Failed to upload certificate"
                )

        @self.app.post("/api/system/ssl/upload-key")
        async def upload_ssl_private_key(
            file: UploadFile = File(...),
            user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
        ):
            """Upload SSL private key file."""
            try:
                # Secure file upload validation
                try:
                    from security_fixes.critical.file_upload_security import (
                        SecureFileUploadManager,
                    )

                    upload_manager = SecureFileUploadManager()
                    upload_result = await upload_manager.handle_upload(file, "ssl_key")

                    # Move approved file to SSL directory
                    ssl_dir = (
                        Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                    )
                    ssl_dir.mkdir(exist_ok=True)
                    file_path = ssl_dir / file.filename

                    if upload_manager.approve_quarantined_file(
                        upload_result["quarantine_path"], str(file_path)
                    ):
                        # Set restrictive permissions on private key
                        os.chmod(file_path, 0o600)
                        logger.info(
                            f"SSL private key uploaded successfully: {file.filename}"
                        )

                        # Store private key path in database
                        await self.db_manager.set_system_config(
                            "ssl.key_path", str(file_path)
                        )
                        logger.info(
                            f"SSL private key path stored in database: {file_path}"
                        )

                        # Check if both cert and key exist, then enable SSL
                        ssl_cert_path = await self.db_manager.get_system_config(
                            "ssl.cert_path"
                        )
                        if ssl_cert_path and Path(ssl_cert_path).exists():
                            await self.db_manager.set_system_config(
                                "ssl.enabled", "true"
                            )
                            logger.info(
                                "SSL enabled - both certificate and key are present"
                            )
                    else:
                        raise HTTPException(
                            status_code=500, detail="Failed to move private key file"
                        )

                except ImportError:
                    logger.warning(
                        "Secure file upload not available, using basic validation"
                    )
                    # Fallback to basic validation
                    if not file.filename or not file.filename.endswith(
                        (".key", ".pem")
                    ):
                        raise HTTPException(
                            status_code=400, detail="Invalid private key file type"
                        )

                    # Basic size check
                    content = await file.read()
                    if len(content) > 5 * 1024 * 1024:  # 5MB limit for keys
                        raise HTTPException(
                            status_code=400, detail="Private key file too large"
                        )

                    # Validate private key format
                    if (
                        b"-----BEGIN" not in content
                        or b"-----END" not in content
                        or b"PRIVATE KEY" not in content
                    ):
                        raise HTTPException(
                            status_code=400, detail="Invalid private key format"
                        )

                    ssl_dir = (
                        Path("ssl") if not Path("/app").exists() else Path("/app/ssl")
                    )
                    ssl_dir.mkdir(exist_ok=True)
                    file_path = ssl_dir / file.filename

                    with open(file_path, "wb") as f:
                        f.write(content)

                    # Set restrictive permissions on private key
                    os.chmod(file_path, 0o600)

                    # Store private key path in database
                    await self.db_manager.set_system_config(
                        "ssl.key_path", str(file_path)
                    )
                    logger.info(f"SSL private key path stored in database: {file_path}")

                    # Check if both cert and key exist, then enable SSL
                    ssl_cert_path = await self.db_manager.get_system_config(
                        "ssl.cert_path"
                    )
                    if ssl_cert_path and Path(ssl_cert_path).exists():
                        await self.db_manager.set_system_config("ssl.enabled", "true")
                        logger.info(
                            "SSL enabled - both certificate and key are present"
                        )

                # Log successful private key upload
                if self.audit_logger:
                    config_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                        severity=AuditSeverity.INFO,
                        user_id=user.id,
                        username=user.username,
                        action="SSL private key uploaded",
                        details={
                            "config_type": "ssl_private_key",
                            "key_filename": file.filename,
                            "key_path": str(file_path),
                            "file_size_bytes": len(content),
                            "permissions_set": "0o600",
                            "operation": "private_key_upload",
                        },
                    )
                    await self.audit_logger.log_event_async(config_event)

                return {
                    "message": "Private key uploaded successfully",
                    "path": str(file_path),
                    "filename": file.filename,
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error uploading private key: {e}")

                # Log private key upload failure
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=user.id,
                        username=user.username,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="config",
                        resource_id=f"ssl_private_key_{getattr(file, 'filename', 'unknown')}",
                        action="SSL private key upload failed",
                        details={
                            "config_type": "ssl_private_key",
                            "key_filename": getattr(file, "filename", "unknown"),
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "operation": "private_key_upload_failed",
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(
                    status_code=500, detail="Failed to upload private key"
                )

        # Permission management endpoints
        @self.app.get("/api/permissions")
        async def get_all_permissions(
            user: User = Depends(require_permission(Permission.USERS_VIEW)),
        ):
            """Get all available permissions."""
            permissions = []
            category_map = {
                "devices": "device_management",
                "rates": "rate_management",
                "costs": "rate_management",
                "users": "user_management",
                "system": "system_config",
            }

            # Import Permission enum to iterate through it
            from models import Permission

            # Get all permission values
            for perm_name in Permission.__members__:
                perm = Permission[perm_name]
                parts = perm.value.split(".")
                category_key = parts[0] if len(parts) > 0 else "other"
                category = category_map.get(category_key, "other")

                # Create a more readable description
                if len(parts) > 1:
                    action = parts[1].replace("_", " ").title()
                    resource = parts[0].title()
                    description = f"{action} {resource}"
                else:
                    description = (
                        perm.value.replace(".", " - ").replace("_", " ").title()
                    )

                permissions.append(
                    {
                        "name": perm.value,
                        "description": description,
                        "category": category,
                    }
                )
            return permissions

        @self.app.get("/api/roles/permissions")
        async def get_roles_permissions(
            user: User = Depends(require_permission(Permission.USERS_VIEW)),
        ):
            """Get permissions for all roles."""
            from auth import ROLE_PERMISSIONS
            from models import UserRole

            role_perms = []
            for role in UserRole:
                role_perms.append(
                    {
                        "role": role.value,
                        "permissions": [
                            p.value for p in ROLE_PERMISSIONS.get(role, [])
                        ],
                    }
                )
            return role_perms

        @self.app.put("/api/roles/{role}/permissions")
        async def update_role_permissions(
            role: str,
            permissions: List[str],
            user: User = Depends(require_permission(Permission.USERS_PERMISSIONS)),
        ):
            """Update permissions for a role (admin only)."""
            # Note: This would need database storage for custom role permissions
            # For now, return success but note that default roles have fixed permissions
            return {
                "message": f"Permissions updated for role {role}",
                "note": "Default roles have fixed permissions",
            }

        @self.app.post("/api/roles/{role}/permissions")
        async def toggle_role_permission(
            role: str,
            request: dict,
            user: User = Depends(require_permission(Permission.USERS_PERMISSIONS)),
        ):
            """Toggle a single permission for a role."""
            permission = request.get("permission")
            action = request.get("action", "toggle")

            # Note: This would need database storage for custom role permissions
            # For now, return success but note that default roles have fixed permissions
            return {
                "message": f"Permission {permission} {action} for role {role}",
                "note": "Default roles have fixed permissions",
            }

    def setup_socketio(self):
        """Set up Socket.IO for real-time updates."""

        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"Client {sid} connected")
            await self.sio.emit("connected", {"data": "Connected to server"}, to=sid)

        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Client {sid} disconnected")

        @self.sio.event
        async def subscribe_device(sid, data):
            device_ip = data.get("device_ip")
            await self.sio.enter_room(sid, f"device_{device_ip}")
            logger.info(f"Client {sid} subscribed to device {device_ip}")

        @self.sio.event
        async def unsubscribe_device(sid, data):
            device_ip = data.get("device_ip")
            await self.sio.leave_room(sid, f"device_{device_ip}")
            logger.info(f"Client {sid} unsubscribed from device {device_ip}")

        # Mount Socket.IO app
        self.app = socketio.ASGIApp(self.sio, self.app)

    def setup_data_management_routes(self):
        """Set up data management routes if available."""
        if not data_management_available:
            return

        from fastapi.responses import StreamingResponse

        # Export endpoints
        @self.app.post("/api/export/devices")
        async def export_devices(
            format: str = "csv",
            include_energy: bool = True,
            user: User = Depends(require_permission(Permission.DATA_EXPORT)),
        ):
            """Export device data in various formats."""
            if not self.data_exporter:
                raise HTTPException(
                    status_code=503, detail="Export service not available"
                )

            export_start_time = datetime.now()

            try:
                if format == "csv":
                    content = await self.data_exporter.export_devices_csv()
                    filename = "devices.csv"
                    media_type = "text/csv"
                elif format == "excel":
                    content = await self.data_exporter.export_devices_excel(
                        include_energy=include_energy
                    )
                    filename = "devices.xlsx"
                    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    raise HTTPException(status_code=400, detail="Unsupported format")

                # Log successful data export
                if self.audit_logger:
                    export_event = AuditEvent(
                        event_type=AuditEventType.DATA_EXPORT,
                        severity=AuditSeverity.INFO,
                        user_id=user.id,
                        username=user.username,
                        action="Device data exported",
                        details={
                            "export_type": "devices",
                            "format": format,
                            "include_energy": include_energy,
                            "filename": filename,
                            "export_size_bytes": len(content),
                            "export_duration_ms": (
                                datetime.now() - export_start_time
                            ).total_seconds()
                            * 1000,
                            "export_timestamp": export_start_time.isoformat(),
                        },
                    )
                    await self.audit_logger.log_event_async(export_event)

                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )

            except Exception as e:
                # Log failed data export
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=user.id,
                        username=user.username,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="data",
                        resource_id="device_export",
                        action="Device data export failed",
                        details={
                            "export_type": "devices",
                            "format": format,
                            "include_energy": include_energy,
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "export_duration_ms": (
                                datetime.now() - export_start_time
                            ).total_seconds()
                            * 1000,
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/export/energy")
        async def export_energy(
            device_ip: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            format: str = "csv",
            user: User = Depends(require_permission(Permission.DATA_EXPORT)),
        ):
            """Export energy consumption data."""
            if not self.data_exporter:
                raise HTTPException(
                    status_code=503, detail="Export service not available"
                )

            export_start_time = datetime.now()

            try:
                if format == "csv":
                    content = await self.data_exporter.export_energy_data_csv(
                        device_ip=device_ip, start_date=start_date, end_date=end_date
                    )
                    filename = "energy_data.csv"
                    media_type = "text/csv"
                else:
                    raise HTTPException(status_code=400, detail="Unsupported format")

                # Log successful energy data export
                if self.audit_logger:
                    export_event = AuditEvent(
                        event_type=AuditEventType.DATA_EXPORT,
                        severity=AuditSeverity.INFO,
                        user_id=user.id,
                        username=user.username,
                        action="Energy data exported",
                        details={
                            "export_type": "energy_data",
                            "format": format,
                            "device_ip": device_ip,
                            "start_date": (
                                start_date.isoformat() if start_date else None
                            ),
                            "end_date": end_date.isoformat() if end_date else None,
                            "filename": filename,
                            "export_size_bytes": len(content),
                            "export_duration_ms": (
                                datetime.now() - export_start_time
                            ).total_seconds()
                            * 1000,
                            "export_timestamp": export_start_time.isoformat(),
                        },
                    )
                    await self.audit_logger.log_event_async(export_event)

                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )

            except Exception as e:
                # Log failed energy data export
                if self.audit_logger:
                    error_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=user.id,
                        username=user.username,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="data",
                        resource_id=(
                            f"energy_export_{device_ip}"
                            if device_ip
                            else "energy_export_all"
                        ),
                        action="Energy data export failed",
                        details={
                            "export_type": "energy_data",
                            "format": format,
                            "device_ip": device_ip,
                            "start_date": (
                                start_date.isoformat() if start_date else None
                            ),
                            "end_date": end_date.isoformat() if end_date else None,
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "export_duration_ms": (
                                datetime.now() - export_start_time
                            ).total_seconds()
                            * 1000,
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=str(e),
                    )
                    await self.audit_logger.log_event_async(error_event)

                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/export/report")
        async def generate_report(
            report_type: str = "monthly",
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
        ):
            """Generate PDF report."""
            if not self.data_exporter:
                raise HTTPException(
                    status_code=503, detail="Export service not available"
                )

            try:
                content = await self.data_exporter.generate_pdf_report(
                    report_type=report_type, start_date=start_date, end_date=end_date
                )
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename={report_type}_report.pdf"
                    },
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Aggregation endpoints
        @self.app.get("/api/aggregation")
        async def get_aggregated_data(
            period: str = "day",
            device_ip: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
        ):
            """Get aggregated data for specified period."""
            if not self.data_aggregator:
                raise HTTPException(
                    status_code=503, detail="Aggregation service not available"
                )

            try:
                from data_aggregation import AggregationPeriod

                period_enum = AggregationPeriod(period.lower())
                data = await self.data_aggregator.get_aggregated_data(
                    device_ip=device_ip,
                    period=period_enum,
                    start_date=start_date,
                    end_date=end_date,
                )
                return data
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid aggregation period"
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/statistics/{device_ip}")
        async def get_device_statistics(
            device_ip: str,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
        ):
            """Get statistical analysis for a device."""
            if not self.data_aggregator:
                raise HTTPException(
                    status_code=503, detail="Aggregation service not available"
                )

            try:
                stats = await self.data_aggregator.calculate_statistics(
                    device_ip=device_ip, start_date=start_date, end_date=end_date
                )
                return {
                    "device_ip": device_ip,
                    "statistics": stats,
                    "start_date": start_date or datetime.now() - timedelta(days=30),
                    "end_date": end_date or datetime.now(),
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/trends/{device_ip}")
        async def get_trend_analysis(
            device_ip: str, period: str = "day", lookback: int = 30
        ):
            """Get trend analysis for a device."""
            if not self.data_aggregator:
                raise HTTPException(
                    status_code=503, detail="Aggregation service not available"
                )

            try:
                from data_aggregation import AggregationPeriod

                period_enum = AggregationPeriod(period.lower())
                analysis = await self.data_aggregator.get_trend_analysis(
                    device_ip=device_ip, period=period_enum, lookback_periods=lookback
                )
                return {"device_ip": device_ip, **analysis}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid period")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Cache management (if Redis available)
        if self.cache_manager:

            @self.app.get("/api/cache/stats")
            async def get_cache_stats():
                """Get cache statistics."""
                return self.cache_manager.get_stats()

            @self.app.post("/api/cache/clear")
            async def clear_cache(pattern: Optional[str] = None):
                """Clear cache entries."""
                count = await self.cache_manager.clear(pattern)
                return {"status": "success", "cleared": count}

    def setup_monitoring_routes(self):
        """Setup monitoring-related API routes."""

        # Health check endpoints
        if self.health_monitor:

            @self.app.get("/api/health")
            async def health_check():
                """Basic health check endpoint."""
                return await self.health_monitor.get_liveness()

            @self.app.get("/api/ready")
            async def readiness_check():
                """Readiness check endpoint."""
                return await self.health_monitor.get_readiness()

            @self.app.get("/api/health/detailed")
            async def detailed_health(
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Detailed health status with all components."""
                return await self.health_monitor.perform_health_check()

        # Prometheus metrics endpoint
        if self.prometheus_metrics:

            @self.app.get("/api/metrics")
            async def get_metrics():
                """Prometheus metrics endpoint."""
                return Response(
                    content=self.prometheus_metrics.get_metrics(),
                    media_type="text/plain",
                )

        # Alert management endpoints
        if self.alert_manager:

            @self.app.get("/api/alerts")
            async def get_alerts(
                severity: Optional[str] = None,
                status: Optional[str] = None,
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_VIEW)
                ),
            ):
                """Get active alerts."""
                # Return empty list for now - AlertManager needs different parameters
                return []

            @self.app.get("/api/alerts/rules")
            async def get_alert_rules(
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_VIEW)
                ),
            ):
                """Get configured alert rules."""
                return await self.alert_manager.get_rules()

            @self.app.post("/api/alerts/rules")
            async def create_alert_rule(
                rule: Dict[str, Any],
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_EDIT)
                ),
            ):
                """Create a new alert rule."""
                return await self.alert_manager.create_rule(rule)

            @self.app.delete("/api/alerts/rules/{rule_id}")
            async def delete_alert_rule(
                rule_id: int,
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_EDIT)
                ),
            ):
                """Delete an alert rule."""
                success = await self.alert_manager.delete_rule(rule_id)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Rule not found")

            @self.app.post("/api/alerts/{alert_id}/acknowledge")
            async def acknowledge_alert(
                alert_id: int,
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_EDIT)
                ),
            ):
                """Acknowledge an alert."""
                success = await self.alert_manager.acknowledge_alert(
                    alert_id, user_id=current_user.id
                )
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Alert not found")

            @self.app.get("/api/alerts/history")
            async def get_alert_history(
                start_date: Optional[datetime] = None,
                end_date: Optional[datetime] = None,
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_VIEW)
                ),
            ):
                """Get alert history."""
                # Return empty list for now - AlertManager doesn't have get_history method
                return []

        # Device groups endpoints
        if self.device_group_manager:

            @self.app.get("/api/device-groups")
            async def get_device_groups(
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_VIEW)
                ),
            ):
                """Get all device groups."""
                return self.device_group_manager.get_all_groups()

            @self.app.get("/api/device-groups/{group_id}")
            async def get_device_group(
                group_id: int,
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_VIEW)
                ),
            ):
                """Get a specific device group."""
                group = self.device_group_manager.get_group(group_id)
                if group:
                    return group
                raise HTTPException(status_code=404, detail="Group not found")

            @self.app.post("/api/device-groups")
            async def create_device_group(
                group_data: Dict[str, Any],
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_EDIT)
                ),
            ):
                """Create a new device group."""
                return self.device_group_manager.create_group(group_data)

            @self.app.put("/api/device-groups/{group_id}")
            async def update_device_group(
                group_id: int,
                group_data: Dict[str, Any],
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_EDIT)
                ),
            ):
                """Update a device group."""
                success = self.device_group_manager.update_group(group_id, group_data)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Group not found")

            @self.app.delete("/api/device-groups/{group_id}")
            async def delete_device_group(
                group_id: int,
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_EDIT)
                ),
            ):
                """Delete a device group."""
                success = self.device_group_manager.delete_group(group_id)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Group not found")

            @self.app.post("/api/device-groups/{group_id}/control")
            async def control_device_group(
                group_id: int,
                action: Dict[str, str],
                current_user: User = Depends(
                    require_permission(Permission.DEVICES_CONTROL)
                ),
            ):
                """Control all devices in a group."""
                result = self.device_group_manager.control_group(
                    group_id, action.get("action", "off")
                )
                return {"status": "success", "result": result}

        # Backup and restore endpoints
        if self.backup_manager:

            @self.app.get("/api/backups")
            async def get_backups(
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Get list of available backups."""
                return await self.backup_manager.list_backups()

            @self.app.get("/api/backups/progress")
            async def get_backup_progress(
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Get current backup progress."""
                return self.backup_manager.get_backup_progress()

            @self.app.post("/api/backups/create")
            async def create_backup(
                backup_options: Dict[str, Any],
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Create a new backup."""
                backup_info = await self.backup_manager.create_backup(
                    backup_type=backup_options.get("type", "manual"),
                    description=backup_options.get("description"),
                    compress=backup_options.get("compress", True),
                    encrypt=backup_options.get("encrypt", False),
                )

                # Check if backup failed
                if backup_info.get("status") == "failed":
                    error_msg = backup_info.get("error", "Unknown error occurred")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Backup failed: {error_msg}",
                    )

                return {"status": "success", "backup": backup_info}

            @self.app.get("/api/backups/{filename}/download")
            async def download_backup(
                filename: str,
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Download a backup file."""
                file_path = await self.backup_manager.get_backup_file_by_name(filename)
                if file_path and os.path.exists(file_path):
                    from fastapi.responses import FileResponse

                    return FileResponse(
                        path=file_path,
                        filename=filename,
                        media_type="application/octet-stream",
                    )
                raise HTTPException(status_code=404, detail="Backup not found")

            @self.app.delete("/api/backups/{filename}")
            async def delete_backup(
                filename: str,
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Delete a backup."""
                success = await self.backup_manager.delete_backup_by_name(filename)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Backup not found")

            @self.app.post("/api/backups/restore")
            async def restore_backup(
                request: Request,
                backup: UploadFile,
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Restore from a backup file."""
                import shutil
                import tempfile

                # Check if backup manager is available
                if not self.backup_manager:
                    raise HTTPException(
                        status_code=503, detail="Backup service not available"
                    )

                # Get client IP for audit logging
                client_ip = request.client.host if request.client else "unknown"

                # Validate file extension
                allowed_extensions = [".db", ".sql", ".backup", ".7z"]
                file_ext = os.path.splitext(backup.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}",
                    )

                # Log the restore initiation to the current database
                if self.audit_logger:
                    event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_BACKUP_RESTORED,
                        severity=AuditSeverity.INFO,
                        user_id=current_user.id,
                        username=current_user.username,
                        ip_address=client_ip,
                        user_agent=request.headers.get("user-agent"),
                        session_id=None,
                        resource_type="backup",
                        resource_id=backup.filename,
                        action="restore_initiated",
                        details={
                            "backup_file": backup.filename,
                            "file_size": (
                                backup.size if hasattr(backup, "size") else None
                            ),
                        },
                        timestamp=datetime.now(),
                        success=True,
                    )
                    await self.audit_logger.log_event_async(event)

                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=file_ext
                ) as tmp_file:
                    content = await backup.read()
                    tmp_file.write(content)
                    temp_path = tmp_file.name

                try:
                    # Prepare user info for audit logging
                    user_info = {
                        "id": current_user.id,
                        "username": current_user.username,
                        "ip_address": client_ip,
                    }

                    # Restore the backup
                    result = await self.backup_manager.restore_uploaded_backup(
                        temp_path, backup.filename, user_info=user_info
                    )

                    if result.get("status") == "completed":
                        # Log successful restore to the restored database
                        if self.audit_logger:
                            event = AuditEvent(
                                event_type=AuditEventType.SYSTEM_BACKUP_RESTORED,
                                severity=AuditSeverity.INFO,
                                user_id=current_user.id,
                                username=current_user.username,
                                ip_address=client_ip,
                                user_agent=request.headers.get("user-agent"),
                                session_id=None,
                                resource_type="backup",
                                resource_id=backup.filename,
                                action="restore_completed",
                                details={
                                    "backup_file": backup.filename,
                                    "restore_id": result.get("restore_id"),
                                    "pre_restore_backup": result.get(
                                        "pre_restore_backup"
                                    ),
                                },
                                timestamp=datetime.now(),
                                success=True,
                            )
                            await self.audit_logger.log_event_async(event)

                        # Verify audit log was properly recorded
                        if result.get("restore_id") and self.backup_manager:
                            await self.backup_manager.verify_restore_audit_log(
                                result["restore_id"]
                            )

                        return {
                            "status": "success",
                            "message": "Backup restored successfully",
                            "restore_id": result.get("restore_id"),
                        }
                    else:
                        # Log failed restore
                        if self.audit_logger:
                            event = AuditEvent(
                                event_type=AuditEventType.SYSTEM_BACKUP_RESTORED,
                                severity=AuditSeverity.ERROR,
                                user_id=current_user.id,
                                username=current_user.username,
                                ip_address=client_ip,
                                user_agent=request.headers.get("user-agent"),
                                session_id=None,
                                resource_type="backup",
                                resource_id=backup.filename,
                                action="restore_failed",
                                details={
                                    "backup_file": backup.filename,
                                    "error": result.get("error", "Unknown error"),
                                },
                                timestamp=datetime.now(),
                                success=False,
                                error_message=result.get("error", "Unknown error"),
                            )
                            await self.audit_logger.log_event_async(event)
                        raise HTTPException(
                            status_code=500,
                            detail=result.get("error", "Restore failed"),
                        )
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            @self.app.get("/api/backups/schedules")
            async def get_backup_schedules(
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Get backup schedules."""
                return await self.backup_manager.get_schedules()

            @self.app.post("/api/backups/schedules")
            async def create_backup_schedule(
                schedule_data: Dict[str, Any],
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Create a new backup schedule."""
                schedule = await self.backup_manager.create_schedule(schedule_data)
                return {"status": "success", "schedule": schedule}

            @self.app.put("/api/backups/schedules/{schedule_id}")
            async def update_backup_schedule(
                schedule_id: int,
                schedule_data: Dict[str, Any],
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Update a backup schedule."""
                success = await self.backup_manager.update_schedule(
                    schedule_id, schedule_data
                )
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Schedule not found")

            @self.app.delete("/api/backups/schedules/{schedule_id}")
            async def delete_backup_schedule(
                schedule_id: int,
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_CONFIG)
                ),
            ):
                """Delete a backup schedule."""
                success = await self.backup_manager.delete_schedule(schedule_id)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Schedule not found")

        # Audit logging endpoints
        if self.audit_logger:

            @self.app.get("/api/audit-logs")
            async def get_audit_logs(
                page: int = 1,
                category: Optional[str] = None,
                severity: Optional[str] = None,
                range: str = "7days",
                search: Optional[str] = None,
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_LOGS)
                ),
            ):
                """Get audit logs."""
                logs, total_pages = await self.audit_logger.get_logs(
                    page=page,
                    category=category,
                    severity=severity,
                    date_range=range,
                    search=search,
                )
                return {"logs": logs, "total_pages": total_pages, "current_page": page}

            @self.app.post("/api/audit-logs/export")
            async def export_audit_logs(
                export_options: Dict[str, Any],
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_LOGS)
                ),
            ):
                """Export audit logs."""
                file_path = await self.audit_logger.export_logs(
                    format=export_options.get("format", "csv"),
                    date_range=export_options.get("date_range"),
                    category=export_options.get("category"),
                )
                if file_path:
                    import os

                    filename = os.path.basename(file_path)
                    return FileResponse(
                        file_path,
                        media_type="application/octet-stream",
                        filename=filename,
                    )
                raise HTTPException(status_code=500, detail="Failed to export logs")

            @self.app.delete("/api/audit-logs/clear")
            async def clear_audit_logs(
                before_date: Optional[str] = None,
                current_user: User = Depends(
                    require_permission(Permission.SYSTEM_LOGS_CLEAR)
                ),
            ):
                """Clear audit logs before specified date or all logs."""
                try:
                    date_obj = None
                    if before_date:
                        from datetime import datetime

                        date_obj = datetime.fromisoformat(
                            before_date.replace("Z", "+00:00")
                        )

                    deleted_count = await self.audit_logger.clear_logs(
                        before_date=date_obj
                    )

                    # Log the clear action
                    if self.audit_logger:
                        audit_event = AuditEvent(
                            event_type=AuditEventType.DATA_DELETED,
                            severity=AuditSeverity.WARNING,
                            user_id=current_user.id,
                            username=current_user.username,
                            ip_address=None,  # Could extract from request
                            user_agent=None,
                            session_id=None,
                            resource_type="audit_logs",
                            resource_id=None,
                            action="clear_audit_logs",
                            details={
                                "deleted_count": deleted_count,
                                "before_date": before_date,
                            },
                            timestamp=datetime.now(),
                            success=True,
                        )
                        await self.audit_logger.log_event_async(audit_event)

                    return {"message": f"Cleared {deleted_count} audit log entries"}
                except Exception as e:
                    raise HTTPException(
                        status_code=500, detail=f"Failed to clear logs: {str(e)}"
                    )

    def setup_plugin_routes(self):
        """Setup plugin system API routes."""
        if self.plugin_api_router:
            # Plugin API routes are already registered in PluginAPIRouter.__init__()
            logger.info("Plugin API routes registered")

    async def load_saved_devices(self):
        """Load saved devices from database on startup."""
        try:
            saved_devices = await self.db_manager.get_monitored_devices()
            logger.info(f"Loading {len(saved_devices)} saved devices from database")

            for device_info in saved_devices:
                try:
                    # Try to connect to the device
                    device = await SmartDevice.connect(
                        device_info["device_ip"],
                        credentials=self.device_manager.credentials,
                    )
                    await device.update()
                    self.device_manager.devices[device_info["device_ip"]] = device
                    logger.info(
                        f"Connected to saved device: {device_info['alias']} ({device_info['device_ip']})"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not connect to saved device {device_info['alias']} ({device_info['device_ip']}): {e}"
                    )
        except Exception as e:
            logger.error(f"Error loading saved devices: {e}")

    async def poll_and_store_data(self):
        """Poll all devices and store data in database."""
        import time

        polling_start_time = time.time()

        try:
            # Only poll devices that are being monitored
            monitored = await self.db_manager.get_monitored_devices()
            monitored_ips = {d["device_ip"] for d in monitored}

            # Filter devices to only poll monitored ones
            device_data_list = []
            failed_devices = []

            for ip in monitored_ips:
                if ip in self.device_manager.devices:
                    try:
                        device_data = await self.device_manager.get_device_data(ip)
                        if device_data:
                            device_data_list.append(device_data)
                        else:
                            failed_devices.append(ip)
                    except Exception as e:
                        failed_devices.append(ip)
                        logger.warning(f"Failed to poll device {ip}: {e}")

            for device_data in device_data_list:
                # Store in database
                await self.db_manager.store_device_reading(device_data)

                # Emit real-time update via Socket.IO
                await self.sio.emit(
                    "device_update", device_data.dict(), room=f"device_{device_data.ip}"
                )

            polling_duration_ms = (time.time() - polling_start_time) * 1000

            # Log slow polling cycles (>10 seconds)
            if polling_duration_ms > 10000 and self.audit_logger:
                performance_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    severity=AuditSeverity.WARNING,
                    user_id=None,
                    username=None,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="system",
                    resource_id="device_polling",
                    action="Slow device polling cycle detected",
                    details={
                        "performance_monitoring": True,
                        "polling_duration_ms": polling_duration_ms,
                        "devices_polled": len(device_data_list),
                        "devices_failed": len(failed_devices),
                        "failed_device_ips": failed_devices,
                        "threshold_exceeded": "10000ms",
                        "monitored_device_count": len(monitored_ips),
                    },
                    timestamp=datetime.now(),
                    success=False,
                    error_message=f"Device polling cycle exceeded threshold: {polling_duration_ms:.1f}ms > 10000ms",
                )
                await self.audit_logger.log_event_async(performance_event)

            # Log excessive device failures (>20% failure rate)
            if len(monitored_ips) > 0:
                failure_rate = len(failed_devices) / len(monitored_ips)
                if failure_rate > 0.2 and self.audit_logger:
                    reliability_event = AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.ERROR,
                        user_id=None,
                        username=None,
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="system",
                        resource_id="device_polling_reliability",
                        action="High device polling failure rate detected",
                        details={
                            "performance_monitoring": True,
                            "failure_rate": failure_rate,
                            "failed_devices": len(failed_devices),
                            "total_devices": len(monitored_ips),
                            "failed_device_ips": failed_devices,
                            "threshold_exceeded": "20% failure rate",
                        },
                        timestamp=datetime.now(),
                        success=False,
                        error_message=f"Device polling failure rate exceeded threshold: {failure_rate:.2%} > 20%",
                    )
                    await self.audit_logger.log_event_async(reliability_event)

            logger.info(
                f"Polled and stored data for {len(device_data_list)} devices (duration: {polling_duration_ms:.1f}ms)"
            )

        except Exception as e:
            logger.error(f"Error in polling cycle: {e}")

            # Log polling system failures
            if self.audit_logger:
                system_error_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    severity=AuditSeverity.CRITICAL,
                    user_id=None,
                    username=None,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="system",
                    resource_id="device_polling_system",
                    action="Device polling system failure",
                    details={
                        "performance_monitoring": True,
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "polling_duration_ms": (time.time() - polling_start_time)
                        * 1000,
                        "system_component": "device_polling",
                    },
                    timestamp=datetime.now(),
                    success=False,
                    error_message=str(e),
                )
                await self.audit_logger.log_event_async(system_error_event)

    def _get_optimal_interval(self, start_time: Optional[datetime], end_time: Optional[datetime], time_period: Optional[str]) -> str:
        """Auto-select optimal interval based on time range."""
        if time_period:
            # Map time periods to optimal intervals
            period_to_interval = {
                '1h': '1m',
                '6h': '5m',
                '24h': '15m',
                '3d': '1h',
                '7d': '4h',
                '30d': '12h',
                'custom': '1h'  # Default for custom, may be overridden below
            }
            interval = period_to_interval.get(time_period, '1h')
            
            # For custom periods, adjust based on actual time range
            if time_period == 'custom' and start_time and end_time:
                time_diff = end_time - start_time
                if time_diff.days <= 1:
                    interval = '15m'
                elif time_diff.days <= 7:
                    interval = '1h'
                elif time_diff.days <= 30:
                    interval = '4h'
                else:
                    interval = '12h'
            
            return interval
        
        # Fallback logic based on time range
        if start_time and end_time:
            time_diff = end_time - start_time
            if time_diff.total_seconds() <= 3600:  # 1 hour
                return '1m'
            elif time_diff.total_seconds() <= 21600:  # 6 hours
                return '5m'
            elif time_diff.days <= 1:
                return '15m'
            elif time_diff.days <= 7:
                return '1h'
            elif time_diff.days <= 30:
                return '4h'
            else:
                return '12h'
        
        return '1h'  # Default

    def _get_cache_duration(self, time_period: str) -> int:
        """Get cache duration in seconds based on time period."""
        cache_durations = {
            '1h': 30,      # 30 seconds for 1 hour view
            '6h': 60,      # 1 minute for 6 hour view
            '24h': 300,    # 5 minutes for 24 hour view
            '3d': 900,     # 15 minutes for 3 day view
            '7d': 1800,    # 30 minutes for 7 day view
            '30d': 3600,   # 1 hour for 30 day view
            'custom': 300  # 5 minutes for custom range
        }
        return cache_durations.get(time_period, 300)


if __name__ == "__main__":
    app_instance = KasaMonitorApp()

    # Check for SSL configuration
    import asyncio
    import os
    from pathlib import Path

    async def get_ssl_config():
        """Get SSL configuration from database."""
        try:
            # Initialize database connection temporarily
            temp_db = DatabaseManager()
            await temp_db.initialize()

            # Get SSL configuration
            ssl_enabled = await temp_db.get_system_config("ssl.enabled")
            ssl_cert_path = await temp_db.get_system_config("ssl.cert_path")
            ssl_key_path = await temp_db.get_system_config("ssl.key_path")
            ssl_port = await temp_db.get_system_config("ssl.port")

            # Auto-enable SSL if both cert and key paths exist and files are present
            if not ssl_enabled or ssl_enabled.lower() != "true":
                if ssl_cert_path and ssl_key_path:
                    cert_path = Path(ssl_cert_path)
                    key_path = Path(ssl_key_path)

                    # Convert relative paths to absolute paths if needed
                    if not cert_path.is_absolute():
                        cert_path = Path(__file__).parent.parent / cert_path
                    if not key_path.is_absolute():
                        key_path = Path(__file__).parent.parent / key_path

                    if cert_path.exists() and key_path.exists():
                        ssl_enabled = "true"
                        await temp_db.set_system_config("ssl.enabled", "true")
                        logger.info(
                            "SSL auto-enabled - certificate and key files found"
                        )

            await temp_db.close()

            return {
                "enabled": ssl_enabled and ssl_enabled.lower() == "true",
                "cert_path": ssl_cert_path or "",
                "key_path": ssl_key_path or "",
                "port": (
                    int(ssl_port)
                    if ssl_port and ssl_port.isdigit()
                    else int(os.getenv("HTTPS_PORT", "5273"))
                ),
            }
        except Exception as e:
            logger.error(f"Error getting SSL config: {e}")
            return {
                "enabled": False,
                "cert_path": "",
                "key_path": "",
                "port": int(os.getenv("HTTPS_PORT", "5273")),
            }

    # Get SSL configuration
    ssl_config = asyncio.run(get_ssl_config())

    # Check if SSL should be enabled
    if ssl_config["enabled"] and ssl_config["cert_path"] and ssl_config["key_path"]:
        cert_path = Path(ssl_config["cert_path"])
        key_path = Path(ssl_config["key_path"])
        ssl_port = ssl_config.get("port", 5273)

        # Convert relative paths to absolute paths relative to project root
        if not cert_path.is_absolute():
            cert_path = Path(__file__).parent.parent / cert_path
        if not key_path.is_absolute():
            key_path = Path(__file__).parent.parent / key_path

        if cert_path.exists() and key_path.exists():
            # SSL is enabled and certificates exist - run both HTTP and HTTPS servers
            import threading

            import uvicorn.config
            import uvicorn.server

            logger.info(f"Starting HTTPS server on port {ssl_port}")
            logger.info(f"Starting HTTP server on port 5272")
            logger.info(f"SSL Certificate: {cert_path}")
            logger.info(f"SSL Private Key: {key_path}")

            # Configure HTTPS server
            https_config = uvicorn.Config(
                app=app_instance.app,
                host="0.0.0.0",
                port=ssl_port,
                ssl_certfile=str(cert_path),
                ssl_keyfile=str(key_path),
                log_level="info",
            )

            # Configure HTTP server
            http_config = uvicorn.Config(
                app=app_instance.app, host="0.0.0.0", port=5272, log_level="info"
            )

            # Start HTTPS server in a separate thread
            https_server = uvicorn.Server(https_config)
            https_thread = threading.Thread(target=https_server.run, daemon=True)
            https_thread.start()

            # Start HTTP server in main thread
            http_server = uvicorn.Server(http_config)
            http_server.run()
        else:
            logger.warning(
                f"SSL enabled but files not found - cert: {cert_path}, key: {key_path}"
            )
            logger.info("Starting server without SSL on port 5272")
            uvicorn.run(app=app_instance.app, host="0.0.0.0", port=5272)
    else:
        logger.info("Starting server without SSL on port 5272")
        uvicorn.run(app=app_instance.app, host="0.0.0.0", port=5272)
