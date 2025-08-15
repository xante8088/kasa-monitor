"""Webhook notification system with retry logic and security.

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
import hmac
import hashlib
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import backoff
from urllib.parse import urlparse
import threading
import queue as Queue


class WebhookEvent(Enum):
    """Webhook event types."""

    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    DEVICE_ERROR = "device.error"
    ENERGY_THRESHOLD = "energy.threshold"
    SYSTEM_ERROR = "system.error"
    USER_ACTION = "user.action"
    DATA_EXPORT = "data.export"
    BACKUP_COMPLETE = "backup.complete"
    CUSTOM = "custom"


class WebhookStatus(Enum):
    """Webhook delivery status."""

    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class WebhookAuthType(Enum):
    """Webhook authentication types."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    HMAC = "hmac"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"


@dataclass
class WebhookConfig:
    """Webhook configuration."""

    name: str
    url: str
    events: List[WebhookEvent]
    enabled: bool = True
    auth_type: WebhookAuthType = WebhookAuthType.NONE
    auth_config: Optional[Dict] = None
    headers: Optional[Dict[str, str]] = None
    retry_count: int = 3
    retry_delay: int = 5
    timeout: int = 30
    validate_ssl: bool = True
    secret: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["events"] = [e.value for e in self.events]
        data["auth_type"] = self.auth_type.value
        return data


@dataclass
class WebhookPayload:
    """Webhook payload structure."""

    event: WebhookEvent
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }


class WebhookManager:
    """Webhook management system."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize webhook manager.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.webhooks = {}
        self.delivery_queue = Queue.Queue()
        self.running = False
        self.worker_thread = None

        self._init_database()
        self._load_webhooks()

    def _init_database(self):
        """Initialize webhook tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Webhook configurations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                events TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                auth_type TEXT DEFAULT 'none',
                auth_config TEXT,
                headers TEXT,
                retry_count INTEGER DEFAULT 3,
                retry_delay INTEGER DEFAULT 5,
                timeout INTEGER DEFAULT 30,
                validate_ssl BOOLEAN DEFAULT 1,
                secret TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Webhook deliveries table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_id INTEGER NOT NULL,
                event TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                response_code INTEGER,
                response_body TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered_at TIMESTAMP,
                next_retry TIMESTAMP,
                FOREIGN KEY (webhook_id) REFERENCES webhook_configs(id)
            )
        """
        )

        # Webhook metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_id INTEGER NOT NULL,
                date DATE NOT NULL,
                total_deliveries INTEGER DEFAULT 0,
                successful_deliveries INTEGER DEFAULT 0,
                failed_deliveries INTEGER DEFAULT 0,
                avg_response_time REAL,
                FOREIGN KEY (webhook_id) REFERENCES webhook_configs(id),
                UNIQUE(webhook_id, date)
            )
        """
        )

        conn.commit()
        conn.close()

    def create_webhook(self, config: WebhookConfig) -> int:
        """Create webhook configuration.

        Args:
            config: Webhook configuration

        Returns:
            Webhook ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO webhook_configs 
            (name, url, events, enabled, auth_type, auth_config, headers,
             retry_count, retry_delay, timeout, validate_ssl, secret, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                config.name,
                config.url,
                json.dumps([e.value for e in config.events]),
                config.enabled,
                config.auth_type.value,
                json.dumps(config.auth_config) if config.auth_config else None,
                json.dumps(config.headers) if config.headers else None,
                config.retry_count,
                config.retry_delay,
                config.timeout,
                config.validate_ssl,
                config.secret,
                json.dumps(config.metadata) if config.metadata else None,
            ),
        )

        webhook_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Add to in-memory store
        self.webhooks[webhook_id] = config

        return webhook_id

    def update_webhook(self, webhook_id: int, updates: Dict) -> bool:
        """Update webhook configuration.

        Args:
            webhook_id: Webhook ID
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build update query
        fields = []
        values = []

        for key, value in updates.items():
            fields.append(f"{key} = ?")
            if key == "events":
                values.append(
                    json.dumps([e.value if isinstance(e, Enum) else e for e in value])
                )
            elif key in ["auth_config", "headers", "metadata"]:
                values.append(json.dumps(value) if value else None)
            elif key == "auth_type":
                values.append(value.value if isinstance(value, Enum) else value)
            else:
                values.append(value)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(webhook_id)

        query = f"UPDATE webhook_configs SET {', '.join(fields)} WHERE id = ?"

        cursor.execute(query, values)
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        # Reload webhooks
        if success:
            self._load_webhooks()

        return success

    def delete_webhook(self, webhook_id: int) -> bool:
        """Delete webhook configuration.

        Args:
            webhook_id: Webhook ID

        Returns:
            True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM webhook_configs WHERE id = ?", (webhook_id,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()

        # Remove from in-memory store
        if success and webhook_id in self.webhooks:
            del self.webhooks[webhook_id]

        return success

    def trigger(
        self, event: WebhookEvent, data: Dict[str, Any], metadata: Optional[Dict] = None
    ):
        """Trigger webhook for event.

        Args:
            event: Event type
            data: Event data
            metadata: Optional metadata
        """
        payload = WebhookPayload(
            event=event, timestamp=datetime.now(), data=data, metadata=metadata
        )

        # Find matching webhooks
        for webhook_id, config in self.webhooks.items():
            if not config.enabled:
                continue

            if event in config.events or WebhookEvent.CUSTOM in config.events:
                # Queue delivery
                self._queue_delivery(webhook_id, payload)

    async def trigger_async(
        self, event: WebhookEvent, data: Dict[str, Any], metadata: Optional[Dict] = None
    ):
        """Trigger webhook asynchronously.

        Args:
            event: Event type
            data: Event data
            metadata: Optional metadata
        """
        payload = WebhookPayload(
            event=event, timestamp=datetime.now(), data=data, metadata=metadata
        )

        tasks = []
        for webhook_id, config in self.webhooks.items():
            if not config.enabled:
                continue

            if event in config.events or WebhookEvent.CUSTOM in config.events:
                task = self._deliver_async(webhook_id, config, payload)
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def start_worker(self):
        """Start background delivery worker."""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop_worker(self):
        """Stop background delivery worker."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def _worker_loop(self):
        """Background worker loop."""
        while self.running:
            try:
                # Get delivery from queue
                delivery = self.delivery_queue.get(timeout=1)
                webhook_id, payload = delivery

                # Get webhook config
                config = self.webhooks.get(webhook_id)
                if config:
                    # Deliver webhook
                    asyncio.run(self._deliver_async(webhook_id, config, payload))

            except Queue.Empty:
                continue
            except Exception:
                continue

    def _queue_delivery(self, webhook_id: int, payload: WebhookPayload):
        """Queue webhook delivery.

        Args:
            webhook_id: Webhook ID
            payload: Webhook payload
        """
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO webhook_deliveries 
            (webhook_id, event, payload, status)
            VALUES (?, ?, ?, 'pending')
        """,
            (webhook_id, payload.event.value, json.dumps(payload.to_dict())),
        )

        delivery_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Add to queue
        self.delivery_queue.put((webhook_id, payload))

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60,
    )
    async def _deliver_async(
        self, webhook_id: int, config: WebhookConfig, payload: WebhookPayload
    ):
        """Deliver webhook asynchronously with retry.

        Args:
            webhook_id: Webhook ID
            config: Webhook configuration
            payload: Webhook payload
        """
        # Prepare headers
        headers = config.headers.copy() if config.headers else {}
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "KasaMonitor/1.0"
        headers["X-Event-Type"] = payload.event.value
        headers["X-Event-Timestamp"] = payload.timestamp.isoformat()

        # Add authentication
        headers = self._add_authentication(headers, config, payload)

        # Add signature if secret is configured
        if config.secret:
            signature = self._generate_signature(config.secret, payload)
            headers["X-Signature"] = signature

        # Prepare request
        timeout = aiohttp.ClientTimeout(total=config.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                start_time = time.time()

                async with session.post(
                    config.url,
                    json=payload.to_dict(),
                    headers=headers,
                    ssl=config.validate_ssl,
                ) as response:
                    response_time = time.time() - start_time
                    response_body = await response.text()

                    # Record delivery
                    self._record_delivery(
                        webhook_id=webhook_id,
                        event=payload.event,
                        status=(
                            WebhookStatus.SUCCESS
                            if response.status < 400
                            else WebhookStatus.FAILED
                        ),
                        response_code=response.status,
                        response_body=response_body,
                        response_time=response_time,
                    )

                    if response.status >= 400:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                        )

            except Exception as e:
                # Record failure
                self._record_delivery(
                    webhook_id=webhook_id,
                    event=payload.event,
                    status=WebhookStatus.FAILED,
                    error_message=str(e),
                )
                raise

    def _add_authentication(
        self, headers: Dict, config: WebhookConfig, payload: WebhookPayload
    ) -> Dict:
        """Add authentication to headers.

        Args:
            headers: Request headers
            config: Webhook configuration
            payload: Webhook payload

        Returns:
            Updated headers
        """
        if config.auth_type == WebhookAuthType.BASIC:
            if config.auth_config:
                username = config.auth_config.get("username", "")
                password = config.auth_config.get("password", "")
                auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth_str}"

        elif config.auth_type == WebhookAuthType.BEARER:
            if config.auth_config:
                token = config.auth_config.get("token", "")
                headers["Authorization"] = f"Bearer {token}"

        elif config.auth_type == WebhookAuthType.API_KEY:
            if config.auth_config:
                key_name = config.auth_config.get("key_name", "X-API-Key")
                key_value = config.auth_config.get("key_value", "")
                headers[key_name] = key_value

        elif config.auth_type == WebhookAuthType.OAUTH2:
            # TODO: Implement OAuth2 flow
            pass

        return headers

    def _generate_signature(self, secret: str, payload: WebhookPayload) -> str:
        """Generate HMAC signature for payload.

        Args:
            secret: Webhook secret
            payload: Webhook payload

        Returns:
            HMAC signature
        """
        payload_json = json.dumps(payload.to_dict(), sort_keys=True)
        signature = hmac.new(
            secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def _record_delivery(
        self,
        webhook_id: int,
        event: WebhookEvent,
        status: WebhookStatus,
        response_code: Optional[int] = None,
        response_body: Optional[str] = None,
        error_message: Optional[str] = None,
        response_time: Optional[float] = None,
    ):
        """Record webhook delivery result.

        Args:
            webhook_id: Webhook ID
            event: Event type
            status: Delivery status
            response_code: HTTP response code
            response_body: Response body
            error_message: Error message
            response_time: Response time in seconds
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Update delivery record
        if status == WebhookStatus.SUCCESS:
            cursor.execute(
                """
                UPDATE webhook_deliveries 
                SET status = ?, response_code = ?, response_body = ?, 
                    delivered_at = CURRENT_TIMESTAMP
                WHERE webhook_id = ? AND event = ? AND status IN ('pending', 'retry')
                ORDER BY created_at DESC LIMIT 1
            """,
                (status.value, response_code, response_body, webhook_id, event.value),
            )
        else:
            cursor.execute(
                """
                UPDATE webhook_deliveries 
                SET status = ?, attempts = attempts + 1, error_message = ?
                WHERE webhook_id = ? AND event = ? AND status IN ('pending', 'retry')
                ORDER BY created_at DESC LIMIT 1
            """,
                (status.value, error_message, webhook_id, event.value),
            )

        # Update metrics
        today = datetime.now().date()

        cursor.execute(
            """
            INSERT OR IGNORE INTO webhook_metrics 
            (webhook_id, date, total_deliveries, successful_deliveries, failed_deliveries, avg_response_time)
            VALUES (?, ?, 0, 0, 0, 0)
        """,
            (webhook_id, today),
        )

        if status == WebhookStatus.SUCCESS:
            cursor.execute(
                """
                UPDATE webhook_metrics 
                SET total_deliveries = total_deliveries + 1,
                    successful_deliveries = successful_deliveries + 1,
                    avg_response_time = (avg_response_time * total_deliveries + ?) / (total_deliveries + 1)
                WHERE webhook_id = ? AND date = ?
            """,
                (response_time or 0, webhook_id, today),
            )
        else:
            cursor.execute(
                """
                UPDATE webhook_metrics 
                SET total_deliveries = total_deliveries + 1,
                    failed_deliveries = failed_deliveries + 1
                WHERE webhook_id = ? AND date = ?
            """,
                (webhook_id, today),
            )

        conn.commit()
        conn.close()

    def get_delivery_history(self, webhook_id: int, limit: int = 100) -> List[Dict]:
        """Get webhook delivery history.

        Args:
            webhook_id: Webhook ID
            limit: Maximum results

        Returns:
            Delivery history
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT event, payload, status, attempts, response_code, 
                   error_message, created_at, delivered_at
            FROM webhook_deliveries
            WHERE webhook_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (webhook_id, limit),
        )

        deliveries = []
        for row in cursor.fetchall():
            deliveries.append(
                {
                    "event": row[0],
                    "payload": json.loads(row[1]),
                    "status": row[2],
                    "attempts": row[3],
                    "response_code": row[4],
                    "error_message": row[5],
                    "created_at": row[6],
                    "delivered_at": row[7],
                }
            )

        conn.close()
        return deliveries

    def get_metrics(self, webhook_id: int, days: int = 30) -> Dict:
        """Get webhook metrics.

        Args:
            webhook_id: Webhook ID
            days: Number of days to include

        Returns:
            Webhook metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_date = datetime.now().date() - timedelta(days=days)

        cursor.execute(
            """
            SELECT 
                SUM(total_deliveries) as total,
                SUM(successful_deliveries) as successful,
                SUM(failed_deliveries) as failed,
                AVG(avg_response_time) as avg_response_time
            FROM webhook_metrics
            WHERE webhook_id = ? AND date >= ?
        """,
            (webhook_id, start_date),
        )

        row = cursor.fetchone()

        metrics = {
            "total_deliveries": row[0] or 0,
            "successful_deliveries": row[1] or 0,
            "failed_deliveries": row[2] or 0,
            "success_rate": (row[1] / row[0] * 100) if row[0] else 0,
            "average_response_time": row[3] or 0,
        }

        # Get daily breakdown
        cursor.execute(
            """
            SELECT date, total_deliveries, successful_deliveries, failed_deliveries
            FROM webhook_metrics
            WHERE webhook_id = ? AND date >= ?
            ORDER BY date DESC
        """,
            (webhook_id, start_date),
        )

        daily_metrics = []
        for row in cursor.fetchall():
            daily_metrics.append(
                {
                    "date": row[0],
                    "total": row[1],
                    "successful": row[2],
                    "failed": row[3],
                }
            )

        metrics["daily"] = daily_metrics

        conn.close()
        return metrics

    def test_webhook(self, webhook_id: int) -> bool:
        """Test webhook configuration.

        Args:
            webhook_id: Webhook ID

        Returns:
            True if test successful
        """
        config = self.webhooks.get(webhook_id)
        if not config:
            return False

        # Create test payload
        test_payload = WebhookPayload(
            event=WebhookEvent.CUSTOM,
            timestamp=datetime.now(),
            data={"test": True, "message": "This is a test webhook from Kasa Monitor"},
            metadata={"webhook_id": webhook_id},
        )

        # Try to deliver
        try:
            asyncio.run(self._deliver_async(webhook_id, config, test_payload))
            return True
        except Exception:
            return False

    def _load_webhooks(self):
        """Load webhooks from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, url, events, enabled, auth_type, auth_config,
                   headers, retry_count, retry_delay, timeout, validate_ssl,
                   secret, metadata
            FROM webhook_configs
        """
        )

        self.webhooks = {}
        for row in cursor.fetchall():
            config = WebhookConfig(
                name=row[1],
                url=row[2],
                events=[WebhookEvent(e) for e in json.loads(row[3])],
                enabled=bool(row[4]),
                auth_type=WebhookAuthType(row[5]),
                auth_config=json.loads(row[6]) if row[6] else None,
                headers=json.loads(row[7]) if row[7] else None,
                retry_count=row[8],
                retry_delay=row[9],
                timeout=row[10],
                validate_ssl=bool(row[11]),
                secret=row[12],
                metadata=json.loads(row[13]) if row[13] else None,
            )
            self.webhooks[row[0]] = config

        conn.close()
