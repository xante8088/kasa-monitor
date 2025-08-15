"""Two-Factor Authentication implementation using TOTP.

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

import base64
import io
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pyotp
import qrcode


class TwoFactorAuth:
    """Handles Two-Factor Authentication using TOTP."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize 2FA system.

        Args:
            db_path: Path to database for storing 2FA data
        """
        self.db_path = db_path
        self.issuer_name = "Kasa Monitor"
        self.backup_codes_count = 10
        self.backup_code_length = 8

    def generate_secret(self) -> str:
        """Generate a new TOTP secret for a user.

        Returns:
            Base32 encoded secret key
        """
        return pyotp.random_base32()

    def generate_qr_code(self, username: str, secret: str) -> str:
        """Generate QR code for TOTP setup.

        Args:
            username: User's username
            secret: TOTP secret key

        Returns:
            Base64 encoded QR code image
        """
        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username, issuer_name=self.issuer_name
        )

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify a TOTP token.

        Args:
            secret: User's TOTP secret
            token: 6-digit token to verify
            window: Number of time windows to check (for clock skew)

        Returns:
            True if token is valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            # Allow for clock skew by checking adjacent time windows
            return totp.verify(token, valid_window=window)
        except Exception:
            return False

    def generate_backup_codes(self) -> List[str]:
        """Generate backup codes for account recovery.

        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(self.backup_codes_count):
            # Generate alphanumeric backup code
            code = "".join(
                secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                for _ in range(self.backup_code_length)
            )
            # Add hyphen for readability (XXXX-XXXX)
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)

        return codes

    def hash_backup_code(self, code: str) -> str:
        """Hash a backup code for secure storage.

        Args:
            code: Plain text backup code

        Returns:
            Hashed backup code
        """
        import hashlib

        # Remove hyphen if present
        code = code.replace("-", "")
        return hashlib.sha256(code.encode()).hexdigest()

    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> bool:
        """Verify a backup code against stored hashes.

        Args:
            code: Backup code to verify
            hashed_codes: List of hashed backup codes

        Returns:
            True if code is valid, False otherwise
        """
        hashed_input = self.hash_backup_code(code)
        return hashed_input in hashed_codes

    def get_enrollment_data(self, username: str) -> Dict[str, Any]:
        """Get all data needed for 2FA enrollment.

        Args:
            username: User's username

        Returns:
            Dictionary with secret, QR code, and backup codes
        """
        secret = self.generate_secret()
        qr_code = self.generate_qr_code(username, secret)
        backup_codes = self.generate_backup_codes()

        # Hash backup codes for storage
        hashed_codes = [self.hash_backup_code(code) for code in backup_codes]

        return {
            "secret": secret,
            "qr_code": qr_code,
            "backup_codes": backup_codes,
            "hashed_backup_codes": hashed_codes,
            "issuer": self.issuer_name,
            "algorithm": "SHA1",
            "digits": 6,
            "period": 30,
        }

    def get_current_token(self, secret: str) -> str:
        """Get current TOTP token (for testing).

        Args:
            secret: TOTP secret

        Returns:
            Current 6-digit token
        """
        totp = pyotp.TOTP(secret)
        return totp.now()

    def get_remaining_seconds(self, secret: str) -> int:
        """Get seconds remaining for current token.

        Args:
            secret: TOTP secret

        Returns:
            Seconds until token expires
        """
        totp = pyotp.TOTP(secret)
        return totp.interval - (datetime.now().timestamp() % totp.interval)


class TwoFactorSession:
    """Manages 2FA session state and verification attempts."""

    def __init__(self, max_attempts: int = 3, lockout_duration: int = 300):
        """Initialize 2FA session manager.

        Args:
            max_attempts: Maximum verification attempts before lockout
            lockout_duration: Lockout duration in seconds
        """
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.sessions: Dict[str, Dict] = {}

    def create_session(self, user_id: str, challenge_type: str = "totp") -> str:
        """Create a new 2FA challenge session.

        Args:
            user_id: User identifier
            challenge_type: Type of 2FA challenge (totp, backup_code)

        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "user_id": user_id,
            "challenge_type": challenge_type,
            "attempts": 0,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=5),
            "locked_until": None,
        }
        return session_id

    def verify_session(self, session_id: str) -> Optional[Dict]:
        """Verify and get session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data if valid, None otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return None

        # Check expiration
        if datetime.now() > session["expires_at"]:
            del self.sessions[session_id]
            return None

        # Check lockout
        if session["locked_until"] and datetime.now() < session["locked_until"]:
            return None

        return session

    def record_attempt(self, session_id: str, success: bool) -> bool:
        """Record a verification attempt.

        Args:
            session_id: Session identifier
            success: Whether attempt was successful

        Returns:
            True if session is still valid, False if locked out
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        if success:
            # Clear session on success
            del self.sessions[session_id]
            return True

        # Increment attempts
        session["attempts"] += 1

        # Check for lockout
        if session["attempts"] >= self.max_attempts:
            session["locked_until"] = datetime.now() + timedelta(
                seconds=self.lockout_duration
            )
            return False

        return True

    def clear_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        expired = [
            sid for sid, session in self.sessions.items() if now > session["expires_at"]
        ]
        for sid in expired:
            del self.sessions[sid]
