"""API Key Authentication system.

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

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery


class APIKeyScope(Enum):
    """API key permission scopes."""

    READ_DEVICES = "devices:read"
    WRITE_DEVICES = "devices:write"
    READ_ENERGY = "energy:read"
    WRITE_ENERGY = "energy:write"
    READ_USERS = "users:read"
    WRITE_USERS = "users:write"
    READ_SYSTEM = "system:read"
    WRITE_SYSTEM = "system:write"
    ADMIN = "admin:*"


class APIKeyManager:
    """Manages API keys for authentication."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize API key manager.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.key_prefix = "kasa_"
        self.key_length = 32
        self._init_database()

    def _init_database(self):
        """Initialize API keys table in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                scopes TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                metadata TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash
            ON api_keys(key_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_api_keys_user
            ON api_keys(user_id)
        """
        )

        conn.commit()
        conn.close()

    def generate_api_key(
        self,
        user_id: int,
        name: str,
        scopes: List[APIKeyScope],
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Generate a new API key.

        Args:
            user_id: User ID who owns the key
            name: Friendly name for the key
            scopes: List of permission scopes
            expires_in_days: Optional expiration in days
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with key details including the plain key (only shown once)
        """
        # Generate random key
        random_part = secrets.token_urlsafe(self.key_length)
        api_key = f"{self.key_prefix}{random_part}"

        # Hash the key for storage
        key_hash = self._hash_key(api_key)

        # Get first 8 chars as prefix for identification
        key_prefix = api_key[:12] + "..."

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO api_keys
                (key_hash, key_prefix, name, user_id, scopes, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    key_hash,
                    key_prefix,
                    name,
                    user_id,
                    json.dumps([s.value for s in scopes]),
                    expires_at,
                    json.dumps(metadata) if metadata else None,
                ),
            )

            key_id = cursor.lastrowid
            conn.commit()

            return {
                "id": key_id,
                "key": api_key,  # Only returned on creation
                "key_prefix": key_prefix,
                "name": name,
                "scopes": [s.value for s in scopes],
                "created_at": datetime.now().isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
                "metadata": metadata,
            }
        finally:
            conn.close()

    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify an API key and return its details.

        Args:
            api_key: The API key to verify

        Returns:
            Key details if valid, None otherwise
        """
        key_hash = self._hash_key(api_key)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, name, user_id, scopes, expires_at, is_active, metadata
                FROM api_keys
                WHERE key_hash = ?
            """,
                (key_hash,),
            )

            row = cursor.fetchone()

            if not row:
                return None

            key_id, name, user_id, scopes, expires_at, is_active, metadata = row

            # Check if key is active
            if not is_active:
                return None

            # Check expiration
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_dt:
                    return None

            # Update last used timestamp
            cursor.execute(
                """
                UPDATE api_keys
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (key_id,),
            )
            conn.commit()

            return {
                "id": key_id,
                "name": name,
                "user_id": user_id,
                "scopes": json.loads(scopes),
                "expires_at": expires_at,
                "metadata": json.loads(metadata) if metadata else None,
            }
        finally:
            conn.close()

    def revoke_api_key(self, key_id: int, user_id: int) -> bool:
        """Revoke an API key.

        Args:
            key_id: ID of the key to revoke
            user_id: User ID (for authorization check)

        Returns:
            True if revoked, False if not found or unauthorized
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE api_keys
                SET is_active = 0
                WHERE id = ? AND user_id = ?
            """,
                (key_id, user_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def rotate_api_key(self, key_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Rotate an API key (revoke old, create new with same settings).

        Args:
            key_id: ID of the key to rotate
            user_id: User ID (for authorization check)

        Returns:
            New key details if successful, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get existing key details
            cursor.execute(
                """
                SELECT name, scopes, metadata
                FROM api_keys
                WHERE id = ? AND user_id = ? AND is_active = 1
            """,
                (key_id, user_id),
            )

            row = cursor.fetchone()
            if not row:
                return None

            name, scopes_json, metadata_json = row

            # Revoke old key
            cursor.execute(
                """
                UPDATE api_keys
                SET is_active = 0
                WHERE id = ?
            """,
                (key_id,),
            )

            conn.commit()

            # Create new key with same settings
            scopes = [APIKeyScope(s) for s in json.loads(scopes_json)]
            metadata = json.loads(metadata_json) if metadata_json else None

            return self.generate_api_key(
                user_id=user_id,
                name=f"{name} (rotated)",
                scopes=scopes,
                metadata=metadata,
            )
        finally:
            conn.close()

    def list_api_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """List all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of key details (without the actual keys)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, key_prefix, name, scopes, created_at,
                       expires_at, last_used_at, is_active, metadata
                FROM api_keys
                WHERE user_id = ?
                ORDER BY created_at DESC
            """,
                (user_id,),
            )

            keys = []
            for row in cursor.fetchall():
                keys.append(
                    {
                        "id": row[0],
                        "key_prefix": row[1],
                        "name": row[2],
                        "scopes": json.loads(row[3]),
                        "created_at": row[4],
                        "expires_at": row[5],
                        "last_used_at": row[6],
                        "is_active": bool(row[7]),
                        "metadata": json.loads(row[8]) if row[8] else None,
                    }
                )

            return keys
        finally:
            conn.close()

    def check_scope(self, api_key_details: Dict, required_scope: APIKeyScope) -> bool:
        """Check if API key has required scope.

        Args:
            api_key_details: Key details from verify_api_key
            required_scope: Required scope

        Returns:
            True if scope is granted, False otherwise
        """
        if not api_key_details:
            return False

        scopes = api_key_details.get("scopes", [])

        # Admin scope grants all permissions
        if APIKeyScope.ADMIN.value in scopes:
            return True

        return required_scope.value in scopes

    def _hash_key(self, api_key: str) -> str:
        """Hash an API key for secure storage.

        Args:
            api_key: Plain text API key

        Returns:
            Hashed key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def cleanup_expired_keys(self):
        """Remove expired API keys from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE api_keys
                SET is_active = 0
                WHERE expires_at IS NOT NULL
                AND expires_at < CURRENT_TIMESTAMP
            """
            )

            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


# FastAPI dependencies
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> Optional[str]:
    """Extract API key from request.

    Args:
        api_key_header: API key from header
        api_key_query: API key from query parameter

    Returns:
        API key if present
    """
    return api_key_header or api_key_query


def require_api_key(scope: Optional[APIKeyScope] = None):
    """Require API key authentication with optional scope.

    Args:
        scope: Optional required scope

    Returns:
        Dependency function
    """

    async def verify_key(api_key: Optional[str] = Security(get_api_key)):
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
            )

        manager = APIKeyManager()
        key_details = manager.verify_api_key(api_key)

        if not key_details:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

        if scope and not manager.check_scope(key_details, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient scope: {scope.value} required",
            )

        return key_details

    return verify_key
