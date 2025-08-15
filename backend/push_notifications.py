"""Push notification system for mobile and browser notifications.

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
import base64
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jose import jwt


class PushPlatform(Enum):
    """Push notification platforms."""

    WEB = "web"
    IOS = "ios"
    ANDROID = "android"
    WINDOWS = "windows"


class PushPriority(Enum):
    """Push notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(Enum):
    """Notification types."""

    ALERT = "alert"
    MESSAGE = "message"
    UPDATE = "update"
    REMINDER = "reminder"
    PROMOTIONAL = "promotional"


@dataclass
class PushSubscription:
    """Push notification subscription."""

    user_id: int
    platform: PushPlatform
    device_token: str
    device_name: Optional[str] = None
    endpoint: Optional[str] = None
    p256dh: Optional[str] = None
    auth: Optional[str] = None
    topics: Optional[List[str]] = None
    enabled: bool = True
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["platform"] = self.platform.value
        data["topics"] = self.topics or []
        return data


@dataclass
class PushNotification:
    """Push notification message."""

    title: str
    body: str
    icon: Optional[str] = None
    badge: Optional[str] = None
    image: Optional[str] = None
    sound: Optional[str] = None
    tag: Optional[str] = None
    data: Optional[Dict] = None
    actions: Optional[List[Dict]] = None
    priority: PushPriority = PushPriority.NORMAL
    ttl: int = 86400  # 24 hours
    topic: Optional[str] = None
    collapse_key: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["priority"] = self.priority.value
        return {k: v for k, v in data.items() if v is not None}


class WebPushService:
    """Web Push notification service."""

    def __init__(self, vapid_private_key: str, vapid_public_key: str, vapid_email: str):
        """Initialize Web Push service.

        Args:
            vapid_private_key: VAPID private key
            vapid_public_key: VAPID public key
            vapid_email: Contact email for VAPID
        """
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_email = vapid_email

    async def send(
        self, subscription: PushSubscription, notification: PushNotification
    ) -> bool:
        """Send Web Push notification.

        Args:
            subscription: Push subscription
            notification: Notification to send

        Returns:
            True if sent successfully
        """
        try:
            # Create JWT token for VAPID
            vapid_token = self._create_vapid_token(subscription.endpoint)

            # Prepare headers
            headers = {
                "Authorization": f"vapid t={vapid_token}, k={self.vapid_public_key}",
                "Content-Type": "application/json",
                "TTL": str(notification.ttl),
                "Urgency": self._get_urgency(notification.priority),
            }

            if notification.topic:
                headers["Topic"] = notification.topic

            # Encrypt payload if keys are provided
            if subscription.p256dh and subscription.auth:
                payload = self._encrypt_payload(
                    json.dumps(notification.to_dict()),
                    subscription.p256dh,
                    subscription.auth,
                )
                headers["Content-Encoding"] = "aes128gcm"
            else:
                payload = json.dumps(notification.to_dict())

            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    subscription.endpoint, data=payload, headers=headers
                ) as response:
                    return response.status in [200, 201, 204]

        except Exception:
            return False

    def _create_vapid_token(self, endpoint: str) -> str:
        """Create VAPID JWT token.

        Args:
            endpoint: Push endpoint URL

        Returns:
            JWT token
        """
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        claims = {
            "aud": origin,
            "exp": int(time.time()) + 12 * 60 * 60,  # 12 hours
            "sub": f"mailto:{self.vapid_email}",
        }

        token = jwt.encode(claims, self.vapid_private_key, algorithm="ES256")

        return token

    def _encrypt_payload(self, payload: str, p256dh: str, auth: str) -> bytes:
        """Encrypt payload for Web Push.

        Args:
            payload: Payload to encrypt
            p256dh: Client public key
            auth: Client auth secret

        Returns:
            Encrypted payload
        """
        # TODO: Implement Web Push encryption
        # This requires py-vapid or similar library
        return payload.encode()

    def _get_urgency(self, priority: PushPriority) -> str:
        """Convert priority to urgency header.

        Args:
            priority: Push priority

        Returns:
            Urgency value
        """
        mapping = {
            PushPriority.LOW: "low",
            PushPriority.NORMAL: "normal",
            PushPriority.HIGH: "high",
            PushPriority.URGENT: "very-high",
        }
        return mapping.get(priority, "normal")


class FCMService:
    """Firebase Cloud Messaging service for Android/iOS."""

    def __init__(self, service_account_path: str):
        """Initialize FCM service.

        Args:
            service_account_path: Path to Firebase service account JSON
        """
        self.service_account_path = service_account_path
        self.access_token = None
        self.token_expiry = None
        self.fcm_url = (
            "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        )

    async def send(
        self, subscription: PushSubscription, notification: PushNotification
    ) -> bool:
        """Send FCM notification.

        Args:
            subscription: Push subscription
            notification: Notification to send

        Returns:
            True if sent successfully
        """
        try:
            # Get access token
            access_token = await self._get_access_token()

            # Prepare message
            message = {
                "message": {
                    "token": subscription.device_token,
                    "notification": {
                        "title": notification.title,
                        "body": notification.body,
                    },
                }
            }

            if notification.icon:
                message["message"]["notification"]["icon"] = notification.icon

            if notification.image:
                message["message"]["notification"]["image"] = notification.image

            if notification.data:
                message["message"]["data"] = {
                    k: str(v) for k, v in notification.data.items()
                }

            # Platform-specific config
            if subscription.platform == PushPlatform.ANDROID:
                message["message"]["android"] = {
                    "priority": self._get_android_priority(notification.priority),
                    "ttl": f"{notification.ttl}s",
                }

                if notification.collapse_key:
                    message["message"]["android"][
                        "collapse_key"
                    ] = notification.collapse_key

            elif subscription.platform == PushPlatform.IOS:
                message["message"]["apns"] = {
                    "headers": {
                        "apns-priority": self._get_apns_priority(notification.priority)
                    },
                    "payload": {
                        "aps": {
                            "alert": {
                                "title": notification.title,
                                "body": notification.body,
                            }
                        }
                    },
                }

                if notification.badge:
                    message["message"]["apns"]["payload"]["aps"][
                        "badge"
                    ] = notification.badge

                if notification.sound:
                    message["message"]["apns"]["payload"]["aps"][
                        "sound"
                    ] = notification.sound

            # Send request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.fcm_url.format(project_id=self._get_project_id()),
                    json=message,
                    headers=headers,
                ) as response:
                    return response.status == 200

        except Exception:
            return False

    async def _get_access_token(self) -> str:
        """Get FCM access token.

        Returns:
            Access token
        """
        # TODO: Implement OAuth2 token generation for FCM
        # This requires google-auth library
        return "mock_token"

    def _get_project_id(self) -> str:
        """Get Firebase project ID.

        Returns:
            Project ID
        """
        with open(self.service_account_path) as f:
            service_account = json.load(f)
        return service_account.get("project_id", "")

    def _get_android_priority(self, priority: PushPriority) -> str:
        """Convert to Android priority.

        Args:
            priority: Push priority

        Returns:
            Android priority
        """
        if priority in [PushPriority.HIGH, PushPriority.URGENT]:
            return "HIGH"
        return "NORMAL"

    def _get_apns_priority(self, priority: PushPriority) -> str:
        """Convert to APNS priority.

        Args:
            priority: Push priority

        Returns:
            APNS priority
        """
        if priority in [PushPriority.HIGH, PushPriority.URGENT]:
            return "10"
        return "5"


class PushNotificationManager:
    """Main push notification management system."""

    def __init__(
        self,
        db_path: str = "kasa_monitor.db",
        vapid_keys: Optional[Dict] = None,
        fcm_config: Optional[str] = None,
    ):
        """Initialize push notification manager.

        Args:
            db_path: Path to database
            vapid_keys: VAPID keys for Web Push
            fcm_config: Path to FCM service account
        """
        self.db_path = db_path

        # Initialize services
        self.web_push = None
        if vapid_keys:
            self.web_push = WebPushService(
                vapid_keys["private_key"], vapid_keys["public_key"], vapid_keys["email"]
            )

        self.fcm = None
        if fcm_config:
            self.fcm = FCMService(fcm_config)

        self._init_database()

    def _init_database(self):
        """Initialize push notification tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Push subscriptions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                device_token TEXT NOT NULL,
                device_name TEXT,
                endpoint TEXT,
                p256dh TEXT,
                auth TEXT,
                topics TEXT,
                enabled BOOLEAN DEFAULT 1,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, platform, device_token)
            )
        """
        )

        # Push notifications table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS push_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                data TEXT,
                priority TEXT DEFAULT 'normal',
                topic TEXT,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP,
                delivered_at TIMESTAMP,
                read_at TIMESTAMP,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Topic subscriptions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS topic_subscriptions (
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, topic),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Push metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS push_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                platform TEXT NOT NULL,
                total_sent INTEGER DEFAULT 0,
                total_delivered INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0,
                total_opened INTEGER DEFAULT 0,
                UNIQUE(date, platform)
            )
        """
        )

        conn.commit()
        conn.close()

    def register_device(self, subscription: PushSubscription) -> bool:
        """Register device for push notifications.

        Args:
            subscription: Push subscription

        Returns:
            True if registered successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO push_subscriptions 
                (user_id, platform, device_token, device_name, endpoint, 
                 p256dh, auth, topics, enabled, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    subscription.user_id,
                    subscription.platform.value,
                    subscription.device_token,
                    subscription.device_name,
                    subscription.endpoint,
                    subscription.p256dh,
                    subscription.auth,
                    json.dumps(subscription.topics) if subscription.topics else None,
                    subscription.enabled,
                    (
                        json.dumps(subscription.metadata)
                        if subscription.metadata
                        else None
                    ),
                ),
            )

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def unregister_device(self, user_id: int, device_token: str) -> bool:
        """Unregister device from push notifications.

        Args:
            user_id: User ID
            device_token: Device token

        Returns:
            True if unregistered successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM push_subscriptions 
            WHERE user_id = ? AND device_token = ?
        """,
            (user_id, device_token),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def subscribe_to_topic(self, user_id: int, topic: str) -> bool:
        """Subscribe user to topic.

        Args:
            user_id: User ID
            topic: Topic name

        Returns:
            True if subscribed successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Add to topic subscriptions
            cursor.execute(
                """
                INSERT OR IGNORE INTO topic_subscriptions (user_id, topic)
                VALUES (?, ?)
            """,
                (user_id, topic),
            )

            # Update device subscriptions
            cursor.execute(
                """
                UPDATE push_subscriptions 
                SET topics = json_insert(
                    COALESCE(topics, '[]'), 
                    '$[#]', 
                    ?
                )
                WHERE user_id = ?
            """,
                (topic, user_id),
            )

            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def unsubscribe_from_topic(self, user_id: int, topic: str) -> bool:
        """Unsubscribe user from topic.

        Args:
            user_id: User ID
            topic: Topic name

        Returns:
            True if unsubscribed successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Remove from topic subscriptions
        cursor.execute(
            """
            DELETE FROM topic_subscriptions 
            WHERE user_id = ? AND topic = ?
        """,
            (user_id, topic),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    async def send_to_user(self, user_id: int, notification: PushNotification) -> int:
        """Send notification to all user's devices.

        Args:
            user_id: User ID
            notification: Notification to send

        Returns:
            Number of devices notified
        """
        # Get user's subscriptions
        subscriptions = self._get_user_subscriptions(user_id)

        sent_count = 0
        for sub in subscriptions:
            if await self._send_notification(sub, notification):
                sent_count += 1
                self._record_notification(user_id, sub.platform, notification, "sent")
            else:
                self._record_notification(user_id, sub.platform, notification, "failed")

        return sent_count

    async def send_to_topic(self, topic: str, notification: PushNotification) -> int:
        """Send notification to topic subscribers.

        Args:
            topic: Topic name
            notification: Notification to send

        Returns:
            Number of users notified
        """
        # Get topic subscribers
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT user_id FROM topic_subscriptions 
            WHERE topic = ?
        """,
            (topic,),
        )

        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Send to each user
        sent_count = 0
        for user_id in user_ids:
            count = await self.send_to_user(user_id, notification)
            if count > 0:
                sent_count += 1

        return sent_count

    async def broadcast(
        self, notification: PushNotification, platform: Optional[PushPlatform] = None
    ) -> int:
        """Broadcast notification to all users.

        Args:
            notification: Notification to send
            platform: Optional platform filter

        Returns:
            Number of devices notified
        """
        # Get all subscriptions
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT DISTINCT user_id FROM push_subscriptions WHERE enabled = 1"
        params = []

        if platform:
            query += " AND platform = ?"
            params.append(platform.value)

        cursor.execute(query, params)
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Send to each user
        sent_count = 0
        for user_id in user_ids:
            count = await self.send_to_user(user_id, notification)
            sent_count += count

        return sent_count

    async def _send_notification(
        self, subscription: PushSubscription, notification: PushNotification
    ) -> bool:
        """Send notification to specific subscription.

        Args:
            subscription: Push subscription
            notification: Notification to send

        Returns:
            True if sent successfully
        """
        if subscription.platform == PushPlatform.WEB:
            if self.web_push:
                return await self.web_push.send(subscription, notification)

        elif subscription.platform in [PushPlatform.IOS, PushPlatform.ANDROID]:
            if self.fcm:
                return await self.fcm.send(subscription, notification)

        return False

    def _get_user_subscriptions(self, user_id: int) -> List[PushSubscription]:
        """Get user's push subscriptions.

        Args:
            user_id: User ID

        Returns:
            List of subscriptions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT platform, device_token, device_name, endpoint, 
                   p256dh, auth, topics, metadata
            FROM push_subscriptions
            WHERE user_id = ? AND enabled = 1
        """,
            (user_id,),
        )

        subscriptions = []
        for row in cursor.fetchall():
            sub = PushSubscription(
                user_id=user_id,
                platform=PushPlatform(row[0]),
                device_token=row[1],
                device_name=row[2],
                endpoint=row[3],
                p256dh=row[4],
                auth=row[5],
                topics=json.loads(row[6]) if row[6] else None,
                metadata=json.loads(row[7]) if row[7] else None,
            )
            subscriptions.append(sub)

        conn.close()
        return subscriptions

    def _record_notification(
        self,
        user_id: int,
        platform: PushPlatform,
        notification: PushNotification,
        status: str,
    ):
        """Record notification in database.

        Args:
            user_id: User ID
            platform: Platform
            notification: Notification sent
            status: Delivery status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Record notification
        cursor.execute(
            """
            INSERT INTO push_notifications 
            (user_id, platform, title, body, data, priority, topic, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                platform.value,
                notification.title,
                notification.body,
                json.dumps(notification.data) if notification.data else None,
                notification.priority.value,
                notification.topic,
                status,
            ),
        )

        if status == "sent":
            cursor.execute(
                """
                UPDATE push_notifications 
                SET sent_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """,
                (cursor.lastrowid,),
            )

        # Update metrics
        today = datetime.now().date()

        cursor.execute(
            """
            INSERT OR IGNORE INTO push_metrics 
            (date, platform, total_sent, total_delivered, total_failed)
            VALUES (?, ?, 0, 0, 0)
        """,
            (today, platform.value),
        )

        if status == "sent":
            cursor.execute(
                """
                UPDATE push_metrics 
                SET total_sent = total_sent + 1
                WHERE date = ? AND platform = ?
            """,
                (today, platform.value),
            )
        elif status == "failed":
            cursor.execute(
                """
                UPDATE push_metrics 
                SET total_failed = total_failed + 1
                WHERE date = ? AND platform = ?
            """,
                (today, platform.value),
            )

        conn.commit()
        conn.close()

    def get_metrics(
        self, days: int = 30, platform: Optional[PushPlatform] = None
    ) -> Dict:
        """Get push notification metrics.

        Args:
            days: Number of days to include
            platform: Optional platform filter

        Returns:
            Push metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_date = datetime.now().date() - timedelta(days=days)

        query = """
            SELECT 
                SUM(total_sent) as sent,
                SUM(total_delivered) as delivered,
                SUM(total_failed) as failed,
                SUM(total_opened) as opened
            FROM push_metrics
            WHERE date >= ?
        """
        params = [start_date]

        if platform:
            query += " AND platform = ?"
            params.append(platform.value)

        cursor.execute(query, params)
        row = cursor.fetchone()

        metrics = {
            "total_sent": row[0] or 0,
            "total_delivered": row[1] or 0,
            "total_failed": row[2] or 0,
            "total_opened": row[3] or 0,
            "delivery_rate": ((row[1] or 0) / (row[0] or 1)) * 100,
            "open_rate": ((row[3] or 0) / (row[1] or 1)) * 100,
        }

        conn.close()
        return metrics
