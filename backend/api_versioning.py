"""API versioning system for Kasa Monitor.

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

import functools
import warnings
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Tuple
from enum import Enum
from dataclasses import dataclass
from fastapi import Request, Response, HTTPException, Header
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class APIVersion(Enum):
    """API version definitions."""

    V1 = "v1"
    V2 = "v2"
    V3 = "v3"
    LATEST = "v3"  # Points to latest stable version
    BETA = "beta"  # Beta features
    DEPRECATED = "deprecated"  # Deprecated version


@dataclass
class VersionInfo:
    """API version information."""

    version: str
    introduced: datetime
    deprecated: Optional[datetime] = None
    sunset: Optional[datetime] = None
    changes: Optional[List[str]] = None
    breaking_changes: Optional[List[str]] = None
    migration_guide: Optional[str] = None

    def is_deprecated(self) -> bool:
        """Check if version is deprecated."""
        return self.deprecated is not None and datetime.now() >= self.deprecated

    def is_sunset(self) -> bool:
        """Check if version is sunset (no longer available)."""
        return self.sunset is not None and datetime.now() >= self.sunset

    def days_until_sunset(self) -> Optional[int]:
        """Get days until sunset."""
        if self.sunset:
            delta = self.sunset - datetime.now()
            return max(0, delta.days)
        return None


class VersionRegistry:
    """Registry for API versions."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize version registry.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.versions = {}
        self.routes = {}
        self.transformers = {}

        self._init_database()
        self._register_versions()

    def _init_database(self):
        """Initialize versioning tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_versions (
                version TEXT PRIMARY KEY,
                introduced TIMESTAMP NOT NULL,
                deprecated TIMESTAMP,
                sunset TIMESTAMP,
                changes TEXT,
                breaking_changes TEXT,
                migration_guide TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                client_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms REAL,
                status_code INTEGER
            )
        """
        )

        conn.commit()
        conn.close()

    def _register_versions(self):
        """Register API versions."""
        # Version 1 - Original API
        self.register_version(
            VersionInfo(
                version=APIVersion.V1.value,
                introduced=datetime(2024, 1, 1),
                deprecated=datetime(2024, 12, 31),
                sunset=datetime(2025, 6, 30),
                changes=[
                    "Initial API release",
                    "Basic device management",
                    "Simple authentication",
                ],
            )
        )

        # Version 2 - Enhanced API
        self.register_version(
            VersionInfo(
                version=APIVersion.V2.value,
                introduced=datetime(2024, 6, 1),
                deprecated=datetime(2025, 6, 30),
                changes=[
                    "Added bulk operations",
                    "Enhanced filtering",
                    "Improved error responses",
                    "WebSocket support",
                ],
                breaking_changes=[
                    "Changed device response format",
                    "Renamed 'device_id' to 'device_ip'",
                ],
                migration_guide="https://docs.kasa-monitor.com/migration/v1-to-v2",
            )
        )

        # Version 3 - Current API
        self.register_version(
            VersionInfo(
                version=APIVersion.V3.value,
                introduced=datetime(2025, 1, 1),
                changes=[
                    "Plugin system support",
                    "Advanced scheduling",
                    "Performance monitoring",
                    "GraphQL endpoint",
                ],
                breaking_changes=[
                    "New authentication flow",
                    "Changed pagination format",
                ],
                migration_guide="https://docs.kasa-monitor.com/migration/v2-to-v3",
            )
        )

    def register_version(self, version_info: VersionInfo):
        """Register an API version.

        Args:
            version_info: Version information
        """
        self.versions[version_info.version] = version_info

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO api_versions
            (version, introduced, deprecated, sunset, changes, breaking_changes, migration_guide)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                version_info.version,
                version_info.introduced,
                version_info.deprecated,
                version_info.sunset,
                str(version_info.changes) if version_info.changes else None,
                (str(version_info.breaking_changes) if version_info.breaking_changes else None),
                version_info.migration_guide,
            ),
        )

        conn.commit()
        conn.close()

    def get_version(self, version: str) -> Optional[VersionInfo]:
        """Get version information.

        Args:
            version: Version string

        Returns:
            Version information
        """
        # Handle special versions
        if version == "latest":
            version = APIVersion.LATEST.value

        return self.versions.get(version)

    def is_version_available(self, version: str) -> bool:
        """Check if version is available.

        Args:
            version: Version string

        Returns:
            True if version is available
        """
        version_info = self.get_version(version)
        return version_info is not None and not version_info.is_sunset()

    def record_usage(
        self,
        version: str,
        endpoint: str,
        method: str,
        client_id: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        status_code: Optional[int] = None,
    ):
        """Record API usage.

        Args:
            version: API version
            endpoint: Endpoint path
            method: HTTP method
            client_id: Client identifier
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO api_usage (version, endpoint, method, client_id, response_time_ms, status_code)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (version, endpoint, method, client_id, response_time_ms, status_code),
        )

        conn.commit()
        conn.close()


class VersionedRoute(APIRoute):
    """Versioned API route."""

    def __init__(
        self,
        path: str,
        endpoint: Callable,
        *args,
        supported_versions: List[str] = None,
        **kwargs,
    ):
        """Initialize versioned route.

        Args:
            path: Route path
            endpoint: Route endpoint
            supported_versions: List of supported versions
        """
        self.supported_versions = supported_versions or [v.value for v in APIVersion]
        super().__init__(path, endpoint, *args, **kwargs)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware for API versioning."""

    def __init__(self, app, registry: VersionRegistry):
        """Initialize middleware.

        Args:
            app: FastAPI application
            registry: Version registry
        """
        super().__init__(app)
        self.registry = registry

    async def dispatch(self, request: Request, call_next):
        """Process request with versioning.

        Args:
            request: HTTP request
            call_next: Next middleware

        Returns:
            HTTP response
        """
        # Extract version from request
        version = self._extract_version(request)

        # Check if version is available
        if not self.registry.is_version_available(version):
            version_info = self.registry.get_version(version)

            if version_info and version_info.is_sunset():
                return JSONResponse(
                    status_code=410,
                    content={
                        "error": "API version no longer available",
                        "version": version,
                        "sunset_date": version_info.sunset.isoformat(),
                        "migration_guide": version_info.migration_guide,
                    },
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid API version",
                        "version": version,
                        "available_versions": list(self.registry.versions.keys()),
                    },
                )

        # Add version to request state
        request.state.api_version = version

        # Record start time
        start_time = datetime.now()

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Record usage
        self.registry.record_usage(
            version=version,
            endpoint=str(request.url.path),
            method=request.method,
            client_id=request.headers.get("X-Client-ID"),
            response_time_ms=response_time_ms,
            status_code=response.status_code,
        )

        # Add version headers
        response.headers["X-API-Version"] = version

        # Add deprecation warnings
        version_info = self.registry.get_version(version)
        if version_info and version_info.is_deprecated():
            response.headers["X-API-Deprecated"] = "true"
            response.headers["X-API-Sunset"] = version_info.sunset.isoformat()

            if version_info.days_until_sunset():
                response.headers["X-API-Sunset-Days"] = str(version_info.days_until_sunset())

            if version_info.migration_guide:
                response.headers["X-API-Migration-Guide"] = version_info.migration_guide

        return response

    def _extract_version(self, request: Request) -> str:
        """Extract API version from request.

        Args:
            request: HTTP request

        Returns:
            API version
        """
        # Check URL path (e.g., /api/v2/devices)
        path_parts = request.url.path.split("/")
        for part in path_parts:
            if part in self.registry.versions:
                return part

        # Check Accept header (e.g., Accept: application/vnd.api+json;version=2)
        accept_header = request.headers.get("Accept", "")
        if "version=" in accept_header:
            version = accept_header.split("version=")[1].split(";")[0].strip()
            if version:
                return f"v{version}" if not version.startswith("v") else version

        # Check custom header (e.g., X-API-Version: v2)
        version_header = request.headers.get("X-API-Version")
        if version_header:
            return version_header

        # Check query parameter (e.g., ?api_version=v2)
        version_param = request.query_params.get("api_version")
        if version_param:
            return version_param

        # Default to latest version
        return APIVersion.LATEST.value


class ResponseTransformer:
    """Transform responses between API versions."""

    def __init__(self):
        """Initialize transformer."""
        self.transformers = {}

    def register(self, from_version: str, to_version: str, transformer: Callable[[Dict], Dict]):
        """Register a response transformer.

        Args:
            from_version: Source version
            to_version: Target version
            transformer: Transformation function
        """
        key = (from_version, to_version)
        self.transformers[key] = transformer

    def transform(self, data: Dict, from_version: str, to_version: str) -> Dict:
        """Transform data between versions.

        Args:
            data: Data to transform
            from_version: Source version
            to_version: Target version

        Returns:
            Transformed data
        """
        key = (from_version, to_version)

        if key in self.transformers:
            return self.transformers[key](data)

        # No transformation needed
        return data


# Decorators for versioning


def api_version(*versions: str):
    """Decorator to specify supported API versions.

    Args:
        versions: Supported versions
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get request version
            api_version = getattr(request.state, "api_version", APIVersion.LATEST.value)

            # Check if version is supported
            if api_version not in versions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Endpoint not available in API version {api_version}",
                )

            # Execute function
            return await func(request, *args, **kwargs)

        # Store supported versions
        wrapper.supported_versions = versions

        return wrapper

    return decorator


def deprecated(sunset_date: datetime, migration_guide: Optional[str] = None):
    """Decorator to mark endpoint as deprecated.

    Args:
        sunset_date: Date when endpoint will be removed
        migration_guide: URL to migration guide
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Issue deprecation warning
            warnings.warn(
                f"Endpoint {func.__name__} is deprecated and will be removed on {sunset_date}",
                DeprecationWarning,
                stacklevel=2,
            )

            # Execute function
            result = await func(*args, **kwargs)

            # Add deprecation headers if result is Response
            if isinstance(result, Response):
                result.headers["X-Deprecated"] = "true"
                result.headers["X-Sunset-Date"] = sunset_date.isoformat()

                if migration_guide:
                    result.headers["X-Migration-Guide"] = migration_guide

            return result

        return wrapper

    return decorator


def transform_response(from_version: str, to_version: str):
    """Decorator to transform response between versions.

    Args:
        from_version: Source version
        to_version: Target version
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs)

            # Transform result
            transformer = ResponseTransformer()

            if isinstance(result, dict):
                result = transformer.transform(result, from_version, to_version)

            return result

        return wrapper

    return decorator


class APIVersionManager:
    """Main API version manager."""

    def __init__(self, app, db_path: str = "kasa_monitor.db"):
        """Initialize version manager.

        Args:
            app: FastAPI application
            db_path: Path to database
        """
        self.app = app
        self.registry = VersionRegistry(db_path)
        self.transformer = ResponseTransformer()

        # Add middleware
        app.add_middleware(APIVersionMiddleware, registry=self.registry)

        # Register default transformers
        self._register_default_transformers()

    def _register_default_transformers(self):
        """Register default response transformers."""

        # V1 to V2 transformer
        def v1_to_v2(data: Dict) -> Dict:
            # Transform device_id to device_ip
            if "device_id" in data:
                data["device_ip"] = data.pop("device_id")

            # Add new fields with defaults
            if "devices" in data:
                for device in data["devices"]:
                    if "device_id" in device:
                        device["device_ip"] = device.pop("device_id")

            return data

        self.transformer.register("v1", "v2", v1_to_v2)

        # V2 to V3 transformer
        def v2_to_v3(data: Dict) -> Dict:
            # Update pagination format
            if "page" in data and "per_page" in data:
                data["pagination"] = {
                    "page": data.pop("page"),
                    "per_page": data.pop("per_page"),
                    "total": data.get("total", 0),
                }

            return data

        self.transformer.register("v2", "v3", v2_to_v3)

    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get API usage statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Usage statistics
        """
        conn = sqlite3.connect(self.registry.db_path)
        cursor = conn.cursor()

        # Get usage by version
        cursor.execute(
            """
            SELECT version, COUNT(*) as count,
                   AVG(response_time_ms) as avg_response_time
            FROM api_usage
            WHERE timestamp > datetime('now', '-{} days')
            GROUP BY version
        """.format(
                days
            )
        )

        version_stats = {}
        for row in cursor.fetchall():
            version_stats[row[0]] = {"requests": row[1], "avg_response_time_ms": row[2]}

        # Get deprecated version usage
        deprecated_usage = {}
        for version, info in self.registry.versions.items():
            if info.is_deprecated() and version in version_stats:
                deprecated_usage[version] = {
                    "requests": version_stats[version]["requests"],
                    "days_until_sunset": info.days_until_sunset(),
                }

        conn.close()

        return {
            "versions": version_stats,
            "deprecated_usage": deprecated_usage,
            "available_versions": list(self.registry.versions.keys()),
        }
