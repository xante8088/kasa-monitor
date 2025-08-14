"""Password Policy enforcement and management.

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

import re
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import bcrypt


class PasswordStrength(Enum):
    """Password strength levels."""
    VERY_WEAK = 0
    WEAK = 1
    FAIR = 2
    GOOD = 3
    STRONG = 4
    VERY_STRONG = 5


class PasswordPolicy:
    """Password policy enforcement."""
    
    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize password policy.
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        
        # Default policy settings
        self.default_policy = {
            'min_length': 8,
            'max_length': 128,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_digits': True,
            'require_special': True,
            'min_uppercase': 1,
            'min_lowercase': 1,
            'min_digits': 1,
            'min_special': 1,
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
            'disallow_common': True,
            'disallow_user_info': True,
            'history_count': 5,
            'expiry_days': 90,
            'min_change_interval_hours': 24,
            'max_failed_attempts': 5,
            'lockout_duration_minutes': 30,
            'require_change_on_first_login': True,
            'min_strength': PasswordStrength.FAIR.value
        }
        
        self.common_passwords = self._load_common_passwords()
        self._init_database()
    
    def _init_database(self):
        """Initialize password policy tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Password policies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                policy_data TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Password history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Password expiry tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_expiry (
                user_id INTEGER PRIMARY KEY,
                last_changed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                force_change BOOLEAN DEFAULT 0,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Insert default policy if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO password_policies (name, policy_data, is_default)
            VALUES ('default', ?, 1)
        """, (json.dumps(self.default_policy),))
        
        conn.commit()
        conn.close()
    
    def _load_common_passwords(self) -> set:
        """Load list of common passwords.
        
        Returns:
            Set of common passwords
        """
        # In production, load from a file or database
        # This is a minimal example list
        return {
            'password', '123456', '12345678', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            '1234567890', 'password1', '123456789', 'welcome123',
            'admin123', 'root', 'toor', 'pass', 'pass123', 'password!',
            'Password1', 'Password123', 'Password!', 'P@ssw0rd',
            'qwerty123', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            'iloveyou', 'trustno1', '1234', '12345', '111111',
            '123123', 'abc', 'default', 'guest', 'master'
        }
    
    def get_policy(self, policy_name: str = 'default') -> Dict[str, Any]:
        """Get password policy.
        
        Args:
            policy_name: Name of policy to retrieve
            
        Returns:
            Policy configuration
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT policy_data FROM password_policies
            WHERE name = ? OR (? = 'default' AND is_default = 1)
        """, (policy_name, policy_name))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        
        return self.default_policy
    
    def validate_password(self, 
                         password: str,
                         username: Optional[str] = None,
                         email: Optional[str] = None,
                         policy_name: str = 'default') -> Tuple[bool, List[str]]:
        """Validate password against policy.
        
        Args:
            password: Password to validate
            username: Optional username for context
            email: Optional email for context
            policy_name: Policy to use
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        policy = self.get_policy(policy_name)
        errors = []
        
        # Length checks
        if len(password) < policy['min_length']:
            errors.append(f"Password must be at least {policy['min_length']} characters long")
        
        if len(password) > policy['max_length']:
            errors.append(f"Password must be no more than {policy['max_length']} characters long")
        
        # Character type requirements
        uppercase_count = sum(1 for c in password if c.isupper())
        lowercase_count = sum(1 for c in password if c.islower())
        digit_count = sum(1 for c in password if c.isdigit())
        special_count = sum(1 for c in password if c in policy['special_chars'])
        
        if policy['require_uppercase'] and uppercase_count < policy['min_uppercase']:
            errors.append(f"Password must contain at least {policy['min_uppercase']} uppercase letter(s)")
        
        if policy['require_lowercase'] and lowercase_count < policy['min_lowercase']:
            errors.append(f"Password must contain at least {policy['min_lowercase']} lowercase letter(s)")
        
        if policy['require_digits'] and digit_count < policy['min_digits']:
            errors.append(f"Password must contain at least {policy['min_digits']} digit(s)")
        
        if policy['require_special'] and special_count < policy['min_special']:
            errors.append(f"Password must contain at least {policy['min_special']} special character(s)")
        
        # Common password check
        if policy['disallow_common'] and password.lower() in self.common_passwords:
            errors.append("Password is too common and easily guessable")
        
        # User info check
        if policy['disallow_user_info']:
            if username and username.lower() in password.lower():
                errors.append("Password cannot contain your username")
            
            if email:
                email_parts = email.lower().split('@')[0].split('.')
                for part in email_parts:
                    if len(part) > 3 and part in password.lower():
                        errors.append("Password cannot contain parts of your email address")
        
        # Check password strength
        strength = self.calculate_strength(password)
        if strength.value < policy['min_strength']:
            errors.append(f"Password strength is too weak (minimum: {PasswordStrength(policy['min_strength']).name})")
        
        return len(errors) == 0, errors
    
    def calculate_strength(self, password: str) -> PasswordStrength:
        """Calculate password strength.
        
        Args:
            password: Password to analyze
            
        Returns:
            Password strength level
        """
        score = 0
        
        # Length scoring
        length = len(password)
        if length >= 8:
            score += 1
        if length >= 12:
            score += 1
        if length >= 16:
            score += 1
        if length >= 20:
            score += 1
        
        # Character diversity
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[^a-zA-Z0-9]', password))
        
        diversity = sum([has_lower, has_upper, has_digit, has_special])
        score += diversity
        
        # Pattern checks (reduce score for patterns)
        if re.search(r'(.)\1{2,}', password):  # Repeated characters
            score -= 1
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):  # Sequential numbers
            score -= 1
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):  # Sequential letters
            score -= 1
        
        # Common patterns
        if password.lower() in self.common_passwords:
            score = 0
        
        # Map score to strength
        if score <= 2:
            return PasswordStrength.VERY_WEAK
        elif score <= 4:
            return PasswordStrength.WEAK
        elif score <= 6:
            return PasswordStrength.FAIR
        elif score <= 8:
            return PasswordStrength.GOOD
        elif score <= 10:
            return PasswordStrength.STRONG
        else:
            return PasswordStrength.VERY_STRONG
    
    def check_password_history(self, user_id: int, new_password: str, history_count: Optional[int] = None) -> bool:
        """Check if password was recently used.
        
        Args:
            user_id: User ID
            new_password: New password to check
            history_count: Number of previous passwords to check
            
        Returns:
            True if password is not in history, False if it was recently used
        """
        if history_count is None:
            policy = self.get_policy()
            history_count = policy.get('history_count', 5)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT password_hash FROM password_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, history_count))
        
        for row in cursor.fetchall():
            stored_hash = row[0]
            if bcrypt.checkpw(new_password.encode('utf-8'), stored_hash.encode('utf-8')):
                conn.close()
                return False
        
        conn.close()
        return True
    
    def add_to_history(self, user_id: int, password_hash: str):
        """Add password to history.
        
        Args:
            user_id: User ID
            password_hash: Hashed password
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO password_history (user_id, password_hash)
            VALUES (?, ?)
        """, (user_id, password_hash))
        
        # Clean old history entries (keep last 20)
        cursor.execute("""
            DELETE FROM password_history
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM password_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 20
            )
        """, (user_id, user_id))
        
        conn.commit()
        conn.close()
    
    def check_expiry(self, user_id: int) -> Tuple[bool, Optional[datetime]]:
        """Check if user's password is expired.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (is_expired, expiry_date)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT expires_at, force_change FROM password_expiry
            WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False, None
        
        expires_at, force_change = row
        
        if force_change:
            return True, None
        
        if expires_at:
            expiry_date = datetime.fromisoformat(expires_at)
            return datetime.now() > expiry_date, expiry_date
        
        return False, None
    
    def set_password_expiry(self, user_id: int, days: Optional[int] = None):
        """Set password expiry for a user.
        
        Args:
            user_id: User ID
            days: Days until expiry (None uses policy default)
        """
        if days is None:
            policy = self.get_policy()
            days = policy.get('expiry_days', 90)
        
        expires_at = datetime.now() + timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO password_expiry 
            (user_id, last_changed, expires_at, force_change)
            VALUES (?, CURRENT_TIMESTAMP, ?, 0)
        """, (user_id, expires_at))
        
        conn.commit()
        conn.close()
    
    def force_password_change(self, user_id: int):
        """Force user to change password on next login.
        
        Args:
            user_id: User ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO password_expiry 
            (user_id, force_change)
            VALUES (?, 1)
        """, (user_id,))
        
        conn.commit()
        conn.close()
    
    def record_failed_attempt(self, user_id: int) -> Tuple[bool, Optional[datetime]]:
        """Record failed login attempt.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (is_locked, locked_until)
        """
        policy = self.get_policy()
        max_attempts = policy.get('max_failed_attempts', 5)
        lockout_minutes = policy.get('lockout_duration_minutes', 30)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current failed attempts
        cursor.execute("""
            SELECT failed_attempts, locked_until FROM password_expiry
            WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        
        if row:
            failed_attempts, locked_until = row
            
            # Check if currently locked
            if locked_until:
                locked_until_dt = datetime.fromisoformat(locked_until)
                if datetime.now() < locked_until_dt:
                    conn.close()
                    return True, locked_until_dt
            
            # Increment failed attempts
            failed_attempts = (failed_attempts or 0) + 1
            
            # Check if should lock
            if failed_attempts >= max_attempts:
                locked_until_dt = datetime.now() + timedelta(minutes=lockout_minutes)
                cursor.execute("""
                    UPDATE password_expiry
                    SET failed_attempts = ?, locked_until = ?
                    WHERE user_id = ?
                """, (failed_attempts, locked_until_dt, user_id))
                conn.commit()
                conn.close()
                return True, locked_until_dt
            else:
                cursor.execute("""
                    UPDATE password_expiry
                    SET failed_attempts = ?
                    WHERE user_id = ?
                """, (failed_attempts, user_id))
        else:
            # Create new record
            cursor.execute("""
                INSERT INTO password_expiry (user_id, failed_attempts)
                VALUES (?, 1)
            """, (user_id,))
        
        conn.commit()
        conn.close()
        return False, None
    
    def reset_failed_attempts(self, user_id: int):
        """Reset failed login attempts after successful login.
        
        Args:
            user_id: User ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE password_expiry
            SET failed_attempts = 0, locked_until = NULL
            WHERE user_id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
    
    def generate_secure_password(self, length: int = 16, policy_name: str = 'default') -> str:
        """Generate a secure password that meets policy requirements.
        
        Args:
            length: Desired password length
            policy_name: Policy to comply with
            
        Returns:
            Generated password
        """
        import secrets
        import string
        
        policy = self.get_policy(policy_name)
        
        # Ensure minimum length
        length = max(length, policy['min_length'])
        
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = policy['special_chars']
        
        # Ensure minimum requirements
        password_chars = []
        
        if policy['require_uppercase']:
            for _ in range(policy['min_uppercase']):
                password_chars.append(secrets.choice(uppercase))
        
        if policy['require_lowercase']:
            for _ in range(policy['min_lowercase']):
                password_chars.append(secrets.choice(lowercase))
        
        if policy['require_digits']:
            for _ in range(policy['min_digits']):
                password_chars.append(secrets.choice(digits))
        
        if policy['require_special']:
            for _ in range(policy['min_special']):
                password_chars.append(secrets.choice(special))
        
        # Fill remaining length
        all_chars = lowercase + uppercase + digits + special
        remaining_length = length - len(password_chars)
        
        for _ in range(remaining_length):
            password_chars.append(secrets.choice(all_chars))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)
        
        return ''.join(password_chars)