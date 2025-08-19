"""Basic Plugin Template.

This is a template for creating new Kasa Monitor plugins.
Replace the class name, functionality, and configuration as needed.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from plugin_system import PluginBase

logger = logging.getLogger(__name__)


class MyPlugin(PluginBase):
    """Basic plugin template."""

    def __init__(self):
        super().__init__()
        # Initialize your plugin variables here
        self.example_setting = "default_value"
        self.background_task = None

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            # Load configuration
            config = await self.get_config()
            self.example_setting = config.get('example_setting', 'default_value')

            # Register hooks that your plugin will listen to
            await self.hook_manager.register_hook(
                'device.reading_updated', 
                self.on_device_reading_updated
            )

            # Start any background tasks
            # self.background_task = asyncio.create_task(self.background_loop())

            logger.info("My Plugin initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize My Plugin: {e}")
            return False

    async def shutdown(self):
        """Shutdown the plugin."""
        try:
            # Cancel background tasks
            if self.background_task:
                self.background_task.cancel()
                try:
                    await self.background_task
                except asyncio.CancelledError:
                    pass

            # Unregister hooks
            await self.hook_manager.unregister_hook(
                'device.reading_updated', 
                self.on_device_reading_updated
            )

            logger.info("My Plugin shutdown complete")

        except Exception as e:
            logger.error(f"Error during My Plugin shutdown: {e}")

    async def on_device_reading_updated(self, device_data: Dict[str, Any]):
        """Handle device reading updates."""
        try:
            device_ip = device_data.get('ip')
            device_name = device_data.get('alias', f'Device {device_ip}')
            current_power = device_data.get('current_power_w', 0)

            # Add your plugin logic here
            logger.debug(f"Processing update for {device_name}: {current_power}W")

            # Example: Do something when power exceeds a threshold
            if current_power > 100:
                await self.handle_high_power(device_data)

        except Exception as e:
            logger.error(f"Error handling device reading update: {e}")

    async def handle_high_power(self, device_data: Dict[str, Any]):
        """Example method to handle high power consumption."""
        device_ip = device_data.get('ip')
        logger.info(f"High power detected for device {device_ip}")

        # Example: Send a notification
        await self.hook_manager.emit_hook('notification.send', {
            'type': 'high_power',
            'severity': 'info',
            'title': 'High Power Usage',
            'message': f"Device {device_ip} is using high power",
            'device_ip': device_ip
        })

    async def background_loop(self):
        """Example background task loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Add your background processing here
                logger.debug("Background task running")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background loop: {e}")
                await asyncio.sleep(10)

    async def get_status(self) -> Dict[str, Any]:
        """Get plugin status information."""
        return {
            'example_setting': self.example_setting,
            'background_task_active': (
                self.background_task is not None and 
                not self.background_task.done()
            ),
            'initialized': True
        }

    async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plugin-specific actions."""
        if action == 'update_setting':
            new_value = params.get('value')
            if new_value:
                self.example_setting = new_value
                # Optionally save to config
                await self.update_config({'example_setting': new_value})
                return {
                    'status': 'success', 
                    'message': f'Setting updated to: {new_value}'
                }
            else:
                return {'status': 'error', 'message': 'Value parameter required'}

        elif action == 'get_data':
            # Example action to retrieve some data
            return {
                'status': 'success',
                'data': {
                    'current_setting': self.example_setting,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }

        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    # Add your own custom methods here
    async def custom_method(self, param1: str, param2: int) -> bool:
        """Example of a custom method."""
        try:
            # Your custom logic here
            logger.info(f"Custom method called with {param1}, {param2}")
            return True
        except Exception as e:
            logger.error(f"Error in custom method: {e}")
            return False