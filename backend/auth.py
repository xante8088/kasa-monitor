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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jwt_secret_manager import get_all_valid_jwt_secrets, get_current_jwt_secret

from models import Permission, User, UserRole

# Load environment variables
load_dotenv()

# Security configuration
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
        Permission.DATA_EXPORT,
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
        Permission.DATA_EXPORT,
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

        # Use secure secret manager for token creation
        current_secret = get_current_jwt_secret()
        encoded_jwt = jwt.encode(to_encode, current_secret, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token with key rotation support."""
        # Try all valid secrets (current + recent previous for grace period)
        valid_secrets = get_all_valid_jwt_secrets()

        last_exception = None
        for secret in valid_secrets:
            try:
                payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
                # Additional validation - check token structure
                if not payload.get("user") or not payload.get("exp"):
                    raise jwt.InvalidTokenError("Invalid token structure")
                return payload
            except jwt.ExpiredSignatureError as e:
                # Token is expired - don't try other secrets
                last_exception = e
                break
            except (jwt.InvalidTokenError, jwt.JWTError) as e:
                # Invalid token with this secret, try next one
                last_exception = e
                continue

        # No secret worked, raise appropriate exception with structured error
        if isinstance(last_exception, jwt.ExpiredSignatureError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "authentication_expired",
                    "message": "Your session has expired. Please log in again.",
                    "error_code": "TOKEN_EXPIRED",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "redirect_to": "/login",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            # Invalid token - none of the secrets worked
            import logging

            logging.error(
                f"JWT verification failed with all secrets: {str(last_exception)}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "authentication_invalid",
                    "message": "Invalid authentication credentials. Please log in again.",
                    "error_code": "TOKEN_INVALID",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "redirect_to": "/login",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def create_refresh_token(user_data: Dict[str, Any]) -> str:
        """Create a refresh token with extended expiration."""
        to_encode = user_data.copy()
        # Refresh tokens last 7 days
        expire = datetime.now(timezone.utc) + timedelta(days=7)

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
        serialized_data = serialize_datetime(user_data)
        to_encode = (
            serialized_data.copy()
            if isinstance(serialized_data, dict)
            else user_data.copy()
        )
        to_encode.update(
            {"exp": expire, "type": "refresh"}
        )  # Add exp as datetime object

        current_secret = get_current_jwt_secret()
        encoded_jwt = jwt.encode(to_encode, current_secret, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_refresh_token(token: str) -> Dict[str, Any]:
        """Verify and decode a refresh token."""
        valid_secrets = get_all_valid_jwt_secrets()

        last_exception = None
        for secret in valid_secrets:
            try:
                payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
                # Verify it's a refresh token
                if payload.get("type") != "refresh":
                    raise jwt.InvalidTokenError("Not a refresh token")
                return payload
            except jwt.ExpiredSignatureError as e:
                last_exception = e
                break
            except (jwt.InvalidTokenError, jwt.JWTError) as e:
                last_exception = e
                continue

        # Handle refresh token errors
        if isinstance(last_exception, jwt.ExpiredSignatureError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "refresh_token_expired",
                    "message": "Refresh token has expired. Please log in again.",
                    "error_code": "REFRESH_TOKEN_EXPIRED",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "redirect_to": "/login",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "refresh_token_invalid",
                    "message": "Invalid refresh token. Please log in again.",
                    "error_code": "REFRESH_TOKEN_INVALID",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "redirect_to": "/login",
                },
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
            detail={
                "error": "authentication_required",
                "message": "Authentication required. Please log in to continue.",
                "error_code": "AUTH_REQUIRED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "redirect_to": "/login",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = AuthManager.verify_token(credentials.credentials)
    user_data = payload.get("user")
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_invalid",
                "message": "Invalid authentication token. Please log in again.",
                "error_code": "TOKEN_INVALID",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "redirect_to": "/login",
            },
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


def get_auth_security_status() -> Dict[str, Any]:
    """Get comprehensive authentication security status."""
    from jwt_secret_manager import get_jwt_secret_manager

    manager = get_jwt_secret_manager()
    secret_info = manager.get_secret_info()

    return {
        "jwt_configuration": {
            "algorithm": ALGORITHM,
            "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
            "secret_management": {
                "has_current_secret": secret_info.get("has_current"),
                "has_previous_secrets": secret_info.get("has_previous"),
                "secret_file_exists": secret_info.get("file_exists"),
                "file_permissions": secret_info.get("file_permissions"),
                "current_secret_age_days": secret_info.get("current_age_days"),
            },
        },
        "security_features": {
            "bcrypt_password_hashing": True,
            "jwt_key_rotation": True,
            "role_based_permissions": True,
            "structured_error_responses": True,
            "token_refresh_enabled": True,
            "session_management_available": True,
            "audit_logging_enabled": True,
        },
        "token_settings": {
            "access_token_lifetime": f"{ACCESS_TOKEN_EXPIRE_MINUTES} minutes",
            "refresh_token_lifetime": "7 days",
            "token_validation_strict": True,
        },
        "recommendations": _get_security_recommendations(secret_info),
    }


def _get_security_recommendations(secret_info: Dict[str, Any]) -> List[str]:
    """Get security recommendations based on current configuration."""
    recommendations = []

    # Check secret age
    age_days = secret_info.get("current_age_days", 0)
    if age_days > 30:
        recommendations.append(
            f"JWT secret is {age_days} days old. Consider rotating for enhanced security."
        )

    # Check file permissions
    permissions = secret_info.get("file_permissions")
    if permissions and permissions != "600":
        recommendations.append(
            f"JWT secret file has permissions {permissions}. Should be 600 for security."
        )

    # Check if environment variable is used
    if not os.getenv("JWT_SECRET_KEY"):
        recommendations.append(
            "Consider setting JWT_SECRET_KEY environment variable for production."
        )

    # General recommendations
    recommendations.extend(
        [
            "Ensure HTTPS is enabled in production environments",
            "Regularly monitor authentication logs for suspicious activity",
            "Consider implementing rate limiting on authentication endpoints",
            "Review and rotate JWT secrets periodically",
        ]
    )

    return recommendations
