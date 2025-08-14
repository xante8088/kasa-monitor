"""Advanced security features including Fail2ban integration and SSL management.

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
import ssl
import sqlite3
import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import hashlib
import OpenSSL.crypto
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


class Fail2BanIntegration:
    """Integration with Fail2ban for automated IP banning."""
    
    def __init__(self, db_path: str = "kasa_monitor.db", log_path: str = "/var/log/kasa_monitor"):
        """Initialize Fail2ban integration.
        
        Args:
            db_path: Path to database
            log_path: Path to log directory
        """
        self.db_path = db_path
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        self.auth_log = self.log_path / "auth.log"
        self.access_log = self.log_path / "access.log"
        
        self._init_database()
        self._setup_fail2ban_config()
    
    def _init_database(self):
        """Initialize security event tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                username TEXT,
                details TEXT,
                severity TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS banned_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                reason TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                banned_by TEXT,
                is_permanent BOOLEAN DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _setup_fail2ban_config(self):
        """Generate Fail2ban jail configuration."""
        jail_config = """
[kasa-monitor-auth]
enabled = true
filter = kasa-monitor-auth
logpath = /var/log/kasa_monitor/auth.log
maxretry = 5
findtime = 600
bantime = 3600
action = iptables-multiport[name=KasaMonitor, port="80,443,8000"]

[kasa-monitor-api]
enabled = true
filter = kasa-monitor-api
logpath = /var/log/kasa_monitor/access.log
maxretry = 100
findtime = 60
bantime = 3600
action = iptables-multiport[name=KasaMonitorAPI, port="80,443,8000"]
"""
        
        filter_auth = """
[Definition]
failregex = ^.*Failed login attempt from <HOST>.*$
            ^.*Invalid credentials from <HOST>.*$
            ^.*Authentication failed for .* from <HOST>.*$
ignoreregex =
"""
        
        filter_api = """
[Definition]
failregex = ^.*Rate limit exceeded from <HOST>.*$
            ^.*Suspicious activity detected from <HOST>.*$
            ^.*Unauthorized API access from <HOST>.*$
ignoreregex =
"""
        
        # Save configurations (in production, these would go to /etc/fail2ban/)
        config_dir = Path("fail2ban_config")
        config_dir.mkdir(exist_ok=True)
        
        (config_dir / "jail.local").write_text(jail_config)
        (config_dir / "filter.d" / "kasa-monitor-auth.conf").write_text(filter_auth)
        (config_dir / "filter.d" / "kasa-monitor-api.conf").write_text(filter_api)
    
    def log_auth_failure(self, ip: str, username: Optional[str] = None, reason: str = "Invalid credentials"):
        """Log authentication failure for Fail2ban.
        
        Args:
            ip: IP address
            username: Optional username
            reason: Failure reason
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} Failed login attempt from {ip}"
        
        if username:
            log_entry += f" for user {username}"
        log_entry += f": {reason}\n"
        
        # Write to auth log
        with open(self.auth_log, 'a') as f:
            f.write(log_entry)
        
        # Store in database
        self._store_security_event('auth_failure', ip, username=username, details=reason, severity='warning')
    
    def log_rate_limit(self, ip: str, endpoint: str):
        """Log rate limit violation for Fail2ban.
        
        Args:
            ip: IP address
            endpoint: API endpoint
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} Rate limit exceeded from {ip} on endpoint {endpoint}\n"
        
        # Write to access log
        with open(self.access_log, 'a') as f:
            f.write(log_entry)
        
        # Store in database
        self._store_security_event('rate_limit', ip, details=f"Endpoint: {endpoint}", severity='info')
    
    def log_suspicious_activity(self, ip: str, activity: str, severity: str = 'warning'):
        """Log suspicious activity for Fail2ban.
        
        Args:
            ip: IP address
            activity: Description of activity
            severity: Severity level
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} Suspicious activity detected from {ip}: {activity}\n"
        
        # Write to access log
        with open(self.access_log, 'a') as f:
            f.write(log_entry)
        
        # Store in database
        self._store_security_event('suspicious_activity', ip, details=activity, severity=severity)
    
    def _store_security_event(self, event_type: str, ip: str, username: Optional[str] = None,
                             user_agent: Optional[str] = None, details: Optional[str] = None,
                             severity: str = 'info'):
        """Store security event in database.
        
        Args:
            event_type: Type of event
            ip: IP address
            username: Optional username
            user_agent: Optional user agent
            details: Event details
            severity: Event severity
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO security_events 
            (event_type, ip_address, user_agent, username, details, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_type, ip, user_agent, username, details, severity))
        
        conn.commit()
        conn.close()
    
    def ban_ip(self, ip: str, duration_hours: Optional[int] = None, reason: str = "Manual ban"):
        """Manually ban an IP address.
        
        Args:
            ip: IP address to ban
            duration_hours: Ban duration in hours (None for permanent)
            reason: Ban reason
        """
        expires_at = None
        is_permanent = duration_hours is None
        
        if duration_hours:
            expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO banned_ips 
            (ip_address, reason, expires_at, banned_by, is_permanent)
            VALUES (?, ?, ?, 'manual', ?)
        """, (ip, reason, expires_at, is_permanent))
        
        conn.commit()
        conn.close()
        
        # Add to system firewall
        self._update_firewall('ban', ip)
    
    def unban_ip(self, ip: str):
        """Unban an IP address.
        
        Args:
            ip: IP address to unban
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM banned_ips WHERE ip_address = ?
        """, (ip,))
        
        conn.commit()
        conn.close()
        
        # Remove from system firewall
        self._update_firewall('unban', ip)
    
    def _update_firewall(self, action: str, ip: str):
        """Update system firewall rules.
        
        Args:
            action: 'ban' or 'unban'
            ip: IP address
        """
        try:
            if action == 'ban':
                # Using iptables (Linux)
                subprocess.run(['sudo', 'iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'], check=False)
            elif action == 'unban':
                subprocess.run(['sudo', 'iptables', '-D', 'INPUT', '-s', ip, '-j', 'DROP'], check=False)
        except Exception:
            pass  # Firewall update failed, continue anyway
    
    def get_banned_ips(self) -> List[Dict[str, Any]]:
        """Get list of banned IPs.
        
        Returns:
            List of banned IP details
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ip_address, reason, banned_at, expires_at, is_permanent
            FROM banned_ips
            WHERE is_permanent = 1 OR expires_at > CURRENT_TIMESTAMP
        """)
        
        banned = []
        for row in cursor.fetchall():
            banned.append({
                'ip': row[0],
                'reason': row[1],
                'banned_at': row[2],
                'expires_at': row[3],
                'is_permanent': bool(row[4])
            })
        
        conn.close()
        return banned


class SSLCertificateManager:
    """SSL/TLS certificate management."""
    
    def __init__(self, cert_dir: str = "/etc/kasa_monitor/certs"):
        """Initialize SSL certificate manager.
        
        Args:
            cert_dir: Directory for storing certificates
        """
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_self_signed_cert(self, 
                                 domain: str,
                                 days: int = 365) -> Tuple[str, str]:
        """Generate self-signed certificate.
        
        Args:
            domain: Domain name
            days: Validity period in days
            
        Returns:
            Tuple of (cert_path, key_path)
        """
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Kasa Monitor"),
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}"),
            ]),
            critical=False,
        ).sign(key, hashes.SHA256(), backend=default_backend())
        
        # Save certificate
        cert_path = self.cert_dir / f"{domain}.crt"
        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Save private key
        key_path = self.cert_dir / f"{domain}.key"
        with open(key_path, 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Set appropriate permissions
        os.chmod(key_path, 0o600)
        
        return str(cert_path), str(key_path)
    
    def verify_certificate(self, cert_path: str) -> Dict[str, Any]:
        """Verify and get certificate information.
        
        Args:
            cert_path: Path to certificate file
            
        Returns:
            Certificate information
        """
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, backend=default_backend())
            
            # Check expiration
            now = datetime.utcnow()
            is_expired = now > cert.not_valid_after
            days_until_expiry = (cert.not_valid_after - now).days
            
            # Get subject info
            subject = cert.subject
            common_name = None
            for attribute in subject:
                if attribute.oid == NameOID.COMMON_NAME:
                    common_name = attribute.value
                    break
            
            # Get SANs
            sans = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                sans = [san.value for san in san_ext.value]
            except x509.ExtensionNotFound:
                pass
            
            return {
                'valid': not is_expired,
                'common_name': common_name,
                'issuer': cert.issuer.rfc4514_string(),
                'not_before': cert.not_valid_before.isoformat(),
                'not_after': cert.not_valid_after.isoformat(),
                'days_until_expiry': days_until_expiry,
                'is_expired': is_expired,
                'serial_number': str(cert.serial_number),
                'signature_algorithm': cert.signature_algorithm_oid._name,
                'sans': sans
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def check_expiry_alerts(self, days_warning: int = 30) -> List[Dict[str, Any]]:
        """Check for certificates nearing expiry.
        
        Args:
            days_warning: Days before expiry to warn
            
        Returns:
            List of certificates nearing expiry
        """
        expiring_certs = []
        
        for cert_file in self.cert_dir.glob("*.crt"):
            info = self.verify_certificate(str(cert_file))
            
            if info['valid'] and info['days_until_expiry'] <= days_warning:
                expiring_certs.append({
                    'file': cert_file.name,
                    'common_name': info['common_name'],
                    'days_until_expiry': info['days_until_expiry'],
                    'expires_at': info['not_after']
                })
        
        return expiring_certs
    
    def create_csr(self, domain: str, organization: str = "Kasa Monitor") -> str:
        """Create Certificate Signing Request.
        
        Args:
            domain: Domain name
            organization: Organization name
            
        Returns:
            Path to CSR file
        """
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Create CSR
        csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ])).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}"),
            ]),
            critical=False,
        ).sign(key, hashes.SHA256(), backend=default_backend())
        
        # Save CSR
        csr_path = self.cert_dir / f"{domain}.csr"
        with open(csr_path, 'wb') as f:
            f.write(csr.public_bytes(serialization.Encoding.PEM))
        
        # Save private key
        key_path = self.cert_dir / f"{domain}.key"
        with open(key_path, 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        os.chmod(key_path, 0o600)
        
        return str(csr_path)


class SessionManager:
    """Session management with security features."""
    
    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize session manager.
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize session tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Set default configuration
        defaults = {
            'session_timeout_minutes': '30',
            'max_concurrent_sessions': '3',
            'require_same_ip': 'false',
            'require_same_user_agent': 'true'
        }
        
        for key, value in defaults.items():
            cursor.execute("""
                INSERT OR IGNORE INTO session_config (key, value)
                VALUES (?, ?)
            """, (key, value))
        
        conn.commit()
        conn.close()
    
    def create_session(self, user_id: int, ip: str, user_agent: str) -> str:
        """Create new session.
        
        Args:
            user_id: User ID
            ip: IP address
            user_agent: User agent string
            
        Returns:
            Session ID
        """
        import secrets
        
        session_id = secrets.token_urlsafe(32)
        
        # Get timeout configuration
        timeout_minutes = self._get_config('session_timeout_minutes', 30)
        expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
        
        # Check concurrent session limit
        self._enforce_session_limit(user_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_sessions 
            (session_id, user_id, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, user_id, ip, user_agent, expires_at))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def validate_session(self, session_id: str, ip: str, user_agent: str) -> Optional[int]:
        """Validate session.
        
        Args:
            session_id: Session ID
            ip: Current IP address
            user_agent: Current user agent
            
        Returns:
            User ID if valid, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, ip_address, user_agent, expires_at
            FROM user_sessions
            WHERE session_id = ? AND is_active = 1
        """, (session_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        user_id, stored_ip, stored_agent, expires_at = row
        
        # Check expiration
        if datetime.now() > datetime.fromisoformat(expires_at):
            self._invalidate_session(session_id)
            conn.close()
            return None
        
        # Check IP if required
        if self._get_config('require_same_ip', False) and ip != stored_ip:
            self._invalidate_session(session_id)
            conn.close()
            return None
        
        # Check user agent if required
        if self._get_config('require_same_user_agent', True) and user_agent != stored_agent:
            self._invalidate_session(session_id)
            conn.close()
            return None
        
        # Update last activity
        cursor.execute("""
            UPDATE user_sessions
            SET last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
        
        return user_id
    
    def _enforce_session_limit(self, user_id: int):
        """Enforce concurrent session limit.
        
        Args:
            user_id: User ID
        """
        max_sessions = self._get_config('max_concurrent_sessions', 3)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get active sessions
        cursor.execute("""
            SELECT session_id FROM user_sessions
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
        """, (user_id,))
        
        sessions = cursor.fetchall()
        
        # Invalidate oldest sessions if limit exceeded
        if len(sessions) >= max_sessions:
            for session in sessions[max_sessions - 1:]:
                cursor.execute("""
                    UPDATE user_sessions
                    SET is_active = 0
                    WHERE session_id = ?
                """, (session[0],))
        
        conn.commit()
        conn.close()
    
    def _invalidate_session(self, session_id: str):
        """Invalidate a session.
        
        Args:
            session_id: Session ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_sessions
            SET is_active = 0
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
    
    def _get_config(self, key: str, default: Any) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value
            
        Returns:
            Configuration value
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT value FROM session_config WHERE key = ?
        """, (key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            value = row[0]
            # Convert to appropriate type
            if isinstance(default, bool):
                return value.lower() == 'true'
            elif isinstance(default, int):
                return int(value)
            return value
        
        return default