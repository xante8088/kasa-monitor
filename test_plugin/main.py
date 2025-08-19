"""Test Plugin for Kasa Monitor

A simple plugin that demonstrates the plugin system functionality.
"""

import asyncio
import logging
from typing import Any, Dict

from backend.plugin_system import Plugin

logger = logging.getLogger(__name__)


class TestPlugin(Plugin):
    """Test plugin implementation."""

    def __init__(self, context):
        """Initialize the test plugin."""
        super().__init__(context)
        self.config = {}
        self.device_count = 0
        
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            self.config = self.context.get_config()
            logger.info(f"Test plugin initialized with config: {self.config}")
            
            # Register for hooks
            self.context.call_hook("register_hook", "device_discovered", self.on_device_discovered)
            self.context.call_hook("register_hook", "data_collected", self.on_data_collected)
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize test plugin: {e}")
            return False

    async def start(self) -> bool:
        """Start the plugin."""
        try:
            if self.config.get("enabled", True):
                logger.info("Test plugin started successfully")
                self.context.log("info", "Test plugin is now active")
                return True
            else:
                logger.info("Test plugin is disabled in configuration")
                return False
        except Exception as e:
            logger.error(f"Failed to start test plugin: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the plugin."""
        try:
            logger.info("Test plugin stopped")
            self.context.log("info", "Test plugin has been stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop test plugin: {e}")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """Get plugin status information."""
        return {
            "status": "running" if self.config.get("enabled", True) else "disabled",
            "devices_discovered": self.device_count,
            "log_level": self.config.get("log_level", "info"),
            "notification_email": self.config.get("notification_email", "Not configured"),
            "uptime": "Active since initialization"
        }

    async def get_metrics(self) -> Dict[str, Any]:
        """Get plugin metrics."""
        return {
            "devices_seen": self.device_count,
            "hooks_registered": 2,
            "memory_usage": "Low",
            "cpu_usage": "Minimal"
        }

    def on_device_discovered(self, device_info: Dict[str, Any]):
        """Handle device discovery events."""
        self.device_count += 1
        device_name = device_info.get("alias", "Unknown Device")
        device_ip = device_info.get("ip", "Unknown IP")
        
        log_level = self.config.get("log_level", "info")
        if log_level in ["debug", "info"]:
            self.context.log("info", f"Device discovered: {device_name} ({device_ip})")
            logger.info(f"Test plugin: Device discovered - {device_name} at {device_ip}")

    def on_data_collected(self, device_ip: str, data: Dict[str, Any]):
        """Handle data collection events."""
        log_level = self.config.get("log_level", "info")
        if log_level == "debug":
            power = data.get("current_power_w", 0)
            self.context.log("debug", f"Data collected from {device_ip}: {power}W")

    async def configure(self, new_config: Dict[str, Any]) -> bool:
        """Update plugin configuration."""
        try:
            # Validate configuration
            if "enabled" in new_config and not isinstance(new_config["enabled"], bool):
                raise ValueError("'enabled' must be a boolean")
            
            if "log_level" in new_config and new_config["log_level"] not in ["debug", "info", "warning", "error"]:
                raise ValueError("'log_level' must be one of: debug, info, warning, error")
            
            # Update configuration
            self.config.update(new_config)
            self.context.save_config(self.config)
            
            logger.info(f"Test plugin configuration updated: {new_config}")
            self.context.log("info", "Configuration updated successfully")
            
            return True
        except Exception as e:
            logger.error(f"Failed to update test plugin configuration: {e}")
            self.context.log("error", f"Configuration update failed: {e}")
            return False


# Plugin entry point
def create_plugin(context):
    """Create and return the plugin instance."""
    return TestPlugin(context)