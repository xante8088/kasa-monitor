"""Power Monitor Example Plugin.

This plugin monitors device power consumption and sends alerts when 
devices exceed configured power thresholds.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from plugin_system import PluginBase

logger = logging.getLogger(__name__)


class PowerMonitorPlugin(PluginBase):
    """Example plugin that monitors power consumption."""

    def __init__(self):
        super().__init__()
        self.power_threshold = 1000  # Default threshold in watts
        self.check_interval = 60     # Default check interval in seconds
        self.enabled_devices = []    # Empty = monitor all devices
        self.monitoring_task = None
        self.device_alerts = {}      # Track alert timestamps per device

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            # Load configuration
            config = await self.get_config()
            self.power_threshold = config.get('power_threshold', 1000)
            self.check_interval = config.get('check_interval', 60)
            self.enabled_devices = config.get('enabled_devices', [])

            # Register hooks
            await self.hook_manager.register_hook(
                'device.reading_updated', 
                self.on_device_reading_updated
            )
            await self.hook_manager.register_hook(
                'device.discovered', 
                self.on_device_discovered
            )

            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
            
            logger.info(f"Power Monitor initialized with threshold: {self.power_threshold}W")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Power Monitor plugin: {e}")
            return False

    async def shutdown(self):
        """Shutdown the plugin."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Unregister hooks
        await self.hook_manager.unregister_hook(
            'device.reading_updated', 
            self.on_device_reading_updated
        )
        await self.hook_manager.unregister_hook(
            'device.discovered', 
            self.on_device_discovered
        )
        
        logger.info("Power Monitor plugin shutdown complete")

    async def on_device_reading_updated(self, device_data: Dict[str, Any]):
        """Handle device reading updates."""
        device_ip = device_data.get('ip')
        current_power = device_data.get('current_power_w', 0)
        
        # Check if we should monitor this device
        if self.enabled_devices and device_ip not in self.enabled_devices:
            return
            
        # Check if power exceeds threshold
        if current_power > self.power_threshold:
            await self.send_high_power_alert(device_data)

    async def on_device_discovered(self, device_data: Dict[str, Any]):
        """Handle new device discovery."""
        device_ip = device_data.get('ip')
        device_name = device_data.get('alias', f'Device {device_ip}')
        
        logger.info(f"New device discovered for monitoring: {device_name} ({device_ip})")

    async def monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self.check_all_devices()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Brief pause before retrying

    async def check_all_devices(self):
        """Check all monitored devices."""
        try:
            # Get current device data from the database
            devices = await self.db_manager.get_monitored_devices()
            
            for device in devices:
                if self.enabled_devices and device['ip'] not in self.enabled_devices:
                    continue
                    
                # Get latest reading
                latest_reading = await self.db_manager.get_latest_device_reading(device['ip'])
                if latest_reading and latest_reading.get('current_power_w', 0) > self.power_threshold:
                    await self.send_high_power_alert(latest_reading)
                    
        except Exception as e:
            logger.error(f"Error checking devices: {e}")

    async def send_high_power_alert(self, device_data: Dict[str, Any]):
        """Send high power consumption alert."""
        device_ip = device_data.get('ip')
        device_name = device_data.get('alias', f'Device {device_ip}')
        current_power = device_data.get('current_power_w', 0)
        
        # Throttle alerts (only send once per hour per device)
        now = datetime.now(timezone.utc)
        last_alert = self.device_alerts.get(device_ip)
        
        if last_alert and (now - last_alert).total_seconds() < 3600:
            return  # Already sent alert recently
            
        self.device_alerts[device_ip] = now
        
        # Create alert message
        message = (
            f"⚡ High Power Alert\\n"
            f"Device: {device_name} ({device_ip})\\n"
            f"Current Power: {current_power:.1f}W\\n"
            f"Threshold: {self.power_threshold}W\\n"
            f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Send notification through hook system
        await self.hook_manager.emit_hook('notification.send', {
            'type': 'power_alert',
            'severity': 'warning',
            'title': 'High Power Consumption',
            'message': message,
            'device_ip': device_ip,
            'power_usage': current_power,
            'threshold': self.power_threshold
        })
        
        logger.warning(f"High power alert: {device_name} using {current_power:.1f}W")

    async def get_status(self) -> Dict[str, Any]:
        """Get plugin status information."""
        return {
            'power_threshold': self.power_threshold,
            'check_interval': self.check_interval,
            'enabled_devices_count': len(self.enabled_devices) if self.enabled_devices else 'all',
            'monitoring_active': self.monitoring_task is not None and not self.monitoring_task.done(),
            'recent_alerts': len(self.device_alerts)
        }

    async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plugin-specific actions."""
        if action == 'update_threshold':
            new_threshold = params.get('threshold')
            if new_threshold and new_threshold > 0:
                self.power_threshold = new_threshold
                # Update config
                await self.update_config({'power_threshold': new_threshold})
                return {'status': 'success', 'message': f'Threshold updated to {new_threshold}W'}
            else:
                return {'status': 'error', 'message': 'Invalid threshold value'}
                
        elif action == 'clear_alerts':
            self.device_alerts.clear()
            return {'status': 'success', 'message': 'Alert history cleared'}
            
        elif action == 'test_alert':
            device_ip = params.get('device_ip')
            if device_ip:
                await self.send_high_power_alert({
                    'ip': device_ip,
                    'alias': f'Test Device {device_ip}',
                    'current_power_w': self.power_threshold + 100
                })
                return {'status': 'success', 'message': 'Test alert sent'}
            else:
                return {'status': 'error', 'message': 'Device IP required'}
                
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}