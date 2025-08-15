"""
WebSocket real-time updates manager for Kasa Monitor
Handles real-time device status, energy data, and notifications
"""

import json
import logging
import asyncio
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""

    def __init__(self):
        # Active connections by client ID
        self.active_connections: Dict[str, WebSocket] = {}

        # Subscription management
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # topic -> set of client_ids
        self.client_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # client_id -> set of topics

        # Authentication tracking
        self.authenticated_clients: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self.stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "broadcasts_sent": 0,
            "errors": 0,
        }

    async def connect(self, websocket: WebSocket, client_id: str, user_info: Optional[Dict] = None):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.stats["total_connections"] += 1

        if user_info:
            self.authenticated_clients[client_id] = user_info

        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )

        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # Clean up subscriptions
        if client_id in self.client_subscriptions:
            for topic in self.client_subscriptions[client_id]:
                self.subscriptions[topic].discard(client_id)
            del self.client_subscriptions[client_id]

        # Clean up authentication
        if client_id in self.authenticated_clients:
            del self.authenticated_clients[client_id]

        logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
                self.stats["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.stats["errors"] += 1
                self.disconnect(client_id)

    async def broadcast(self, message: Dict[str, Any], topic: Optional[str] = None):
        """Broadcast a message to all connected clients or topic subscribers"""
        if topic:
            # Send to topic subscribers only
            recipients = self.subscriptions.get(topic, set())
        else:
            # Send to all connected clients
            recipients = set(self.active_connections.keys())

        if not recipients:
            return

        # Send to all recipients
        disconnected = []
        for client_id in recipients:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        self.stats["broadcasts_sent"] += 1
        self.stats["messages_sent"] += len(recipients) - len(disconnected)

    async def subscribe(self, client_id: str, topic: str):
        """Subscribe a client to a topic"""
        self.subscriptions[topic].add(client_id)
        self.client_subscriptions[client_id].add(topic)

        await self.send_personal_message(
            {
                "type": "subscription",
                "action": "subscribed",
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )

        logger.debug(f"Client {client_id} subscribed to {topic}")

    async def unsubscribe(self, client_id: str, topic: str):
        """Unsubscribe a client from a topic"""
        self.subscriptions[topic].discard(client_id)
        self.client_subscriptions[client_id].discard(topic)

        await self.send_personal_message(
            {
                "type": "subscription",
                "action": "unsubscribed",
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )

        logger.debug(f"Client {client_id} unsubscribed from {topic}")

    def get_client_count(self) -> int:
        """Get number of connected clients"""
        return len(self.active_connections)

    def get_topic_subscribers(self, topic: str) -> int:
        """Get number of subscribers for a topic"""
        return len(self.subscriptions.get(topic, set()))

    def get_statistics(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            **self.stats,
            "active_connections": len(self.active_connections),
            "authenticated_clients": len(self.authenticated_clients),
            "topics": len(self.subscriptions),
            "topic_details": {topic: len(subscribers) for topic, subscribers in self.subscriptions.items()},
        }


class WebSocketEventHandler:
    """Handles WebSocket events and message routing"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.handlers = {
            "subscribe": self.handle_subscribe,
            "unsubscribe": self.handle_unsubscribe,
            "device_command": self.handle_device_command,
            "get_status": self.handle_get_status,
            "ping": self.handle_ping,
        }

    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        """Route incoming message to appropriate handler"""
        message_type = message.get("type")

        if message_type not in self.handlers:
            await self.manager.send_personal_message(
                {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now().isoformat(),
                },
                client_id,
            )
            return

        try:
            handler = self.handlers[message_type]
            await handler(client_id, message)
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self.manager.send_personal_message(
                {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
                client_id,
            )

    async def handle_subscribe(self, client_id: str, message: Dict[str, Any]):
        """Handle subscription request"""
        topics = message.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]

        for topic in topics:
            await self.manager.subscribe(client_id, topic)

    async def handle_unsubscribe(self, client_id: str, message: Dict[str, Any]):
        """Handle unsubscription request"""
        topics = message.get("topics", [])
        if isinstance(topics, str):
            topics = [topics]

        for topic in topics:
            await self.manager.unsubscribe(client_id, topic)

    async def handle_device_command(self, client_id: str, message: Dict[str, Any]):
        """Handle device command"""
        device_id = message.get("device_id")
        command = message.get("command")
        params = message.get("params", {})

        # Check authorization
        user_info = self.manager.authenticated_clients.get(client_id)
        if not user_info or not user_info.get("is_authenticated"):
            await self.manager.send_personal_message(
                {
                    "type": "error",
                    "message": "Unauthorized",
                    "timestamp": datetime.now().isoformat(),
                },
                client_id,
            )
            return

        # Process device command (integrate with device manager)
        # This is a placeholder - integrate with actual device control
        result = {
            "type": "device_command_response",
            "device_id": device_id,
            "command": command,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
        }

        await self.manager.send_personal_message(result, client_id)

    async def handle_get_status(self, client_id: str, message: Dict[str, Any]):
        """Handle status request"""
        status = self.manager.get_statistics()
        await self.manager.send_personal_message(
            {
                "type": "status_response",
                "status": status,
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )

    async def handle_ping(self, client_id: str, message: Dict[str, Any]):
        """Handle ping message"""
        await self.manager.send_personal_message({"type": "pong", "timestamp": datetime.now().isoformat()}, client_id)


class WebSocketNotifier:
    """Sends notifications through WebSocket"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def notify_device_status(self, device_id: str, status: Dict[str, Any]):
        """Notify about device status change"""
        message = {
            "type": "device_status",
            "device_id": device_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast(message, topic=f"device:{device_id}")
        await self.manager.broadcast(message, topic="devices:all")

    async def notify_energy_data(self, device_id: str, energy_data: Dict[str, Any]):
        """Notify about new energy data"""
        message = {
            "type": "energy_data",
            "device_id": device_id,
            "data": energy_data,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast(message, topic=f"energy:{device_id}")
        await self.manager.broadcast(message, topic="energy:all")

    async def notify_alert(self, alert: Dict[str, Any]):
        """Notify about alert"""
        message = {
            "type": "alert",
            "alert": alert,
            "timestamp": datetime.now().isoformat(),
        }

        # Send to specific device topic if device_id present
        if "device_id" in alert:
            await self.manager.broadcast(message, topic=f"alerts:{alert['device_id']}")

        # Always send to all alerts topic
        await self.manager.broadcast(message, topic="alerts:all")

    async def notify_system_event(self, event: Dict[str, Any]):
        """Notify about system event"""
        message = {
            "type": "system_event",
            "event": event,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast(message, topic="system:events")

    async def notify_schedule_trigger(self, schedule: Dict[str, Any]):
        """Notify about schedule trigger"""
        message = {
            "type": "schedule_trigger",
            "schedule": schedule,
            "timestamp": datetime.now().isoformat(),
        }

        if "device_id" in schedule:
            await self.manager.broadcast(message, topic=f"schedules:{schedule['device_id']}")

        await self.manager.broadcast(message, topic="schedules:all")


# Global instances
manager = ConnectionManager()
event_handler = WebSocketEventHandler(manager)
notifier = WebSocketNotifier(manager)


# WebSocket authentication
async def get_current_user_ws(websocket: WebSocket, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Authenticate WebSocket connection"""
    if not token:
        # Check for token in query params
        token = websocket.query_params.get("token")

    if not token:
        return None

    try:
        # Decode JWT token (integrate with your auth system)
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "is_authenticated": True,
            "is_admin": payload.get("is_admin", False),
        }
    except jwt.InvalidTokenError:
        return None


# WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket, client_id: str, token: Optional[str] = None):
    """Main WebSocket endpoint"""
    # Authenticate if token provided
    user_info = await get_current_user_ws(websocket, token)

    # Connect client
    await manager.connect(websocket, client_id, user_info)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            manager.stats["messages_received"] += 1

            try:
                message = json.loads(data)
                await event_handler.handle_message(client_id, message)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                        "timestamp": datetime.now().isoformat(),
                    },
                    client_id,
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)


# Background task for periodic updates
async def websocket_background_task():
    """Background task for sending periodic updates"""
    while True:
        try:
            # Send heartbeat to all connected clients
            await manager.broadcast(
                {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                    "clients": manager.get_client_count(),
                },
                topic="system:heartbeat",
            )

            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
        except Exception as e:
            logger.error(f"WebSocket background task error: {e}")
            await asyncio.sleep(5)
