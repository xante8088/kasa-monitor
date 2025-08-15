"""Authentication and authorization system.

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

import os
import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
from jose import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import User, Permission, UserRole
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Role permission mappings
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        # All permissions - admin has everything
        Permission.DEVICES_VIEW,
        Permission.DEVICES_DISCOVER,
        Permission.DEVICES_EDIT,
        Permission.DEVICES_REMOVE,
        Permission.DEVICES_CONTROL,
        Permission.RATES_VIEW,
        Permission.RATES_EDIT,
        Permission.RATES_DELETE,
        Permission.COSTS_VIEW,
        Permission.COSTS_EXPORT,
        Permission.USERS_VIEW,
        Permission.USERS_INVITE,
        Permission.USERS_EDIT,
        Permission.USERS_REMOVE,
        Permission.USERS_PERMISSIONS,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_LOGS,
        Permission.SYSTEM_LOGS_CLEAR,
        Permission.SYSTEM_BACKUP,
    ],
    UserRole.OPERATOR: [
        # Can manage devices and rates but not users
        Permission.DEVICES_VIEW,
        Permission.DEVICES_DISCOVER,
        Permission.DEVICES_EDIT,
        Permission.DEVICES_CONTROL,
        Permission.RATES_VIEW,
        Permission.RATES_EDIT,
        Permission.COSTS_VIEW,
        Permission.COSTS_EXPORT,
    ],
    UserRole.VIEWER: [
        # Read-only access to most features
        Permission.DEVICES_VIEW,
        Permission.RATES_VIEW,
        Permission.COSTS_VIEW,
    ],
    UserRole.GUEST: [
        # Very limited access
        Permission.DEVICES_VIEW,
    ],
}

security = HTTPBearer(auto_error=False)


class AuthManager:
    """Handles authentication and authorization."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def create_access_token(
        data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )

        # Convert datetime objects to ISO strings for JSON serialization (except exp)
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(v) for v in obj]
            return obj

        # Serialize everything except exp (which JWT needs as datetime)
        serialized_data = serialize_datetime(data)
        to_encode = (
            serialized_data.copy() if isinstance(serialized_data, dict) else data.copy()
        )
        to_encode.update({"exp": expire})  # Add exp as datetime object

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError as e:
            import logging

            logging.error(f"JWT verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def get_user_permissions(role: UserRole) -> list[Permission]:
        """Get permissions for a user role."""
        return ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def check_permission(
        user_permissions: list[Permission], required_permission: Permission
    ) -> bool:
        """Check if user has required permission."""
        return required_permission in user_permissions


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get current authenticated user from JWT token."""
    if not credentials:
        return None

    try:
        payload = AuthManager.verify_token(credentials.credentials)
        user_data = payload.get("user")
        if user_data:
            user = User(**user_data)
            user.permissions = AuthManager.get_user_permissions(user.role)
            return user
    except HTTPException:
        pass

    return None


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Require authentication - raises exception if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = AuthManager.verify_token(credentials.credentials)
    user_data = payload.get("user")
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = User(**user_data)
    user.permissions = AuthManager.get_user_permissions(user.role)
    return user


def require_permission(permission: Permission):
    """Decorator to require specific permission."""

    def permission_checker(user: User = Depends(require_auth)) -> User:
        if not AuthManager.check_permission(user.permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission.value}",
            )
        return user

    return permission_checker


def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin role."""
    if not user.is_admin and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


def get_network_access_config() -> Dict[str, Any]:
    """Get network access configuration."""
    return {
        "allow_local_only": os.getenv("ALLOW_LOCAL_ONLY", "true").lower() == "true",
        "allowed_networks": os.getenv(
            "ALLOWED_NETWORKS", "192.168.0.0/16,10.0.0.0/8,172.16.0.0/12"
        ).split(","),
        "use_https": os.getenv("USE_HTTPS", "false").lower() == "true",
        "ssl_cert_path": os.getenv("SSL_CERT_PATH", ""),
        "ssl_key_path": os.getenv("SSL_KEY_PATH", ""),
    }


def is_local_network_ip(client_ip: str) -> bool:
    """Check if IP is from local network."""
    import ipaddress

    try:
        client = ipaddress.ip_address(client_ip)

        # Check common private network ranges
        private_ranges = [
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("127.0.0.0/8"),  # Loopback
        ]

        for network in private_ranges:
            if client in network:
                return True

        return False
    except ValueError:
        return False
