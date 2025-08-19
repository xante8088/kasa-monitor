"""Slack Alerts Example Plugin.

This plugin sends device alerts and notifications to Slack channels
using webhook integration.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

from plugin_system import PluginBase

logger = logging.getLogger(__name__)


class SlackAlertsPlugin(PluginBase):
    """Example plugin that sends alerts to Slack."""

    def __init__(self):
        super().__init__()
        self.webhook_url = None
        self.channel = "#kasa-monitor"
        self.username = "Kasa Monitor"
        self.emoji = ":electric_plug:"
        self.alert_types = ["power_alert", "device_offline", "device_online"]
        self.session = None

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            # Load configuration
            config = await self.get_config()
            self.webhook_url = config.get('webhook_url')
            if not self.webhook_url:
                logger.error("Slack webhook URL not configured")
                return False

            self.channel = config.get('channel', '#kasa-monitor')
            self.username = config.get('username', 'Kasa Monitor')
            self.emoji = config.get('emoji', ':electric_plug:')
            self.alert_types = config.get('alert_types', [
                'power_alert', 'device_offline', 'device_online'
            ])

            # Create HTTP session
            self.session = aiohttp.ClientSession()

            # Register hooks
            await self.hook_manager.register_hook(
                'notification.send',
                self.on_notification_send
            )
            await self.hook_manager.register_hook(
                'device.status_changed',
                self.on_device_status_changed
            )
            await self.hook_manager.register_hook(
                'device.discovered',
                self.on_device_discovered
            )

            # Send startup notification
            await self.send_slack_message(
                "🟢 Kasa Monitor Slack integration started",
                color="good"
            )

            logger.info(f"Slack Alerts plugin initialized for channel: {self.channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Slack Alerts plugin: {e}")
            return False

    async def shutdown(self):
        """Shutdown the plugin."""
        try:
            # Send shutdown notification
            if self.session:
                await self.send_slack_message(
                    "🔴 Kasa Monitor Slack integration stopped",
                    color="danger"
                )

            # Unregister hooks
            await self.hook_manager.unregister_hook(
                'notification.send',
                self.on_notification_send
            )
            await self.hook_manager.unregister_hook(
                'device.status_changed',
                self.on_device_status_changed
            )
            await self.hook_manager.unregister_hook(
                'device.discovered',
                self.on_device_discovered
            )

            # Close HTTP session
            if self.session:
                await self.session.close()

            logger.info("Slack Alerts plugin shutdown complete")

        except Exception as e:
            logger.error(f"Error during Slack plugin shutdown: {e}")

    async def on_notification_send(self, notification: Dict[str, Any]):
        """Handle notification send events."""
        try:
            alert_type = notification.get('type')
            if alert_type not in self.alert_types:
                return

            title = notification.get('title', 'Kasa Monitor Alert')
            message = notification.get('message', '')
            severity = notification.get('severity', 'info')
            device_ip = notification.get('device_ip')

            # Map severity to Slack colors
            color_map = {
                'info': 'good',
                'warning': 'warning',
                'error': 'danger',
                'critical': 'danger'
            }
            color = color_map.get(severity, 'good')

            # Format message for Slack
            slack_text = f"*{title}*"
            if device_ip:
                slack_text += f"\\nDevice: `{device_ip}`"
            slack_text += f"\\n{message}"

            await self.send_slack_message(slack_text, color=color)

        except Exception as e:
            logger.error(f"Error handling notification: {e}")

    async def on_device_status_changed(self, device_data: Dict[str, Any]):
        """Handle device status change events."""
        try:
            device_ip = device_data.get('ip')
            device_name = device_data.get('alias', f'Device {device_ip}')
            is_online = device_data.get('is_online', True)
            previous_status = device_data.get('previous_status')

            # Only send alerts for actual status changes
            if previous_status is None:
                return

            if is_online and not previous_status:
                # Device came online
                if 'device_online' in self.alert_types:
                    await self.send_slack_message(
                        f"🟢 *Device Online*\\nDevice: {device_name} (`{device_ip}`)\\nStatus: Back online",
                        color="good"
                    )
            elif not is_online and previous_status:
                # Device went offline
                if 'device_offline' in self.alert_types:
                    await self.send_slack_message(
                        f"🔴 *Device Offline*\\nDevice: {device_name} (`{device_ip}`)\\nStatus: Disconnected",
                        color="danger"
                    )

        except Exception as e:
            logger.error(f"Error handling device status change: {e}")

    async def on_device_discovered(self, device_data: Dict[str, Any]):
        """Handle new device discovery events."""
        try:
            device_ip = device_data.get('ip')
            device_name = device_data.get('alias', f'Device {device_ip}')
            device_model = device_data.get('model', 'Unknown')

            await self.send_slack_message(
                f"🔍 *New Device Discovered*\\nName: {device_name}\\nIP: `{device_ip}`\\nModel: {device_model}",
                color="good"
            )

        except Exception as e:
            logger.error(f"Error handling device discovery: {e}")

    async def send_slack_message(self, text: str, color: str = "good", fields: Optional[List[Dict]] = None):
        """Send message to Slack via webhook."""
        if not self.session or not self.webhook_url:
            return

        try:
            # Create Slack message payload
            attachment = {
                "color": color,
                "text": text,
                "ts": int(datetime.now(timezone.utc).timestamp())
            }

            if fields:
                attachment["fields"] = fields

            payload = {
                "channel": self.channel,
                "username": self.username,
                "icon_emoji": self.emoji,
                "attachments": [attachment]
            }

            # Send to Slack
            async with self.session.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to send Slack message: {response.status}")
                else:
                    logger.debug("Slack message sent successfully")

        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get plugin status information."""
        return {
            'webhook_configured': bool(self.webhook_url),
            'channel': self.channel,
            'alert_types': self.alert_types,
            'session_active': self.session is not None and not self.session.closed
        }

    async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plugin-specific actions."""
        if action == 'test_message':
            message = params.get('message', 'Test message from Kasa Monitor')
            await self.send_slack_message(f"🧪 *Test Message*\\n{message}")
            return {'status': 'success', 'message': 'Test message sent to Slack'}

        elif action == 'update_config':
            # Update configuration
            new_config = params.get('config', {})
            await self.update_config(new_config)

            # Reload configuration
            config = await self.get_config()
            self.channel = config.get('channel', self.channel)
            self.username = config.get('username', self.username)
            self.emoji = config.get('emoji', self.emoji)
            self.alert_types = config.get('alert_types', self.alert_types)

            return {'status': 'success', 'message': 'Configuration updated'}

        elif action == 'send_summary':
            # Send device summary
            try:
                devices = await self.db_manager.get_monitored_devices()
                online_count = sum(1 for d in devices if d.get('is_online', True))
                total_count = len(devices)

                fields = [
                    {"title": "Total Devices", "value": str(total_count), "short": True},
                    {"title": "Online Devices", "value": str(online_count), "short": True}
                ]

                await self.send_slack_message(
                    "📊 *Device Status Summary*",
                    color="good",
                    fields=fields
                )

                return {'status': 'success', 'message': 'Device summary sent'}

            except Exception as e:
                return {'status': 'error', 'message': f'Failed to send summary: {str(e)}'}

        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}