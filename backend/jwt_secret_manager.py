#!/usr/bin/env python3
"""
Secure JWT Secret Key Management System

This module provides secure management of JWT secret keys with:
- Persistent storage with proper file permissions
- Key rotation mechanism with grace periods
- Backward compatibility for token validation
- Environment-based configuration

Copyright (C) 2025 Kasa Monitor Contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import os
import stat
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import json


logger = logging.getLogger(__name__)


class JWTSecretManager:
    """Secure JWT secret key management with rotation support."""
    
    def __init__(self, secret_file: Optional[str] = None):
        """
        Initialize JWT Secret Manager.
        
        Args:
            secret_file: Path to secret storage file (default: data/jwt_secrets.json)
        """
        self.secret_file = Path(secret_file or "data/jwt_secrets.json")
        self.secret_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_secure_permissions()
        
    def _ensure_secure_permissions(self) -> None:
        """Ensure secret file has secure permissions (600)."""
        if self.secret_file.exists():
            # Set file permissions to 600 (read/write for owner only)
            os.chmod(self.secret_file, stat.S_IRUSR | stat.S_IWUSR)
            
            # Verify permissions
            file_stat = os.stat(self.secret_file)
            if file_stat.st_mode & 0o077:  # Check if group/other have any permissions
                logger.warning(f"Secret file {self.secret_file} has insecure permissions")
                
    def _load_secrets(self) -> Dict[str, Any]:
        """Load secrets from storage file."""
        if not self.secret_file.exists():
            return {}
            
        try:
            with open(self.secret_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load secrets: {e}")
            return {}
            
    def _save_secrets(self, secrets_data: Dict[str, Any]) -> None:
        """Save secrets to storage file with secure permissions."""
        try:
            # Write to temporary file first
            temp_file = self.secret_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(secrets_data, f, indent=2)
                
            # Set secure permissions on temp file
            os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR)
            
            # Atomically move temp file to final location
            temp_file.replace(self.secret_file)
            
            logger.info(f"Secrets saved to {self.secret_file}")
            
        except IOError as e:
            logger.error(f"Failed to save secrets: {e}")
            raise
            
    def get_current_secret(self) -> str:
        """
        Get the current JWT secret key.
        
        Returns:
            Current secret key string
        """
        # First check environment variable
        env_secret = os.getenv("JWT_SECRET_KEY")
        if env_secret and len(env_secret) >= 32:
            logger.info("Using JWT secret from environment variable")
            return env_secret
            
        # Load from persistent storage
        secrets_data = self._load_secrets()
        
        if "current" in secrets_data:
            current_data = secrets_data["current"]
            # Check if secret is still valid (not expired)
            if datetime.fromisoformat(current_data["created"]) + timedelta(days=90) > datetime.now():
                return current_data["secret"]
                
        # Generate new secret if none exists or expired
        return self._generate_new_secret()
        
    def _generate_new_secret(self) -> str:
        """Generate a new JWT secret key and store it persistently."""
        new_secret = secrets.token_urlsafe(64)  # 512-bit key
        current_time = datetime.now().isoformat()
        
        secrets_data = self._load_secrets()
        
        # Move current secret to previous if it exists
        if "current" in secrets_data:
            if "previous" not in secrets_data:
                secrets_data["previous"] = []
            secrets_data["previous"].append(secrets_data["current"])
            
        # Keep only last 3 previous secrets (for grace period)
        if "previous" in secrets_data:
            secrets_data["previous"] = secrets_data["previous"][-3:]
            
        # Set new current secret
        secrets_data["current"] = {
            "secret": new_secret,
            "created": current_time,
            "key_id": secrets.token_hex(8)
        }
        
        self._save_secrets(secrets_data)
        
        logger.info("Generated new JWT secret key")
        return new_secret
        
    def get_all_valid_secrets(self) -> List[str]:
        """
        Get all valid secrets for token validation (current + recent previous).
        
        This allows for graceful key rotation where old tokens remain valid
        for a grace period.
        
        Returns:
            List of valid secret keys (current first, then previous)
        """
        secrets_data = self._load_secrets()
        valid_secrets = []
        
        # Add current secret
        if "current" in secrets_data:
            valid_secrets.append(secrets_data["current"]["secret"])
            
        # Add previous secrets that are still within grace period
        if "previous" in secrets_data:
            cutoff_time = datetime.now() - timedelta(hours=1)  # 1-hour grace period
            
            for prev_secret in reversed(secrets_data["previous"]):
                created_time = datetime.fromisoformat(prev_secret["created"])
                if created_time >= cutoff_time:
                    valid_secrets.append(prev_secret["secret"])
                    
        return valid_secrets
        
    def rotate_secret(self) -> str:
        """
        Manually rotate the JWT secret key.
        
        Returns:
            New secret key
        """
        logger.info("Manually rotating JWT secret key")
        return self._generate_new_secret()
        
    def validate_secret_strength(self, secret: str) -> bool:
        """
        Validate that a secret key meets security requirements.
        
        Args:
            secret: Secret key to validate
            
        Returns:
            True if secret meets requirements, False otherwise
        """
        if len(secret) < 32:
            logger.warning("JWT secret is too short (minimum 32 characters)")
            return False
            
        # Check for sufficient entropy (base64url has ~6 bits per character)
        if len(secret) < 43:  # 256 bits / 6 bits per char ≈ 43 chars
            logger.warning("JWT secret may have insufficient entropy")
            return False
            
        return True
        
    def get_secret_info(self) -> Dict[str, Any]:
        """Get information about current secret (for admin/debugging)."""
        secrets_data = self._load_secrets()
        
        info = {
            "has_current": "current" in secrets_data,
            "has_previous": "previous" in secrets_data and len(secrets_data["previous"]) > 0,
            "file_exists": self.secret_file.exists(),
            "file_permissions": oct(os.stat(self.secret_file).st_mode)[-3:] if self.secret_file.exists() else None
        }
        
        if "current" in secrets_data:
            current = secrets_data["current"]
            info.update({
                "current_created": current["created"],
                "current_key_id": current["key_id"],
                "current_age_days": (datetime.now() - datetime.fromisoformat(current["created"])).days
            })
            
        return info


# Global instance
_secret_manager = None


def get_jwt_secret_manager() -> JWTSecretManager:
    """Get the global JWT secret manager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = JWTSecretManager()
    return _secret_manager


def get_current_jwt_secret() -> str:
    """Get the current JWT secret key (convenience function)."""
    return get_jwt_secret_manager().get_current_secret()


def get_all_valid_jwt_secrets() -> List[str]:
    """Get all valid JWT secrets for token validation (convenience function)."""
    return get_jwt_secret_manager().get_all_valid_secrets()


if __name__ == "__main__":
    # Test/demo the secret manager
    import sys
    
    manager = JWTSecretManager("test_secrets.json")
    
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        # Show secret info
        info = manager.get_secret_info()
        print("JWT Secret Manager Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        # Generate and show current secret
        secret = manager.get_current_secret()
        print(f"Current JWT Secret: {secret[:16]}... (truncated)")
        print(f"Secret length: {len(secret)} characters")
        print(f"Valid: {manager.validate_secret_strength(secret)}")