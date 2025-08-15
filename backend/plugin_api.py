"""Plugin API for management, configuration, and monitoring.

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

import sqlite3
import json
import aiohttp
import asyncio
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import shutil

from plugin_system import (
    PluginLoader,
    PluginManifest,
    PluginState,
    PluginType,
    PluginPriority,
)
from hook_system import HookManager, HookType, HookPriority


class PluginConfigUpdate(BaseModel):
    """Plugin configuration update model."""

    config: Dict[str, Any]


class PluginPermissionUpdate(BaseModel):
    """Plugin permission update model."""

    permission: str
    granted: bool
    granted_by: Optional[str] = "system"


class PluginInstallRequest(BaseModel):
    """Plugin installation request."""

    source: str  # URL or file path
    install_dependencies: bool = True
    enable_after_install: bool = False


class PluginSearchQuery(BaseModel):
    """Plugin marketplace search query."""

    query: Optional[str] = None
    plugin_type: Optional[str] = None
    min_rating: Optional[float] = None
    max_results: int = 50


class PluginMetrics(BaseModel):
    """Plugin metrics model."""

    cpu_usage: float
    memory_usage: float
    execution_count: int
    error_count: int
    average_execution_time: float


class PluginAPIRouter:
    """Plugin API router for FastAPI."""

    def __init__(
        self,
        app: FastAPI,
        plugin_loader: PluginLoader,
        hook_manager: HookManager,
        db_path: str = "kasa_monitor.db",
    ):
        """Initialize plugin API router.

        Args:
            app: FastAPI application
            plugin_loader: Plugin loader instance
            hook_manager: Hook manager instance
            db_path: Path to database
        """
        self.app = app
        self.plugin_loader = plugin_loader
        self.hook_manager = hook_manager
        self.db_path = db_path
        self.marketplace_url = "https://api.kasamonitor.com/plugins"  # Placeholder

        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/api/plugins")
        async def list_plugins(
            plugin_type: Optional[str] = None, state: Optional[str] = None
        ):
            """List installed plugins."""
            type_filter = PluginType(plugin_type) if plugin_type else None
            state_filter = PluginState(state) if state else None

            plugins = self.plugin_loader.list_plugins(type_filter, state_filter)

            # Add additional info for each plugin
            for plugin in plugins:
                plugin["metrics"] = await self._get_plugin_metrics(plugin["id"])
                plugin["has_updates"] = await self._check_for_updates(plugin["id"])

            return plugins

        @self.app.get("/api/plugins/{plugin_id}")
        async def get_plugin(plugin_id: str):
            """Get plugin details."""
            info = self.plugin_loader.get_plugin_info(plugin_id)

            if not info:
                raise HTTPException(status_code=404, detail="Plugin not found")

            # Add runtime information
            if plugin_id in self.plugin_loader.plugins:
                plugin = self.plugin_loader.plugins[plugin_id]
                info["runtime"] = plugin.get_info()

            # Add metrics
            info["metrics"] = await self._get_plugin_metrics(plugin_id)

            # Add hook information
            info["hooks"] = self.hook_manager.registry.list_hooks(plugin_id)

            # Add execution statistics
            info["statistics"] = self.hook_manager.get_statistics(plugin_id)

            return info

        @self.app.post("/api/plugins/{plugin_id}/enable")
        async def enable_plugin(plugin_id: str, background_tasks: BackgroundTasks):
            """Enable a plugin."""
            background_tasks.add_task(self._enable_plugin_task, plugin_id)

            return {"message": f"Enabling plugin {plugin_id}", "status": "pending"}

        @self.app.post("/api/plugins/{plugin_id}/disable")
        async def disable_plugin(plugin_id: str):
            """Disable a plugin."""
            success = await self.plugin_loader.disable_plugin(plugin_id)

            if not success:
                raise HTTPException(status_code=500, detail="Failed to disable plugin")

            return {"message": f"Plugin {plugin_id} disabled"}

        @self.app.post("/api/plugins/{plugin_id}/reload")
        async def reload_plugin(plugin_id: str):
            """Reload a plugin."""
            # Unload and reload
            await self.plugin_loader.unload_plugin(plugin_id)

            if not self.plugin_loader.load_plugin(plugin_id):
                raise HTTPException(status_code=500, detail="Failed to reload plugin")

            # Re-initialize
            await self.plugin_loader.initialize_plugin(plugin_id)

            return {"message": f"Plugin {plugin_id} reloaded"}

        @self.app.put("/api/plugins/{plugin_id}/config")
        async def update_plugin_config(plugin_id: str, update: PluginConfigUpdate):
            """Update plugin configuration."""
            if plugin_id not in self.plugin_loader.plugins:
                raise HTTPException(status_code=404, detail="Plugin not found")

            # Get plugin API
            plugin = self.plugin_loader.plugins[plugin_id]

            # Save config
            if plugin.api:
                success = plugin.api.save_config(update.config)
                if success:
                    # Reload plugin to apply config
                    await reload_plugin(plugin_id)
                    return {"message": "Configuration updated"}

            raise HTTPException(
                status_code=500, detail="Failed to update configuration"
            )

        @self.app.get("/api/plugins/{plugin_id}/config")
        async def get_plugin_config(plugin_id: str):
            """Get plugin configuration."""
            info = self.plugin_loader.get_plugin_info(plugin_id)

            if not info:
                raise HTTPException(status_code=404, detail="Plugin not found")

            return info.get("config", {})

        @self.app.post("/api/plugins/{plugin_id}/permissions")
        async def update_plugin_permission(
            plugin_id: str, update: PluginPermissionUpdate
        ):
            """Update plugin permission."""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE plugin_permissions
                SET granted = ?, granted_by = ?, granted_at = CURRENT_TIMESTAMP
                WHERE plugin_id = ? AND permission = ?
            """,
                (update.granted, update.granted_by, plugin_id, update.permission),
            )

            if cursor.rowcount == 0:
                # Insert if not exists
                cursor.execute(
                    """
                    INSERT INTO plugin_permissions (plugin_id, permission, granted, granted_by, granted_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (plugin_id, update.permission, update.granted, update.granted_by),
                )

            conn.commit()
            conn.close()

            return {"message": "Permission updated"}

        @self.app.get("/api/plugins/{plugin_id}/permissions")
        async def get_plugin_permissions(plugin_id: str):
            """Get plugin permissions."""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT permission, granted, granted_by, granted_at
                FROM plugin_permissions
                WHERE plugin_id = ?
            """,
                (plugin_id,),
            )

            permissions = []
            for row in cursor.fetchall():
                permissions.append(
                    {
                        "permission": row[0],
                        "granted": bool(row[1]),
                        "granted_by": row[2],
                        "granted_at": row[3],
                    }
                )

            conn.close()
            return permissions

        @self.app.get("/api/plugins/{plugin_id}/logs")
        async def get_plugin_logs(
            plugin_id: str, limit: int = 100, level: Optional[str] = None
        ):
            """Get plugin logs."""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = (
                "SELECT level, message, timestamp FROM plugin_logs WHERE plugin_id = ?"
            )
            params = [plugin_id]

            if level:
                query += " AND level = ?"
                params.append(level)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            logs = []
            for row in cursor.fetchall():
                logs.append({"level": row[0], "message": row[1], "timestamp": row[2]})

            conn.close()
            return logs

        @self.app.get("/api/plugins/{plugin_id}/metrics")
        async def get_plugin_metrics(plugin_id: str, hours: int = 24):
            """Get plugin metrics."""
            metrics = await self._get_plugin_metrics(plugin_id, hours)
            return metrics

        @self.app.post("/api/plugins/install")
        async def install_plugin(
            request: PluginInstallRequest, background_tasks: BackgroundTasks
        ):
            """Install a plugin."""
            background_tasks.add_task(
                self._install_plugin_task,
                request.source,
                request.install_dependencies,
                request.enable_after_install,
            )

            return {"message": "Plugin installation started", "status": "pending"}

        @self.app.post("/api/plugins/install/upload")
        async def upload_and_install_plugin(
            file: UploadFile = File(...),
            enable_after_install: bool = False,
            background_tasks: BackgroundTasks = None,
        ):
            """Upload and install a plugin."""
            # Save uploaded file
            temp_dir = tempfile.mkdtemp()
            temp_file = Path(temp_dir) / file.filename

            with open(temp_file, "wb") as f:
                content = await file.read()
                f.write(content)

            # Install plugin
            background_tasks.add_task(
                self._install_plugin_task, str(temp_file), True, enable_after_install
            )

            return {
                "message": f"Plugin {file.filename} uploaded and installation started"
            }

        @self.app.delete("/api/plugins/{plugin_id}")
        async def uninstall_plugin(plugin_id: str):
            """Uninstall a plugin."""
            success = self.plugin_loader.uninstall_plugin(plugin_id)

            if not success:
                raise HTTPException(
                    status_code=500, detail="Failed to uninstall plugin"
                )

            return {"message": f"Plugin {plugin_id} uninstalled"}

        @self.app.get("/api/plugins/marketplace/search")
        async def search_marketplace(query: PluginSearchQuery):
            """Search plugin marketplace."""
            results = await self._search_marketplace(query)
            return results

        @self.app.get("/api/plugins/marketplace/{plugin_id}")
        async def get_marketplace_plugin(plugin_id: str):
            """Get plugin details from marketplace."""
            details = await self._get_marketplace_plugin(plugin_id)

            if not details:
                raise HTTPException(
                    status_code=404, detail="Plugin not found in marketplace"
                )

            return details

        @self.app.post("/api/plugins/marketplace/{plugin_id}/install")
        async def install_from_marketplace(
            plugin_id: str, background_tasks: BackgroundTasks
        ):
            """Install plugin from marketplace."""
            # Get plugin URL from marketplace
            details = await self._get_marketplace_plugin(plugin_id)

            if not details:
                raise HTTPException(
                    status_code=404, detail="Plugin not found in marketplace"
                )

            background_tasks.add_task(
                self._install_plugin_task, details["download_url"], True, False
            )

            return {"message": f"Installing {details['name']} from marketplace"}

        @self.app.get("/api/plugins/{plugin_id}/dependencies")
        async def get_plugin_dependencies(plugin_id: str):
            """Get plugin dependencies."""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT d.dependency_id, d.version_constraint, d.optional,
                       p.name, p.version, p.state
                FROM plugin_dependencies d
                LEFT JOIN plugin_registry p ON d.dependency_id = p.plugin_id
                WHERE d.plugin_id = ?
            """,
                (plugin_id,),
            )

            dependencies = []
            for row in cursor.fetchall():
                dependencies.append(
                    {
                        "id": row[0],
                        "version_constraint": row[1],
                        "optional": bool(row[2]),
                        "installed": row[3] is not None,
                        "name": row[3],
                        "version": row[4],
                        "state": row[5],
                    }
                )

            conn.close()
            return dependencies

        @self.app.get("/api/plugins/updates")
        async def check_for_updates():
            """Check for plugin updates."""
            updates = []

            for plugin_id in self.plugin_loader.manifests:
                update_info = await self._check_for_updates(plugin_id)
                if update_info:
                    updates.append(update_info)

            return updates

        @self.app.post("/api/plugins/{plugin_id}/update")
        async def update_plugin(plugin_id: str, background_tasks: BackgroundTasks):
            """Update a plugin."""
            update_info = await self._check_for_updates(plugin_id)

            if not update_info:
                return {"message": "Plugin is up to date"}

            background_tasks.add_task(
                self._update_plugin_task, plugin_id, update_info["latest_version"]
            )

            return {
                "message": f"Updating {plugin_id} to version {update_info['latest_version']}"
            }

    async def _enable_plugin_task(self, plugin_id: str):
        """Background task to enable a plugin.

        Args:
            plugin_id: Plugin ID
        """
        try:
            success = await self.plugin_loader.enable_plugin(plugin_id)
            if success:
                # Emit event
                await self.hook_manager.emit(
                    "plugin.enabled",
                    {"plugin_id": plugin_id, "timestamp": datetime.now().isoformat()},
                )
        except Exception as e:
            # Log error
            await self.hook_manager.emit(
                "plugin.error",
                {
                    "plugin_id": plugin_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _install_plugin_task(
        self, source: str, install_dependencies: bool, enable_after_install: bool
    ):
        """Background task to install a plugin.

        Args:
            source: Plugin source (URL or file path)
            install_dependencies: Whether to install dependencies
            enable_after_install: Whether to enable after installation
        """
        try:
            # Download if URL
            if source.startswith("http"):
                temp_file = await self._download_plugin(source)
                plugin_id = self.plugin_loader.install_plugin(temp_file)
                Path(temp_file).unlink()  # Clean up
            else:
                plugin_id = self.plugin_loader.install_plugin(source)

            if plugin_id:
                # Load plugin
                self.plugin_loader.load_plugin(plugin_id)

                # Enable if requested
                if enable_after_install:
                    await self.plugin_loader.enable_plugin(plugin_id)

                # Emit event
                await self.hook_manager.emit(
                    "plugin.installed",
                    {"plugin_id": plugin_id, "timestamp": datetime.now().isoformat()},
                )

        except Exception as e:
            # Emit error event
            await self.hook_manager.emit(
                "plugin.install_error",
                {
                    "source": source,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _update_plugin_task(self, plugin_id: str, new_version: str):
        """Background task to update a plugin.

        Args:
            plugin_id: Plugin ID
            new_version: New version to install
        """
        try:
            # Disable plugin first
            await self.plugin_loader.disable_plugin(plugin_id)

            # Get update URL from marketplace
            update_url = await self._get_update_url(plugin_id, new_version)

            if update_url:
                # Download and install new version
                temp_file = await self._download_plugin(update_url)

                # Backup current version
                self._backup_plugin(plugin_id)

                # Uninstall current version
                self.plugin_loader.uninstall_plugin(plugin_id)

                # Install new version
                new_plugin_id = self.plugin_loader.install_plugin(temp_file)
                Path(temp_file).unlink()

                if new_plugin_id:
                    # Load and enable
                    self.plugin_loader.load_plugin(new_plugin_id)
                    await self.plugin_loader.enable_plugin(new_plugin_id)

                    # Emit event
                    await self.hook_manager.emit(
                        "plugin.updated",
                        {
                            "plugin_id": plugin_id,
                            "new_version": new_version,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

        except Exception as e:
            # Restore backup if available
            self._restore_plugin(plugin_id)

            # Emit error event
            await self.hook_manager.emit(
                "plugin.update_error",
                {
                    "plugin_id": plugin_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _get_plugin_metrics(self, plugin_id: str, hours: int = 24) -> Dict:
        """Get plugin metrics.

        Args:
            plugin_id: Plugin ID
            hours: Number of hours to analyze

        Returns:
            Plugin metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_time = datetime.now() - timedelta(hours=hours)

        # Get metric data
        cursor.execute(
            """
            SELECT metric_type, AVG(value), MAX(value), MIN(value), COUNT(*)
            FROM plugin_metrics
            WHERE plugin_id = ? AND timestamp > ?
            GROUP BY metric_type
        """,
            (plugin_id, start_time),
        )

        metrics = {}
        for row in cursor.fetchall():
            metrics[row[0]] = {
                "average": row[1],
                "max": row[2],
                "min": row[3],
                "count": row[4],
            }

        # Get execution statistics
        cursor.execute(
            """
            SELECT COUNT(*), AVG(execution_time), SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END)
            FROM hook_executions
            WHERE plugin_id = ? AND triggered_at > ?
        """,
            (plugin_id, start_time),
        )

        row = cursor.fetchone()
        if row:
            metrics["executions"] = {
                "total": row[0] or 0,
                "average_time": row[1] or 0,
                "errors": row[2] or 0,
            }

        conn.close()
        return metrics

    async def _check_for_updates(self, plugin_id: str) -> Optional[Dict]:
        """Check if plugin has updates available.

        Args:
            plugin_id: Plugin ID

        Returns:
            Update information if available
        """
        if plugin_id not in self.plugin_loader.manifests:
            return None

        manifest = self.plugin_loader.manifests[plugin_id]

        # Check marketplace for newer version
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.marketplace_url}/{plugin_id}/version"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        latest_version = data.get("version")

                        if latest_version and latest_version > manifest.version:
                            return {
                                "plugin_id": plugin_id,
                                "current_version": manifest.version,
                                "latest_version": latest_version,
                                "changelog": data.get("changelog", ""),
                            }
        except:
            pass

        return None

    async def _search_marketplace(self, query: PluginSearchQuery) -> List[Dict]:
        """Search plugin marketplace.

        Args:
            query: Search query

        Returns:
            Search results
        """
        # TODO: Implement actual marketplace API call
        # This is a placeholder implementation
        return []

    async def _get_marketplace_plugin(self, plugin_id: str) -> Optional[Dict]:
        """Get plugin details from marketplace.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin details
        """
        # TODO: Implement actual marketplace API call
        # This is a placeholder implementation
        return None

    async def _get_update_url(self, plugin_id: str, version: str) -> Optional[str]:
        """Get plugin update URL.

        Args:
            plugin_id: Plugin ID
            version: Version to download

        Returns:
            Download URL
        """
        # TODO: Implement actual marketplace API call
        # This is a placeholder implementation
        return None

    async def _download_plugin(self, url: str) -> str:
        """Download plugin from URL.

        Args:
            url: Plugin URL

        Returns:
            Path to downloaded file
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()

                with open(temp_file.name, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

        return temp_file.name

    def _backup_plugin(self, plugin_id: str):
        """Backup plugin before update.

        Args:
            plugin_id: Plugin ID
        """
        info = self.plugin_loader.get_plugin_info(plugin_id)
        if info:
            install_path = Path(info.get("install_path", ""))
            if install_path.exists():
                backup_path = install_path.parent / f"{plugin_id}_backup"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(install_path, backup_path)

    def _restore_plugin(self, plugin_id: str):
        """Restore plugin from backup.

        Args:
            plugin_id: Plugin ID
        """
        backup_path = Path(self.plugin_loader.plugin_dir) / f"{plugin_id}_backup"
        if backup_path.exists():
            install_path = self.plugin_loader.plugin_dir / plugin_id
            if install_path.exists():
                shutil.rmtree(install_path)
            shutil.move(backup_path, install_path)

            # Reload plugin
            self.plugin_loader.discover_plugins()
            self.plugin_loader.load_plugin(plugin_id)
