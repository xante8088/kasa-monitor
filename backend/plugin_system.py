"""Plugin system with discovery, loading, and lifecycle management.

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

import os
import sys
import json
import importlib
import importlib.util
import inspect
import asyncio
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Type
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import sqlite3
import tempfile
import shutil
import zipfile
import hashlib
import semver


class PluginState(Enum):
    """Plugin lifecycle states."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UNLOADED = "unloaded"


class PluginType(Enum):
    """Plugin types."""

    DEVICE = "device"
    INTEGRATION = "integration"
    UI = "ui"
    AUTOMATION = "automation"
    ANALYTICS = "analytics"
    SECURITY = "security"
    UTILITY = "utility"


class PluginPriority(Enum):
    """Plugin loading priority."""

    CRITICAL = 0
    HIGH = 10
    NORMAL = 50
    LOW = 100


@dataclass
class PluginManifest:
    """Plugin manifest definition."""

    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    main_class: str
    dependencies: Optional[List[str]] = None
    python_dependencies: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    config_schema: Optional[Dict] = None
    hooks: Optional[List[str]] = None
    api_version: str = "1.0"
    min_app_version: Optional[str] = None
    max_app_version: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None
    icon: Optional[str] = None
    priority: PluginPriority = PluginPriority.NORMAL
    sandbox: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["plugin_type"] = self.plugin_type.value
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "PluginManifest":
        """Create from dictionary."""
        data["plugin_type"] = PluginType(data["plugin_type"])
        data["priority"] = PluginPriority(data.get("priority", 50))
        return cls(**data)

    def is_compatible(self, app_version: str) -> bool:
        """Check if plugin is compatible with app version."""
        if self.min_app_version:
            try:
                if semver.compare(app_version, self.min_app_version) < 0:
                    return False
            except ValueError:
                if app_version < self.min_app_version:
                    return False

        if self.max_app_version:
            try:
                if semver.compare(app_version, self.max_app_version) > 0:
                    return False
            except ValueError:
                if app_version > self.max_app_version:
                    return False

        return True


class PluginBase(ABC):
    """Base class for all plugins."""

    def __init__(self, plugin_id: str, config: Optional[Dict] = None):
        """Initialize plugin.

        Args:
            plugin_id: Plugin identifier
            config: Plugin configuration
        """
        self.plugin_id = plugin_id
        self.config = config or {}
        self.state = PluginState.LOADED
        self.logger = None
        self.api = None

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def start(self) -> bool:
        """Start the plugin.

        Returns:
            True if started successfully
        """
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the plugin.

        Returns:
            True if stopped successfully
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """Cleanup plugin resources."""
        pass

    def get_info(self) -> Dict:
        """Get plugin information.

        Returns:
            Plugin information
        """
        return {"id": self.plugin_id, "state": self.state.value, "config": self.config}

    def set_api(self, api: "PluginAPI"):
        """Set plugin API access.

        Args:
            api: Plugin API instance
        """
        self.api = api

    def set_logger(self, logger):
        """Set plugin logger.

        Args:
            logger: Logger instance
        """
        self.logger = logger


class PluginSandbox:
    """Plugin sandbox for isolation."""

    def __init__(self, plugin_id: str, restrictions: Optional[Dict] = None):
        """Initialize sandbox.

        Args:
            plugin_id: Plugin identifier
            restrictions: Sandbox restrictions
        """
        self.plugin_id = plugin_id
        self.restrictions = restrictions or {}
        self.allowed_modules = set(restrictions.get("allowed_modules", []))
        self.blocked_modules = set(
            restrictions.get(
                "blocked_modules", ["os", "sys", "subprocess", "__builtins__"]
            )
        )
        self.max_memory_mb = restrictions.get("max_memory_mb", 100)
        self.max_cpu_percent = restrictions.get("max_cpu_percent", 25)
        self.network_access = restrictions.get("network_access", False)
        self.filesystem_access = restrictions.get("filesystem_access", [])

    def create_restricted_globals(self) -> Dict:
        """Create restricted global namespace.

        Returns:
            Restricted globals dictionary
        """
        restricted_globals = {
            "__name__": f"plugin_{self.plugin_id}",
            "__doc__": None,
            "__package__": None,
            "__loader__": None,
            "__spec__": None,
            "__file__": None,
            "__cached__": None,
            "__builtins__": self._create_restricted_builtins(),
        }

        return restricted_globals

    def _create_restricted_builtins(self) -> Dict:
        """Create restricted builtins.

        Returns:
            Restricted builtins dictionary
        """
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "bytes": bytes,
            "chr": chr,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "format": format,
            "int": int,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "ord": ord,
            "pow": pow,
            "range": range,
            "reversed": reversed,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
            "True": True,
            "False": False,
            "None": None,
        }

        return safe_builtins

    def check_import(self, module_name: str) -> bool:
        """Check if module import is allowed.

        Args:
            module_name: Module to import

        Returns:
            True if import is allowed
        """
        if module_name in self.blocked_modules:
            return False

        if self.allowed_modules and module_name not in self.allowed_modules:
            return False

        return True

    def check_filesystem_access(self, path: str) -> bool:
        """Check if filesystem access is allowed.

        Args:
            path: Path to access

        Returns:
            True if access is allowed
        """
        if not self.filesystem_access:
            return False

        path = Path(path).resolve()
        for allowed_path in self.filesystem_access:
            allowed = Path(allowed_path).resolve()
            if path.is_relative_to(allowed):
                return True

        return False


class PluginLoader:
    """Plugin loader and manager."""

    def __init__(
        self,
        plugin_dir: str = "./plugins",
        db_path: str = "kasa_monitor.db",
        app_version: str = "1.0.0",
    ):
        """Initialize plugin loader.

        Args:
            plugin_dir: Directory containing plugins
            db_path: Path to database
            app_version: Application version
        """
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.app_version = app_version

        self.plugins = {}
        self.manifests = {}
        self.sandboxes = {}
        self.load_order = []

        self._init_database()

    def _init_database(self):
        """Initialize plugin tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Plugin registry table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_registry (
                plugin_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                manifest TEXT NOT NULL,
                state TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                install_path TEXT,
                config TEXT,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_loaded TIMESTAMP,
                error_message TEXT
            )
        """
        )

        # Plugin dependencies table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_dependencies (
                plugin_id TEXT NOT NULL,
                dependency_id TEXT NOT NULL,
                version_constraint TEXT,
                optional BOOLEAN DEFAULT 0,
                PRIMARY KEY (plugin_id, dependency_id),
                FOREIGN KEY (plugin_id) REFERENCES plugin_registry(plugin_id),
                FOREIGN KEY (dependency_id) REFERENCES plugin_registry(plugin_id)
            )
        """
        )

        # Plugin permissions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_permissions (
                plugin_id TEXT NOT NULL,
                permission TEXT NOT NULL,
                granted BOOLEAN DEFAULT 0,
                granted_by TEXT,
                granted_at TIMESTAMP,
                PRIMARY KEY (plugin_id, permission),
                FOREIGN KEY (plugin_id) REFERENCES plugin_registry(plugin_id)
            )
        """
        )

        # Plugin metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugin_registry(plugin_id)
            )
        """
        )

        # Plugin logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugin_registry(plugin_id)
            )
        """
        )

        conn.commit()
        conn.close()

    def discover_plugins(self) -> List[str]:
        """Discover available plugins.

        Returns:
            List of discovered plugin IDs
        """
        discovered = []

        # Scan plugin directory
        for item in self.plugin_dir.iterdir():
            if item.is_dir():
                manifest_path = item / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            manifest_data = json.load(f)

                        manifest = PluginManifest.from_dict(manifest_data)

                        # Check compatibility
                        if manifest.is_compatible(self.app_version):
                            self.manifests[manifest.id] = manifest
                            discovered.append(manifest.id)
                            self._register_plugin(manifest, str(item))
                    except Exception as e:
                        print(f"Error loading manifest from {item}: {e}")

        # Check for packaged plugins (.zip)
        for item in self.plugin_dir.glob("*.zip"):
            try:
                with zipfile.ZipFile(item) as zf:
                    if "manifest.json" in zf.namelist():
                        manifest_data = json.loads(zf.read("manifest.json"))
                        manifest = PluginManifest.from_dict(manifest_data)

                        if manifest.is_compatible(self.app_version):
                            # Extract plugin
                            extract_dir = self.plugin_dir / manifest.id
                            zf.extractall(extract_dir)

                            self.manifests[manifest.id] = manifest
                            discovered.append(manifest.id)
                            self._register_plugin(manifest, str(extract_dir))
            except Exception as e:
                print(f"Error loading plugin from {item}: {e}")

        return discovered

    def load_plugin(self, plugin_id: str) -> bool:
        """Load a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if loaded successfully
        """
        if plugin_id not in self.manifests:
            return False

        manifest = self.manifests[plugin_id]

        # Check dependencies
        if not self._check_dependencies(manifest):
            return False

        # Get plugin path
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT install_path, config FROM plugin_registry WHERE plugin_id = ?",
            (plugin_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False

        install_path, config_str = row
        config = json.loads(config_str) if config_str else {}

        try:
            # Install Python dependencies
            if manifest.python_dependencies:
                self._install_dependencies(manifest.python_dependencies)

            # Create sandbox if needed
            if manifest.sandbox:
                sandbox = PluginSandbox(plugin_id)
                self.sandboxes[plugin_id] = sandbox

            # Load plugin module
            plugin_path = Path(install_path)
            main_file = plugin_path / f"{manifest.main_class.split('.')[0]}.py"

            if not main_file.exists():
                raise FileNotFoundError(f"Plugin main file not found: {main_file}")

            # Load module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_id}", main_file
            )
            module = importlib.util.module_from_spec(spec)

            # Add to sys.modules
            sys.modules[f"plugin_{plugin_id}"] = module

            # Execute module
            spec.loader.exec_module(module)

            # Get plugin class
            class_name = manifest.main_class.split(".")[-1]
            plugin_class = getattr(module, class_name)

            # Verify it's a PluginBase subclass
            if not issubclass(plugin_class, PluginBase):
                raise TypeError(f"Plugin class must inherit from PluginBase")

            # Instantiate plugin
            plugin_instance = plugin_class(plugin_id, config)

            # Set API and logger
            plugin_instance.set_api(PluginAPI(self, plugin_id))

            # Store plugin
            self.plugins[plugin_id] = plugin_instance

            # Update state
            self._update_plugin_state(plugin_id, PluginState.LOADED)

            return True

        except Exception as e:
            self._update_plugin_state(plugin_id, PluginState.ERROR, str(e))
            return False

    async def initialize_plugin(self, plugin_id: str) -> bool:
        """Initialize a loaded plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if initialized successfully
        """
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        try:
            success = await plugin.initialize()
            if success:
                self._update_plugin_state(plugin_id, PluginState.INITIALIZED)
                plugin.state = PluginState.INITIALIZED
            return success
        except Exception as e:
            self._update_plugin_state(plugin_id, PluginState.ERROR, str(e))
            return False

    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if enabled successfully
        """
        if plugin_id not in self.plugins:
            # Try to load first
            if not self.load_plugin(plugin_id):
                return False

        plugin = self.plugins[plugin_id]

        # Initialize if needed
        if plugin.state == PluginState.LOADED:
            if not await self.initialize_plugin(plugin_id):
                return False

        try:
            success = await plugin.start()
            if success:
                self._update_plugin_state(plugin_id, PluginState.ENABLED)
                plugin.state = PluginState.ENABLED
            return success
        except Exception as e:
            self._update_plugin_state(plugin_id, PluginState.ERROR, str(e))
            return False

    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if disabled successfully
        """
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        try:
            success = await plugin.stop()
            if success:
                self._update_plugin_state(plugin_id, PluginState.DISABLED)
                plugin.state = PluginState.DISABLED
            return success
        except Exception as e:
            self._update_plugin_state(plugin_id, PluginState.ERROR, str(e))
            return False

    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if unloaded successfully
        """
        if plugin_id not in self.plugins:
            return True

        plugin = self.plugins[plugin_id]

        # Disable first if enabled
        if plugin.state == PluginState.ENABLED:
            await self.disable_plugin(plugin_id)

        try:
            # Cleanup
            await plugin.cleanup()

            # Remove from memory
            del self.plugins[plugin_id]

            # Remove from sys.modules
            module_name = f"plugin_{plugin_id}"
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Remove sandbox
            if plugin_id in self.sandboxes:
                del self.sandboxes[plugin_id]

            self._update_plugin_state(plugin_id, PluginState.UNLOADED)

            return True

        except Exception as e:
            self._update_plugin_state(plugin_id, PluginState.ERROR, str(e))
            return False

    def install_plugin(self, plugin_path: str) -> Optional[str]:
        """Install a plugin from file.

        Args:
            plugin_path: Path to plugin package

        Returns:
            Plugin ID if installed successfully
        """
        plugin_file = Path(plugin_path)

        if not plugin_file.exists():
            return None

        try:
            if plugin_file.suffix == ".zip":
                # Extract and install
                with zipfile.ZipFile(plugin_file) as zf:
                    # Read manifest
                    manifest_data = json.loads(zf.read("manifest.json"))
                    manifest = PluginManifest.from_dict(manifest_data)

                    # Check compatibility
                    if not manifest.is_compatible(self.app_version):
                        return None

                    # Extract to plugins directory
                    extract_dir = self.plugin_dir / manifest.id
                    if extract_dir.exists():
                        shutil.rmtree(extract_dir)

                    zf.extractall(extract_dir)

                    # Register plugin
                    self._register_plugin(manifest, str(extract_dir))
                    self.manifests[manifest.id] = manifest

                    return manifest.id

            elif plugin_file.is_dir():
                # Copy directory
                manifest_path = plugin_file / "manifest.json"
                if not manifest_path.exists():
                    return None

                with open(manifest_path) as f:
                    manifest_data = json.load(f)

                manifest = PluginManifest.from_dict(manifest_data)

                if not manifest.is_compatible(self.app_version):
                    return None

                # Copy to plugins directory
                dest_dir = self.plugin_dir / manifest.id
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)

                shutil.copytree(plugin_file, dest_dir)

                # Register plugin
                self._register_plugin(manifest, str(dest_dir))
                self.manifests[manifest.id] = manifest

                return manifest.id

        except Exception as e:
            print(f"Error installing plugin: {e}")
            return None

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if uninstalled successfully
        """
        # Unload first
        asyncio.run(self.unload_plugin(plugin_id))

        # Get install path
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT install_path FROM plugin_registry WHERE plugin_id = ?", (plugin_id,)
        )
        row = cursor.fetchone()

        if row:
            install_path = row[0]
            # Remove from database
            cursor.execute(
                "DELETE FROM plugin_registry WHERE plugin_id = ?", (plugin_id,)
            )
            cursor.execute(
                "DELETE FROM plugin_dependencies WHERE plugin_id = ?", (plugin_id,)
            )
            cursor.execute(
                "DELETE FROM plugin_permissions WHERE plugin_id = ?", (plugin_id,)
            )
            conn.commit()

            # Remove files
            if install_path and Path(install_path).exists():
                shutil.rmtree(install_path)

        conn.close()

        # Remove from memory
        if plugin_id in self.manifests:
            del self.manifests[plugin_id]

        return True

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict]:
        """Get plugin information.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name, version, manifest, state, enabled, config,
                   installed_at, updated_at, last_loaded, error_message
            FROM plugin_registry
            WHERE plugin_id = ?
        """,
            (plugin_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": plugin_id,
            "name": row[0],
            "version": row[1],
            "manifest": json.loads(row[2]),
            "state": row[3],
            "enabled": bool(row[4]),
            "config": json.loads(row[5]) if row[5] else {},
            "installed_at": row[6],
            "updated_at": row[7],
            "last_loaded": row[8],
            "error_message": row[9],
        }

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        state: Optional[PluginState] = None,
    ) -> List[Dict]:
        """List installed plugins.

        Args:
            plugin_type: Filter by plugin type
            state: Filter by state

        Returns:
            List of plugin information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT plugin_id, name, version, manifest, state, enabled FROM plugin_registry WHERE 1=1"
        params = []

        if state:
            query += " AND state = ?"
            params.append(state.value)

        cursor.execute(query, params)

        plugins = []
        for row in cursor.fetchall():
            manifest = json.loads(row[3])

            if plugin_type and manifest.get("plugin_type") != plugin_type.value:
                continue

            plugins.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "version": row[2],
                    "type": manifest.get("plugin_type"),
                    "state": row[4],
                    "enabled": bool(row[5]),
                }
            )

        conn.close()
        return plugins

    def _register_plugin(self, manifest: PluginManifest, install_path: str):
        """Register plugin in database.

        Args:
            manifest: Plugin manifest
            install_path: Installation path
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO plugin_registry
            (plugin_id, name, version, manifest, state, install_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                manifest.id,
                manifest.name,
                manifest.version,
                json.dumps(manifest.to_dict()),
                PluginState.DISCOVERED.value,
                install_path,
            ),
        )

        # Register dependencies
        if manifest.dependencies:
            for dep in manifest.dependencies:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO plugin_dependencies
                    (plugin_id, dependency_id)
                    VALUES (?, ?)
                """,
                    (manifest.id, dep),
                )

        # Register permissions
        if manifest.permissions:
            for perm in manifest.permissions:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO plugin_permissions
                    (plugin_id, permission)
                    VALUES (?, ?)
                """,
                    (manifest.id, perm),
                )

        conn.commit()
        conn.close()

    def _check_dependencies(self, manifest: PluginManifest) -> bool:
        """Check if plugin dependencies are satisfied.

        Args:
            manifest: Plugin manifest

        Returns:
            True if dependencies are satisfied
        """
        if not manifest.dependencies:
            return True

        for dep_id in manifest.dependencies:
            if dep_id not in self.manifests:
                return False

            # Check if dependency is loaded
            if dep_id not in self.plugins:
                if not self.load_plugin(dep_id):
                    return False

        return True

    def _install_dependencies(self, dependencies: List[str]):
        """Install Python dependencies.

        Args:
            dependencies: List of pip packages
        """
        for dep in dependencies:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            except subprocess.CalledProcessError:
                pass

    def _update_plugin_state(
        self, plugin_id: str, state: PluginState, error_message: Optional[str] = None
    ):
        """Update plugin state in database.

        Args:
            plugin_id: Plugin identifier
            state: New state
            error_message: Error message if any
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plugin_registry
            SET state = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE plugin_id = ?
        """,
            (state.value, error_message, plugin_id),
        )

        if state == PluginState.LOADED:
            cursor.execute(
                """
                UPDATE plugin_registry
                SET last_loaded = CURRENT_TIMESTAMP
                WHERE plugin_id = ?
            """,
                (plugin_id,),
            )

        conn.commit()
        conn.close()

    def resolve_dependencies(self) -> List[str]:
        """Resolve plugin loading order based on dependencies.

        Returns:
            Ordered list of plugin IDs
        """
        # Build dependency graph
        graph = {}
        for plugin_id, manifest in self.manifests.items():
            graph[plugin_id] = manifest.dependencies or []

        # Topological sort
        visited = set()
        stack = []

        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, []):
                visit(dep)
            stack.append(node)

        for plugin_id in graph:
            visit(plugin_id)

        return stack


class PluginAPI:
    """API exposed to plugins."""

    def __init__(self, loader: PluginLoader, plugin_id: str):
        """Initialize plugin API.

        Args:
            loader: Plugin loader instance
            plugin_id: Plugin identifier
        """
        self.loader = loader
        self.plugin_id = plugin_id

    def get_config(self) -> Dict:
        """Get plugin configuration.

        Returns:
            Plugin configuration
        """
        info = self.loader.get_plugin_info(self.plugin_id)
        return info.get("config", {}) if info else {}

    def save_config(self, config: Dict) -> bool:
        """Save plugin configuration.

        Args:
            config: Configuration to save

        Returns:
            True if saved successfully
        """
        conn = sqlite3.connect(self.loader.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plugin_registry
            SET config = ?, updated_at = CURRENT_TIMESTAMP
            WHERE plugin_id = ?
        """,
            (json.dumps(config), self.plugin_id),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def log(self, level: str, message: str):
        """Log plugin message.

        Args:
            level: Log level
            message: Log message
        """
        conn = sqlite3.connect(self.loader.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plugin_logs (plugin_id, level, message)
            VALUES (?, ?, ?)
        """,
            (self.plugin_id, level, message),
        )

        conn.commit()
        conn.close()

    def emit_event(self, event: str, data: Any):
        """Emit plugin event.

        Args:
            event: Event name
            data: Event data
        """
        # This will be handled by the hook system
        pass

    def call_hook(self, hook: str, *args, **kwargs) -> Any:
        """Call a hook.

        Args:
            hook: Hook name
            *args: Hook arguments
            **kwargs: Hook keyword arguments

        Returns:
            Hook result
        """
        # This will be handled by the hook system
        pass

    def record_metric(self, metric_type: str, value: float):
        """Record plugin metric.

        Args:
            metric_type: Metric type
            value: Metric value
        """
        conn = sqlite3.connect(self.loader.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plugin_metrics (plugin_id, metric_type, value)
            VALUES (?, ?, ?)
        """,
            (self.plugin_id, metric_type, value),
        )

        conn.commit()
        conn.close()

    def has_permission(self, permission: str) -> bool:
        """Check if plugin has permission.

        Args:
            permission: Permission to check

        Returns:
            True if permission is granted
        """
        conn = sqlite3.connect(self.loader.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT granted FROM plugin_permissions
            WHERE plugin_id = ? AND permission = ?
        """,
            (self.plugin_id, permission),
        )

        row = cursor.fetchone()
        conn.close()

        return bool(row[0]) if row else False
