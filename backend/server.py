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
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
import io

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import socketio
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from kasa import Discover, Device, Credentials, SmartDevice
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write_api import SYNCHRONOUS

from database import DatabaseManager
from models import DeviceData, DeviceReading, ElectricityRate, User, UserCreate, UserRole, UserLogin, Token, Permission
from auth import AuthManager, get_current_user, require_auth, require_permission, require_admin, is_local_network_ip, get_network_access_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import data management modules
try:
    from data_export import DataExporter, BulkOperations
    from data_aggregation import DataAggregator
    from cache_manager import CacheManager
    data_management_available = True
except ImportError:
    logger.warning("Data management modules not available. Some features will be disabled.")
    data_management_available = False

# Import additional modules
try:
    from health_monitor import HealthMonitor
    from prometheus_metrics import MetricsCollector as PrometheusMetrics
    from alert_management import AlertManager
    from device_groups import DeviceGroupManager
    from backup_manager import BackupManager
    from audit_logging import AuditLogger
    monitoring_available = True
except ImportError as e:
    logger.warning(f"Monitoring modules not available: {e}")
    monitoring_available = False


class DeviceManager:
    """Manages Kasa device connections and polling."""
    
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.credentials: Optional[Credentials] = None
        self.last_discovery: Optional[datetime] = None
        
    async def discover_devices(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Device]:
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
            await device.update()
            
            # Extract power consumption data
            power_data = {}
            if hasattr(device, 'modules') and 'Energy' in device.modules:
                energy_module = device.modules['Energy']
                power_data = {
                    'current_power_w': energy_module.current_consumption,
                    'today_energy_kwh': energy_module.consumption_today,
                    'month_energy_kwh': energy_module.consumption_this_month,
                    'voltage': energy_module.voltage,
                    'current': energy_module.current,
                }
            elif hasattr(device, 'emeter_realtime'):
                emeter = await device.emeter_realtime
                power_data = {
                    'current_power_w': emeter.power,
                    'voltage': emeter.voltage,
                    'current': emeter.current,
                    'total_energy_kwh': emeter.total,
                }
            
            return DeviceData(
                ip=device_ip,
                alias=device.alias,
                model=device.model,
                device_type=str(device.device_type),
                is_on=device.is_on,
                rssi=device.rssi,
                mac=device.mac,
                **power_data,
                timestamp=datetime.now(timezone.utc)
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
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*'
        )
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
            self.health_monitor = HealthMonitor()
            self.prometheus_metrics = PrometheusMetrics()
            self.alert_manager = AlertManager(db_path="kasa_monitor.db")
            self.device_group_manager = DeviceGroupManager(db_path="kasa_monitor.db")
            self.backup_manager = BackupManager(db_path="kasa_monitor.db", backup_dir="./backups")
            self.audit_logger = AuditLogger(db_path="kasa_monitor.db", log_dir="./logs/audit")
        
        self.setup_middleware()
        self.setup_routes()
        self.setup_data_management_routes()
        self.setup_monitoring_routes()
        self.setup_socketio()
        
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage application lifecycle."""
        # Startup
        await self.db_manager.initialize()
        
        # Load saved devices on startup
        await self.load_saved_devices()
        
        self.scheduler.start()
        
        # Schedule device polling every 30 seconds
        self.scheduler.add_job(
            self.poll_and_store_data,
            trigger=IntervalTrigger(seconds=30),
            id='device_polling',
            replace_existing=True
        )
        
        # Start data aggregation service if available
        if self.data_aggregator:
            await self.data_aggregator.start()
            logger.info("Data aggregation service started")
        
        yield
        
        # Shutdown
        if self.data_aggregator:
            await self.data_aggregator.stop()
        if self.cache_manager:
            await self.cache_manager.close()
        
        self.scheduler.shutdown()
        await self.db_manager.close()
    
    def setup_middleware(self):
        """Configure CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Set up FastAPI routes."""
        
        @self.app.get("/api/devices")
        async def get_devices():
            """Get list of all discovered devices."""
            devices_data = []
            for ip, device in self.device_manager.devices.items():
                devices_data.append({
                    'ip': ip,
                    'alias': device.alias,
                    'model': device.model,
                    'device_type': str(device.device_type),
                    'is_on': device.is_on,
                    'mac': device.mac
                })
            return devices_data
        
        @self.app.post("/api/discover")
        async def discover_devices(credentials: Optional[Dict[str, str]] = None):
            """Trigger device discovery and save to database."""
            username = credentials.get('username') if credentials else None
            password = credentials.get('password') if credentials else None
            
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
            
            return {'discovered': len(devices)}
        
        @self.app.post("/api/devices/manual")
        async def add_manual_device(device_config: dict):
            """Manually add a device by IP address."""
            ip = device_config.get('ip')
            alias = device_config.get('alias', f'Device at {ip}')
            
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
                        logger.info(f"Manually added device {alias} ({ip})")
                        return {"status": "success", "device": device_data.dict()}
                else:
                    raise HTTPException(status_code=404, detail=f"Cannot connect to device at {ip}")
            except Exception as e:
                logger.error(f"Error adding manual device {ip}: {e}")
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
                
                logger.info(f"Removed device {device_ip}")
                return {"status": "success", "message": f"Device {device_ip} removed"}
            except Exception as e:
                logger.error(f"Error removing device {device_ip}: {e}")
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
                "discovery_enabled": os.getenv("DISCOVERY_ENABLED", "false").lower() == "true",
                "manual_devices_enabled": os.getenv("MANUAL_DEVICES_ENABLED", "true").lower() == "true",
                "host_ip": os.getenv("DOCKER_HOST_IP", None)
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
            interval: str = "1h"
        ):
            """Get historical data for a device."""
            history = await self.db_manager.get_device_history(
                device_ip, start_time, end_time, interval
            )
            return history
        
        @self.app.get("/api/device/{device_ip}/stats")
        async def get_device_stats(device_ip: str):
            """Get statistics for a device."""
            stats = await self.db_manager.get_device_stats(device_ip)
            return stats
        
        @self.app.post("/api/device/{device_ip}/control")
        async def control_device(device_ip: str, action: str):
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
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
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
        async def update_device_monitoring(device_ip: str, request: Dict[str, bool]):
            """Enable or disable monitoring for a device."""
            enabled = request.get('enabled', True)
            success = await self.db_manager.update_device_monitoring(device_ip, enabled)
            if success:
                return {"message": f"Monitoring {'enabled' if enabled else 'disabled'} for device {device_ip}"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update monitoring status")
        
        @self.app.put("/api/devices/{device_ip}/ip")
        async def update_device_ip(device_ip: str, request: Dict[str, str]):
            """Update a device's IP address."""
            new_ip = request.get('new_ip')
            if not new_ip:
                raise HTTPException(status_code=400, detail="New IP is required")
            
            success = await self.db_manager.update_device_ip(device_ip, new_ip)
            if success:
                # Update device manager
                if device_ip in self.device_manager.devices:
                    device = self.device_manager.devices.pop(device_ip)
                    self.device_manager.devices[new_ip] = device
                return {"message": f"Device IP updated from {device_ip} to {new_ip}"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update IP (may already exist)")
        
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
        async def update_device_notes(device_ip: str, request: Dict[str, str], user: User = Depends(require_permission(Permission.DEVICES_EDIT))):
            """Update notes for a device."""
            notes = request.get('notes', '')
            success = await self.db_manager.update_device_notes(device_ip, notes)
            if success:
                return {"message": "Notes updated"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update notes")
        
        # Authentication endpoints
        @self.app.post("/api/auth/login", response_model=Token)
        async def login(login_data: UserLogin):
            """Authenticate user and return JWT token."""
            user = await self.db_manager.get_user_by_username(login_data.username)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )
            
            password_hash = await self.db_manager.get_user_password_hash(login_data.username)
            if not password_hash or not AuthManager.verify_password(login_data.password, password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )
            
            # Update last login
            await self.db_manager.update_user_login(login_data.username)
            
            # Create access token
            access_token = AuthManager.create_access_token(data={"user": user.model_dump()})
            
            return Token(
                access_token=access_token,
                expires_in=1800,  # 30 minutes
                user=user
            )
        
        @self.app.post("/api/auth/setup", response_model=User)
        async def initial_setup(admin_data: UserCreate):
            """Create initial admin user."""
            setup_required = await self.db_manager.is_setup_required()
            if not setup_required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Setup already completed"
                )
            
            # Force admin role for initial setup
            admin_data.role = UserRole.ADMIN
            
            success = await self.db_manager.create_admin_user(
                admin_data.username,
                admin_data.email,
                admin_data.full_name,
                admin_data.password
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
                        permissions=[]
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create admin user"
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
        
        # User management endpoints
        @self.app.get("/api/users", response_model=List[User])
        async def get_users(user: User = Depends(require_permission(Permission.USERS_VIEW))):
            """Get all users."""
            users = await self.db_manager.get_all_users()
            # Remove password-related data for security
            for user_item in users:
                user_item.permissions = AuthManager.get_user_permissions(user_item.role)
            return users
        
        @self.app.post("/api/users", response_model=User)
        async def create_user(user_data: UserCreate, current_user: User = Depends(require_permission(Permission.USERS_INVITE))):
            """Create a new user."""
            new_user = await self.db_manager.create_user(user_data)
            if not new_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user (username or email may already exist)"
                )
            new_user.permissions = AuthManager.get_user_permissions(new_user.role)
            return new_user
        
        @self.app.put("/api/users/{user_id}")
        async def update_user(user_id: int, updates: Dict[str, Any], current_user: User = Depends(require_permission(Permission.USERS_EDIT))):
            """Update user information."""
            success = await self.db_manager.update_user(user_id, updates)
            if success:
                return {"message": "User updated successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update user")
        
        @self.app.patch("/api/users/{user_id}")
        async def patch_user(user_id: int, updates: Dict[str, Any], current_user: User = Depends(require_permission(Permission.USERS_EDIT))):
            """Partially update user information."""
            success = await self.db_manager.update_user(user_id, updates)
            if success:
                return {"message": "User updated successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update user")
        
        @self.app.delete("/api/users/{user_id}")
        async def delete_user(user_id: int, current_user: User = Depends(require_permission(Permission.USERS_REMOVE))):
            """Delete a user."""
            if user_id == current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete your own account"
                )
            
            success = await self.db_manager.delete_user(user_id)
            if success:
                return {"message": "User deleted successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to delete user")
        
        # System configuration endpoints
        @self.app.get("/api/system/config")
        async def get_system_config(user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
            """Get system configuration."""
            # Get configuration from database or use defaults
            config = {
                "ssl": {
                    "enabled": False,
                    "cert_path": "",
                    "key_path": "",
                    "force_https": False
                },
                "network": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "allowed_hosts": [],
                    "local_only": False,
                    "cors_origins": []
                },
                "database_path": "kasa_monitor.db",
                "influxdb_enabled": False,
                "polling_interval": 30
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
        async def update_system_config(config: Dict[str, Any], user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
            """Update system configuration."""
            for key, value in config.items():
                await self.db_manager.set_system_config(key, str(value))
            return {"message": "Configuration updated"}
        
        @self.app.put("/api/system/config")
        async def update_system_config_put(config: Dict[str, Any], user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
            """Update system configuration (PUT method)."""
            # Store configuration in database
            for key, value in config.items():
                if isinstance(value, dict):
                    # Handle nested configs like ssl, network
                    for sub_key, sub_value in value.items():
                        await self.db_manager.set_system_config(f"{key}.{sub_key}", str(sub_value))
                else:
                    await self.db_manager.set_system_config(key, str(value))
            return {"message": "Configuration updated successfully"}
        
        # Permission management endpoints
        @self.app.get("/api/permissions")
        async def get_all_permissions(user: User = Depends(require_permission(Permission.USERS_VIEW))):
            """Get all available permissions."""
            permissions = []
            category_map = {
                'devices': 'device_management',
                'rates': 'rate_management',
                'costs': 'rate_management',
                'users': 'user_management',
                'system': 'system_config'
            }
            
            # Import Permission enum to iterate through it
            from models import Permission
            
            # Get all permission values
            for perm_name in Permission.__members__:
                perm = Permission[perm_name]
                parts = perm.value.split('.')
                category_key = parts[0] if len(parts) > 0 else 'other'
                category = category_map.get(category_key, 'other')
                
                # Create a more readable description
                if len(parts) > 1:
                    action = parts[1].replace('_', ' ').title()
                    resource = parts[0].title()
                    description = f"{action} {resource}"
                else:
                    description = perm.value.replace('.', ' - ').replace('_', ' ').title()
                
                permissions.append({
                    "name": perm.value,
                    "description": description,
                    "category": category
                })
            return permissions
        
        @self.app.get("/api/roles/permissions")
        async def get_roles_permissions(user: User = Depends(require_permission(Permission.USERS_VIEW))):
            """Get permissions for all roles."""
            from auth import ROLE_PERMISSIONS
            from models import UserRole
            role_perms = []
            for role in UserRole:
                role_perms.append({
                    "role": role.value,
                    "permissions": [p.value for p in ROLE_PERMISSIONS.get(role, [])]
                })
            return role_perms
        
        @self.app.put("/api/roles/{role}/permissions")
        async def update_role_permissions(role: str, permissions: List[str], 
                                         user: User = Depends(require_permission(Permission.USERS_PERMISSIONS))):
            """Update permissions for a role (admin only)."""
            # Note: This would need database storage for custom role permissions
            # For now, return success but note that default roles have fixed permissions
            return {"message": f"Permissions updated for role {role}", 
                   "note": "Default roles have fixed permissions"}
        
        @self.app.post("/api/roles/{role}/permissions")
        async def toggle_role_permission(role: str, request: dict,
                                        user: User = Depends(require_permission(Permission.USERS_PERMISSIONS))):
            """Toggle a single permission for a role."""
            permission = request.get("permission")
            action = request.get("action", "toggle")
            
            # Note: This would need database storage for custom role permissions
            # For now, return success but note that default roles have fixed permissions
            return {"message": f"Permission {permission} {action} for role {role}", 
                   "note": "Default roles have fixed permissions"}
    
    def setup_socketio(self):
        """Set up Socket.IO for real-time updates."""
        
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"Client {sid} connected")
            await self.sio.emit('connected', {'data': 'Connected to server'}, to=sid)
        
        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Client {sid} disconnected")
        
        @self.sio.event
        async def subscribe_device(sid, data):
            device_ip = data.get('device_ip')
            await self.sio.enter_room(sid, f"device_{device_ip}")
            logger.info(f"Client {sid} subscribed to device {device_ip}")
        
        @self.sio.event
        async def unsubscribe_device(sid, data):
            device_ip = data.get('device_ip')
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
        async def export_devices(format: str = "csv", include_energy: bool = True):
            """Export device data in various formats."""
            if not self.data_exporter:
                raise HTTPException(status_code=503, detail="Export service not available")
            
            try:
                if format == "csv":
                    content = await self.data_exporter.export_devices_csv()
                    return StreamingResponse(
                        io.BytesIO(content),
                        media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=devices.csv"}
                    )
                elif format == "excel":
                    content = await self.data_exporter.export_devices_excel(include_energy=include_energy)
                    return StreamingResponse(
                        io.BytesIO(content),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": "attachment; filename=devices.xlsx"}
                    )
                else:
                    raise HTTPException(status_code=400, detail="Unsupported format")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/export/energy")
        async def export_energy(
            device_ip: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            format: str = "csv"
        ):
            """Export energy consumption data."""
            if not self.data_exporter:
                raise HTTPException(status_code=503, detail="Export service not available")
            
            try:
                if format == "csv":
                    content = await self.data_exporter.export_energy_data_csv(
                        device_ip=device_ip,
                        start_date=start_date,
                        end_date=end_date
                    )
                    return StreamingResponse(
                        io.BytesIO(content),
                        media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=energy_data.csv"}
                    )
                else:
                    raise HTTPException(status_code=400, detail="Unsupported format")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/export/report")
        async def generate_report(
            report_type: str = "monthly",
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
        ):
            """Generate PDF report."""
            if not self.data_exporter:
                raise HTTPException(status_code=503, detail="Export service not available")
            
            try:
                content = await self.data_exporter.generate_pdf_report(
                    report_type=report_type,
                    start_date=start_date,
                    end_date=end_date
                )
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={report_type}_report.pdf"}
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Aggregation endpoints
        @self.app.get("/api/aggregation")
        async def get_aggregated_data(
            period: str = "day",
            device_ip: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
        ):
            """Get aggregated data for specified period."""
            if not self.data_aggregator:
                raise HTTPException(status_code=503, detail="Aggregation service not available")
            
            try:
                from data_aggregation import AggregationPeriod
                period_enum = AggregationPeriod(period.lower())
                data = await self.data_aggregator.get_aggregated_data(
                    device_ip=device_ip,
                    period=period_enum,
                    start_date=start_date,
                    end_date=end_date
                )
                return data
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid aggregation period")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/statistics/{device_ip}")
        async def get_device_statistics(
            device_ip: str,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
        ):
            """Get statistical analysis for a device."""
            if not self.data_aggregator:
                raise HTTPException(status_code=503, detail="Aggregation service not available")
            
            try:
                stats = await self.data_aggregator.calculate_statistics(
                    device_ip=device_ip,
                    start_date=start_date,
                    end_date=end_date
                )
                return {
                    "device_ip": device_ip,
                    "statistics": stats,
                    "start_date": start_date or datetime.now() - timedelta(days=30),
                    "end_date": end_date or datetime.now()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/trends/{device_ip}")
        async def get_trend_analysis(
            device_ip: str,
            period: str = "day",
            lookback: int = 30
        ):
            """Get trend analysis for a device."""
            if not self.data_aggregator:
                raise HTTPException(status_code=503, detail="Aggregation service not available")
            
            try:
                from data_aggregation import AggregationPeriod
                period_enum = AggregationPeriod(period.lower())
                analysis = await self.data_aggregator.get_trend_analysis(
                    device_ip=device_ip,
                    period=period_enum,
                    lookback_periods=lookback
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
            async def detailed_health(current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
                """Detailed health status with all components."""
                return await self.health_monitor.perform_health_check()
        
        # Prometheus metrics endpoint
        if self.prometheus_metrics:
            @self.app.get("/api/metrics")
            async def get_metrics():
                """Prometheus metrics endpoint."""
                return Response(
                    content=self.prometheus_metrics.get_metrics(),
                    media_type="text/plain"
                )
        
        # Alert management endpoints
        if self.alert_manager:
            @self.app.get("/api/alerts")
            async def get_alerts(
                severity: Optional[str] = None,
                status: Optional[str] = None,
                current_user: User = Depends(require_permission(Permission.DEVICES_VIEW))
            ):
                """Get active alerts."""
                return await self.alert_manager.get_alerts(
                    severity=severity,
                    status=status
                )
            
            @self.app.get("/api/alerts/rules")
            async def get_alert_rules(current_user: User = Depends(require_permission(Permission.DEVICES_VIEW))):
                """Get configured alert rules."""
                return await self.alert_manager.get_rules()
            
            @self.app.post("/api/alerts/rules")
            async def create_alert_rule(
                rule: Dict[str, Any],
                current_user: User = Depends(require_permission(Permission.DEVICES_EDIT))
            ):
                """Create a new alert rule."""
                return await self.alert_manager.create_rule(rule)
            
            @self.app.delete("/api/alerts/rules/{rule_id}")
            async def delete_alert_rule(
                rule_id: int,
                current_user: User = Depends(require_permission(Permission.DEVICES_EDIT))
            ):
                """Delete an alert rule."""
                success = await self.alert_manager.delete_rule(rule_id)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Rule not found")
            
            @self.app.post("/api/alerts/{alert_id}/acknowledge")
            async def acknowledge_alert(
                alert_id: int,
                current_user: User = Depends(require_permission(Permission.DEVICES_EDIT))
            ):
                """Acknowledge an alert."""
                success = await self.alert_manager.acknowledge_alert(
                    alert_id,
                    user_id=current_user.id
                )
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Alert not found")
            
            @self.app.get("/api/alerts/history")
            async def get_alert_history(
                start_date: Optional[datetime] = None,
                end_date: Optional[datetime] = None,
                current_user: User = Depends(require_permission(Permission.DEVICES_VIEW))
            ):
                """Get alert history."""
                return await self.alert_manager.get_history(
                    start_date=start_date,
                    end_date=end_date
                )
        
        # Device groups endpoints
        if self.device_group_manager:
            @self.app.get("/api/device-groups")
            async def get_device_groups(current_user: User = Depends(require_permission(Permission.DEVICES_VIEW))):
                """Get all device groups."""
                return self.device_group_manager.get_all_groups()
            
            @self.app.get("/api/device-groups/{group_id}")
            async def get_device_group(
                group_id: int,
                current_user: User = Depends(require_permission(Permission.DEVICES_VIEW))
            ):
                """Get a specific device group."""
                group = self.device_group_manager.get_group(group_id)
                if group:
                    return group
                raise HTTPException(status_code=404, detail="Group not found")
            
            @self.app.post("/api/device-groups")
            async def create_device_group(
                group_data: Dict[str, Any],
                current_user: User = Depends(require_permission(Permission.DEVICES_EDIT))
            ):
                """Create a new device group."""
                return self.device_group_manager.create_group(group_data)
            
            @self.app.put("/api/device-groups/{group_id}")
            async def update_device_group(
                group_id: int,
                group_data: Dict[str, Any],
                current_user: User = Depends(require_permission(Permission.DEVICES_EDIT))
            ):
                """Update a device group."""
                success = self.device_group_manager.update_group(group_id, group_data)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Group not found")
            
            @self.app.delete("/api/device-groups/{group_id}")
            async def delete_device_group(
                group_id: int,
                current_user: User = Depends(require_permission(Permission.DEVICES_EDIT))
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
                current_user: User = Depends(require_permission(Permission.DEVICES_CONTROL))
            ):
                """Control all devices in a group."""
                result = self.device_group_manager.control_group(
                    group_id,
                    action.get("action", "off")
                )
                return {"status": "success", "result": result}
        
        # Backup and restore endpoints
        if self.backup_manager:
            @self.app.get("/api/backups")
            async def get_backups(current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
                """Get list of available backups."""
                return await self.backup_manager.list_backups()
            
            @self.app.get("/api/backups/progress")
            async def get_backup_progress(current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
                """Get current backup progress."""
                return self.backup_manager.get_backup_progress()
            
            @self.app.post("/api/backups/create")
            async def create_backup(
                backup_options: Dict[str, Any],
                current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))
            ):
                """Create a new backup."""
                backup_info = await self.backup_manager.create_backup(
                    backup_type=backup_options.get("type", "manual"),
                    description=backup_options.get("description"),
                    compress=backup_options.get("compress", True),
                    encrypt=backup_options.get("encrypt", False)
                )
                return {"status": "success", "backup": backup_info}
            
            @self.app.get("/api/backups/{backup_id}/download")
            async def download_backup(
                backup_id: int,
                current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))
            ):
                """Download a backup file."""
                file_path = await self.backup_manager.get_backup_file(backup_id)
                if file_path and os.path.exists(file_path):
                    return FileResponse(file_path)
                raise HTTPException(status_code=404, detail="Backup not found")
            
            @self.app.delete("/api/backups/{backup_id}")
            async def delete_backup(
                backup_id: int,
                current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))
            ):
                """Delete a backup."""
                success = await self.backup_manager.delete_backup(backup_id)
                if success:
                    return {"status": "success"}
                raise HTTPException(status_code=404, detail="Backup not found")
            
            @self.app.post("/api/backups/restore")
            async def restore_backup(
                backup: UploadFile,
                current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))
            ):
                """Restore from a backup file."""
                # Save uploaded file temporarily
                temp_path = f"/tmp/{backup.filename}"
                with open(temp_path, "wb") as f:
                    content = await backup.read()
                    f.write(content)
                
                success = await self.backup_manager.restore_backup(temp_path)
                os.remove(temp_path)
                
                if success:
                    return {"status": "success", "message": "Backup restored successfully"}
                raise HTTPException(status_code=400, detail="Failed to restore backup")
            
            @self.app.get("/api/backups/schedules")
            async def get_backup_schedules(current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
                """Get backup schedules."""
                return await self.backup_manager.get_schedules()
        
        # Audit logging endpoints
        if self.audit_logger:
            @self.app.get("/api/audit-logs")
            async def get_audit_logs(
                page: int = 1,
                category: Optional[str] = None,
                severity: Optional[str] = None,
                range: str = "7days",
                search: Optional[str] = None,
                current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))
            ):
                """Get audit logs."""
                logs, total_pages = await self.audit_logger.get_logs(
                    page=page,
                    category=category,
                    severity=severity,
                    date_range=range,
                    search=search
                )
                return {
                    "logs": logs,
                    "total_pages": total_pages,
                    "current_page": page
                }
            
            @self.app.post("/api/audit-logs/export")
            async def export_audit_logs(
                export_options: Dict[str, Any],
                current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))
            ):
                """Export audit logs."""
                file_path = await self.audit_logger.export_logs(
                    format=export_options.get("format", "csv"),
                    date_range=export_options.get("date_range"),
                    category=export_options.get("category")
                )
                if file_path:
                    return FileResponse(file_path)
                raise HTTPException(status_code=500, detail="Failed to export logs")
    
    async def load_saved_devices(self):
        """Load saved devices from database on startup."""
        try:
            saved_devices = await self.db_manager.get_monitored_devices()
            logger.info(f"Loading {len(saved_devices)} saved devices from database")
            
            for device_info in saved_devices:
                try:
                    # Try to connect to the device
                    device = await SmartDevice.connect(
                        device_info['device_ip'],
                        credentials=self.device_manager.credentials
                    )
                    await device.update()
                    self.device_manager.devices[device_info['device_ip']] = device
                    logger.info(f"Connected to saved device: {device_info['alias']} ({device_info['device_ip']})")
                except Exception as e:
                    logger.warning(f"Could not connect to saved device {device_info['alias']} ({device_info['device_ip']}): {e}")
        except Exception as e:
            logger.error(f"Error loading saved devices: {e}")
    
    async def poll_and_store_data(self):
        """Poll all devices and store data in database."""
        try:
            # Only poll devices that are being monitored
            monitored = await self.db_manager.get_monitored_devices()
            monitored_ips = {d['device_ip'] for d in monitored}
            
            # Filter devices to only poll monitored ones
            device_data_list = []
            for ip in monitored_ips:
                if ip in self.device_manager.devices:
                    device_data = await self.device_manager.get_device_data(ip)
                    if device_data:
                        device_data_list.append(device_data)
            
            for device_data in device_data_list:
                # Store in database
                await self.db_manager.store_device_reading(device_data)
                
                # Emit real-time update via Socket.IO
                await self.sio.emit(
                    'device_update',
                    device_data.dict(),
                    room=f"device_{device_data.ip}"
                )
            
            logger.info(f"Polled and stored data for {len(device_data_list)} devices")
        except Exception as e:
            logger.error(f"Error in polling cycle: {e}")


if __name__ == "__main__":
    app_instance = KasaMonitorApp()
    uvicorn.run(app_instance.app, host="0.0.0.0", port=8000)