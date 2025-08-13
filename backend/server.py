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
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
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
        self.setup_middleware()
        self.setup_routes()
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
        
        yield
        
        # Shutdown
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
            config = get_network_access_config()
            return config
        
        @self.app.post("/api/system/config")
        async def update_system_config(config: Dict[str, Any], user: User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
            """Update system configuration."""
            for key, value in config.items():
                await self.db_manager.set_system_config(key, str(value))
            return {"message": "Configuration updated"}
        
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
            
            for perm in Permission:
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
            from backend.auth import ROLE_PERMISSIONS
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