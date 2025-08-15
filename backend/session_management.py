"""Session Management with advanced features.

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

import secrets
import sqlite3
import json
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import hashlib
from fastapi import Request, HTTPException, status


class SessionStatus(Enum):
    """Session status states."""

    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    LOCKED = "locked"


@dataclass
class SessionConfig:
    """Session configuration settings."""

    timeout_minutes: int = 30
    absolute_timeout_hours: int = 12
    concurrent_sessions_limit: int = 3
    remember_me_days: int = 30
    inactivity_timeout_minutes: int = 15
    require_same_ip: bool = False
    require_same_user_agent: bool = True
    enable_session_binding: bool = True
    enable_refresh_tokens: bool = True
    refresh_token_days: int = 7


class SessionStore:
    """Session storage backend interface."""

    def get(self, session_id: str) -> Optional[Dict]:
        raise NotImplementedError

    def set(self, session_id: str, data: Dict, ttl: int):
        raise NotImplementedError

    def delete(self, session_id: str):
        raise NotImplementedError

    def exists(self, session_id: str) -> bool:
        raise NotImplementedError


class RedisSessionStore(SessionStore):
    """Redis-based session storage."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "session:"

    def get(self, session_id: str) -> Optional[Dict]:
        data = self.redis.get(f"{self.prefix}{session_id}")
        if data:
            return json.loads(data)
        return None

    def set(self, session_id: str, data: Dict, ttl: int):
        self.redis.setex(f"{self.prefix}{session_id}", ttl, json.dumps(data))

    def delete(self, session_id: str):
        self.redis.delete(f"{self.prefix}{session_id}")

    def exists(self, session_id: str) -> bool:
        return self.redis.exists(f"{self.prefix}{session_id}") > 0


class DatabaseSessionStore(SessionStore):
    """Database-based session storage."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_expires 
            ON sessions(expires_at)
        """
        )

        conn.commit()
        conn.close()

    def get(self, session_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT data FROM sessions
            WHERE session_id = ? AND expires_at > CURRENT_TIMESTAMP
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def set(self, session_id: str, data: Dict, ttl: int):
        expires_at = datetime.now() + timedelta(seconds=ttl)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions 
            (session_id, data, expires_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (session_id, json.dumps(data), expires_at),
        )

        conn.commit()
        conn.close()

    def delete(self, session_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM sessions WHERE session_id = ?
        """,
            (session_id,),
        )

        conn.commit()
        conn.close()

    def exists(self, session_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1 FROM sessions
            WHERE session_id = ? AND expires_at > CURRENT_TIMESTAMP
        """,
            (session_id,),
        )

        exists = cursor.fetchone() is not None
        conn.close()

        return exists

    def cleanup_expired(self):
        """Remove expired sessions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP
        """
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted


class SessionManager:
    """Advanced session management system."""

    def __init__(
        self,
        store: SessionStore,
        config: Optional[SessionConfig] = None,
        db_path: str = "kasa_monitor.db",
    ):
        """Initialize session manager.

        Args:
            store: Session storage backend
            config: Session configuration
            db_path: Path to database for tracking
        """
        self.store = store
        self.config = config or SessionConfig()
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize session tracking tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Session tracking table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                fingerprint TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                device_name TEXT,
                location TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Refresh tokens table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Session activity log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def create_session(
        self,
        user_id: int,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False,
        device_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new session.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: User agent string
            remember_me: Extended session duration
            device_name: Optional device name

        Returns:
            Session details including tokens
        """
        # Check concurrent session limit
        self._enforce_concurrent_limit(user_id)

        # Generate session ID and tokens
        session_id = secrets.token_urlsafe(32)

        # Determine session duration
        if remember_me:
            timeout_minutes = self.config.remember_me_days * 24 * 60
        else:
            timeout_minutes = self.config.timeout_minutes

        expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
        absolute_expires = datetime.now() + timedelta(hours=self.config.absolute_timeout_hours)

        # Use the earlier expiration
        if absolute_expires < expires_at:
            expires_at = absolute_expires

        # Create session fingerprint
        fingerprint = self._create_fingerprint(ip_address, user_agent)

        # Session data
        session_data = {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "fingerprint": fingerprint,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "remember_me": remember_me,
            "device_name": device_name,
        }

        # Store in session store
        ttl = int((expires_at - datetime.now()).total_seconds())
        self.store.set(session_id, session_data, ttl)

        # Track in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO session_tracking 
            (session_id, user_id, ip_address, user_agent, fingerprint, 
             expires_at, device_name, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """,
            (
                session_id,
                user_id,
                ip_address,
                user_agent,
                fingerprint,
                expires_at,
                device_name,
            ),
        )

        conn.commit()
        conn.close()

        # Log session creation
        self._log_activity(session_id, "created", f"New session from {ip_address}", ip_address)

        result = {
            "session_id": session_id,
            "expires_at": expires_at.isoformat(),
            "timeout_minutes": timeout_minutes,
        }

        # Generate refresh token if enabled
        if self.config.enable_refresh_tokens:
            refresh_token = self._create_refresh_token(session_id, user_id)
            result["refresh_token"] = refresh_token

        return result

    def validate_session(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Dict]:
        """Validate and get session data.

        Args:
            session_id: Session ID
            ip_address: Current IP address
            user_agent: Current user agent

        Returns:
            Session data if valid, None otherwise
        """
        # Get session from store
        session_data = self.store.get(session_id)

        if not session_data:
            self._update_session_status(session_id, SessionStatus.EXPIRED)
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.now() > expires_at:
            self.invalidate_session(session_id)
            return None

        # Check inactivity timeout
        last_activity = datetime.fromisoformat(session_data["last_activity"])
        inactivity_limit = datetime.now() - timedelta(minutes=self.config.inactivity_timeout_minutes)

        if last_activity < inactivity_limit:
            self.invalidate_session(session_id)
            self._log_activity(session_id, "timeout", "Inactivity timeout", ip_address)
            return None

        # Validate session binding if enabled
        if self.config.enable_session_binding:
            if self.config.require_same_ip and ip_address:
                if session_data["ip_address"] != ip_address:
                    self._log_activity(
                        session_id,
                        "ip_mismatch",
                        f'IP changed from {session_data["ip_address"]} to {ip_address}',
                        ip_address,
                    )
                    self.invalidate_session(session_id)
                    return None

            if self.config.require_same_user_agent and user_agent:
                if session_data["user_agent"] != user_agent:
                    self._log_activity(session_id, "agent_mismatch", "User agent changed", ip_address)
                    self.invalidate_session(session_id)
                    return None

        # Update last activity
        session_data["last_activity"] = datetime.now().isoformat()
        ttl = int((expires_at - datetime.now()).total_seconds())
        self.store.set(session_id, session_data, ttl)

        # Update tracking
        self._update_last_activity(session_id)

        return session_data

    def refresh_session(self, refresh_token: str, ip_address: str) -> Optional[Dict]:
        """Refresh session using refresh token.

        Args:
            refresh_token: Refresh token
            ip_address: Current IP address

        Returns:
            New session details if valid
        """
        if not self.config.enable_refresh_tokens:
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Validate refresh token
        cursor.execute(
            """
            SELECT session_id, user_id, expires_at FROM refresh_tokens
            WHERE token = ? AND used_at IS NULL
        """,
            (refresh_token,),
        )

        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        session_id, user_id, expires_at = row

        # Check expiration
        if datetime.now() > datetime.fromisoformat(expires_at):
            conn.close()
            return None

        # Mark token as used
        cursor.execute(
            """
            UPDATE refresh_tokens
            SET used_at = CURRENT_TIMESTAMP
            WHERE token = ?
        """,
            (refresh_token,),
        )

        conn.commit()
        conn.close()

        # Get original session data
        old_session = self.store.get(session_id)

        if old_session:
            # Invalidate old session
            self.invalidate_session(session_id)

            # Create new session with same settings
            return self.create_session(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=old_session.get("user_agent", ""),
                remember_me=old_session.get("remember_me", False),
                device_name=old_session.get("device_name"),
            )

        return None

    def invalidate_session(self, session_id: str):
        """Invalidate a session.

        Args:
            session_id: Session ID to invalidate
        """
        # Remove from store
        self.store.delete(session_id)

        # Update status in database
        self._update_session_status(session_id, SessionStatus.INVALIDATED)

        # Invalidate refresh tokens
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE refresh_tokens
            SET used_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """,
            (session_id,),
        )

        conn.commit()
        conn.close()

        # Log invalidation
        self._log_activity(session_id, "invalidated", "Session invalidated")

    def invalidate_all_sessions(self, user_id: int):
        """Invalidate all sessions for a user.

        Args:
            user_id: User ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all active sessions
        cursor.execute(
            """
            SELECT session_id FROM session_tracking
            WHERE user_id = ? AND status = 'active'
        """,
            (user_id,),
        )

        sessions = cursor.fetchall()
        conn.close()

        # Invalidate each session
        for (session_id,) in sessions:
            self.invalidate_session(session_id)

    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """Get all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of session details
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT session_id, ip_address, user_agent, device_name,
                   created_at, last_activity, expires_at, status
            FROM session_tracking
            WHERE user_id = ?
            ORDER BY last_activity DESC
        """,
            (user_id,),
        )

        sessions = []
        for row in cursor.fetchall():
            sessions.append(
                {
                    "session_id": row[0],
                    "ip_address": row[1],
                    "user_agent": row[2],
                    "device_name": row[3],
                    "created_at": row[4],
                    "last_activity": row[5],
                    "expires_at": row[6],
                    "status": row[7],
                    "is_current": self.store.exists(row[0]),
                }
            )

        conn.close()
        return sessions

    def terminate_session(self, session_id: str, user_id: int) -> bool:
        """Terminate a specific session.

        Args:
            session_id: Session ID
            user_id: User ID (for authorization)

        Returns:
            True if terminated
        """
        # Verify session belongs to user
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1 FROM session_tracking
            WHERE session_id = ? AND user_id = ?
        """,
            (session_id, user_id),
        )

        if cursor.fetchone():
            conn.close()
            self.invalidate_session(session_id)
            self._log_activity(session_id, "terminated", "Session terminated by user")
            return True

        conn.close()
        return False

    def _enforce_concurrent_limit(self, user_id: int):
        """Enforce concurrent session limit.

        Args:
            user_id: User ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get active sessions
        cursor.execute(
            """
            SELECT session_id FROM session_tracking
            WHERE user_id = ? AND status = 'active'
            ORDER BY last_activity DESC
        """,
            (user_id,),
        )

        sessions = cursor.fetchall()

        # Invalidate oldest sessions if limit exceeded
        if len(sessions) >= self.config.concurrent_sessions_limit:
            for session in sessions[self.config.concurrent_sessions_limit - 1 :]:
                self.invalidate_session(session[0])
                self._log_activity(session[0], "limit_exceeded", "Concurrent session limit exceeded")

        conn.close()

    def _create_fingerprint(self, ip_address: str, user_agent: str) -> str:
        """Create session fingerprint.

        Args:
            ip_address: IP address
            user_agent: User agent

        Returns:
            Fingerprint hash
        """
        data = f"{ip_address}:{user_agent}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _create_refresh_token(self, session_id: str, user_id: int) -> str:
        """Create refresh token.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            Refresh token
        """
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=self.config.refresh_token_days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO refresh_tokens 
            (token, session_id, user_id, expires_at)
            VALUES (?, ?, ?, ?)
        """,
            (token, session_id, user_id, expires_at),
        )

        conn.commit()
        conn.close()

        return token

    def _update_session_status(self, session_id: str, status: SessionStatus):
        """Update session status in tracking.

        Args:
            session_id: Session ID
            status: New status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE session_tracking
            SET status = ?
            WHERE session_id = ?
        """,
            (status.value, session_id),
        )

        conn.commit()
        conn.close()

    def _update_last_activity(self, session_id: str):
        """Update last activity timestamp.

        Args:
            session_id: Session ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE session_tracking
            SET last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """,
            (session_id,),
        )

        conn.commit()
        conn.close()

    def _log_activity(
        self,
        session_id: str,
        activity_type: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """Log session activity.

        Args:
            session_id: Session ID
            activity_type: Type of activity
            details: Activity details
            ip_address: IP address
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO session_activity 
            (session_id, activity_type, details, ip_address)
            VALUES (?, ?, ?, ?)
        """,
            (session_id, activity_type, details, ip_address),
        )

        conn.commit()
        conn.close()

    def get_session_activity(self, session_id: str) -> List[Dict]:
        """Get activity log for a session.

        Args:
            session_id: Session ID

        Returns:
            List of activities
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT activity_type, details, ip_address, timestamp
            FROM session_activity
            WHERE session_id = ?
            ORDER BY timestamp DESC
        """,
            (session_id,),
        )

        activities = []
        for row in cursor.fetchall():
            activities.append(
                {
                    "type": row[0],
                    "details": row[1],
                    "ip_address": row[2],
                    "timestamp": row[3],
                }
            )

        conn.close()
        return activities
