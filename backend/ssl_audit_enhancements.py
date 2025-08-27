"""
SSL Audit Logging Enhancements
Critical audit logging improvements for SSL certificate management

Copyright (C) 2025 Kasa Monitor Contributors
Licensed under GPL v3
"""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# SSL-specific audit event types to add to AuditEventType enum
SSL_AUDIT_EVENTS = {
    "SSL_ENABLED": "ssl.enabled",
    "SSL_DISABLED": "ssl.disabled",
    "SSL_CERT_UPLOADED": "ssl.cert_uploaded",
    "SSL_KEY_UPLOADED": "ssl.key_uploaded",
    "SSL_CERT_VALIDATED": "ssl.cert_validated",
    "SSL_CONFIG_CHANGED": "ssl.config_changed",
    "SSL_STARTUP_SUCCESS": "ssl.startup_success",
    "SSL_STARTUP_FAILURE": "ssl.startup_failure",
    "SSL_CERT_EXPIRED": "ssl.cert_expired",
    "SSL_SECURITY_SCAN": "ssl.security_scan",
}


class SSLCertificateValidator:
    """Validates SSL certificates and extracts metadata for audit logging."""

    @staticmethod
    def extract_certificate_metadata(cert_path: Path) -> Dict[str, Any]:
        """
        Extract certificate metadata for audit logging.

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary containing certificate metadata
        """
        try:
            import ssl
            import subprocess

            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes

            # Read certificate
            with open(cert_path, "rb") as f:
                cert_data = f.read()

            # Parse certificate
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            # Extract metadata
            metadata = {
                "subject": {"common_name": None, "organization": None, "country": None},
                "issuer": {"common_name": None, "organization": None, "country": None},
                "validity": {
                    "not_before": cert.not_valid_before.isoformat(),
                    "not_after": cert.not_valid_after.isoformat(),
                    "is_expired": datetime.utcnow() > cert.not_valid_after,
                    "days_until_expiry": (
                        cert.not_valid_after - datetime.utcnow()
                    ).days,
                },
                "serial_number": format(cert.serial_number, "x"),
                "version": cert.version.name,
                "signature_algorithm": cert.signature_algorithm_oid._name,
                "fingerprints": {
                    "sha256": cert.fingerprint(hashes.SHA256()).hex(),
                    "sha1": cert.fingerprint(hashes.SHA1()).hex(),
                },
                "key_info": {"algorithm": None, "key_size": None},
                "extensions": {"is_ca": False, "san": [], "key_usage": []},
                "self_signed": False,
                "file_info": {
                    "path": str(cert_path),
                    "size": len(cert_data),
                    "hash": hashlib.sha256(cert_data).hexdigest(),
                },
            }

            # Extract subject details
            for attr in cert.subject:
                if attr.oid._name == "commonName":
                    metadata["subject"]["common_name"] = attr.value
                elif attr.oid._name == "organizationName":
                    metadata["subject"]["organization"] = attr.value
                elif attr.oid._name == "countryName":
                    metadata["subject"]["country"] = attr.value

            # Extract issuer details
            for attr in cert.issuer:
                if attr.oid._name == "commonName":
                    metadata["issuer"]["common_name"] = attr.value
                elif attr.oid._name == "organizationName":
                    metadata["issuer"]["organization"] = attr.value
                elif attr.oid._name == "countryName":
                    metadata["issuer"]["country"] = attr.value

            # Check if self-signed
            metadata["self_signed"] = cert.subject == cert.issuer

            # Extract key information
            public_key = cert.public_key()
            if hasattr(public_key, "key_size"):
                metadata["key_info"]["key_size"] = public_key.key_size

            # Extract extensions
            try:
                # Subject Alternative Names
                san_ext = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                metadata["extensions"]["san"] = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                pass

            try:
                # Basic Constraints (is CA)
                bc_ext = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.BASIC_CONSTRAINTS
                )
                metadata["extensions"]["is_ca"] = bc_ext.value.ca
            except x509.ExtensionNotFound:
                pass

            try:
                # Key Usage
                ku_ext = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                )
                key_usage = []
                if ku_ext.value.digital_signature:
                    key_usage.append("digital_signature")
                if ku_ext.value.key_encipherment:
                    key_usage.append("key_encipherment")
                metadata["extensions"]["key_usage"] = key_usage
            except x509.ExtensionNotFound:
                pass

            return {"success": True, "metadata": metadata, "validation_passed": True}

        except Exception as e:
            logger.error(f"Failed to extract certificate metadata: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": None,
                "validation_passed": False,
            }

    @staticmethod
    def validate_private_key(key_path: Path) -> Dict[str, Any]:
        """
        Validate private key and extract metadata.

        Args:
            key_path: Path to private key file

        Returns:
            Dictionary containing key metadata
        """
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization

            # Read key file
            with open(key_path, "rb") as f:
                key_data = f.read()

            # Try to load the private key
            try:
                private_key = serialization.load_pem_private_key(
                    key_data, password=None, backend=default_backend()
                )
            except TypeError:
                # Key might be encrypted
                return {
                    "success": False,
                    "error": "Private key is encrypted",
                    "metadata": None,
                }

            # Extract key metadata
            metadata = {
                "algorithm": None,
                "key_size": None,
                "file_info": {
                    "path": str(key_path),
                    "size": len(key_data),
                    "hash": hashlib.sha256(key_data).hexdigest(),
                    "permissions": oct(key_path.stat().st_mode)[-3:],
                },
            }

            # Determine key type and size
            from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa

            if isinstance(private_key, rsa.RSAPrivateKey):
                metadata["algorithm"] = "RSA"
                metadata["key_size"] = private_key.key_size
            elif isinstance(private_key, dsa.DSAPrivateKey):
                metadata["algorithm"] = "DSA"
                metadata["key_size"] = private_key.key_size
            elif isinstance(private_key, ec.EllipticCurvePrivateKey):
                metadata["algorithm"] = "EC"
                metadata["curve"] = private_key.curve.name

            return {"success": True, "metadata": metadata, "validation_passed": True}

        except Exception as e:
            logger.error(f"Failed to validate private key: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": None,
                "validation_passed": False,
            }

    @staticmethod
    def verify_cert_key_match(cert_path: Path, key_path: Path) -> bool:
        """
        Verify that certificate and private key match.

        Args:
            cert_path: Path to certificate file
            key_path: Path to private key file

        Returns:
            True if certificate and key match
        """
        try:
            import subprocess

            # Use OpenSSL to compare modulus
            cert_modulus = (
                subprocess.check_output(
                    ["openssl", "x509", "-modulus", "-noout", "-in", str(cert_path)],
                    stderr=subprocess.PIPE,
                )
                .decode("utf-8")
                .strip()
            )

            key_modulus = (
                subprocess.check_output(
                    ["openssl", "rsa", "-modulus", "-noout", "-in", str(key_path)],
                    stderr=subprocess.PIPE,
                )
                .decode("utf-8")
                .strip()
            )

            return cert_modulus == key_modulus

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to verify cert-key match: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying cert-key match: {e}")
            return False


class SSLAuditLogger:
    """Enhanced SSL audit logging functionality."""

    def __init__(self, audit_logger):
        """
        Initialize SSL audit logger.

        Args:
            audit_logger: Main audit logger instance
        """
        self.audit_logger = audit_logger

    async def log_ssl_enabled(
        self,
        user_id: Optional[int],
        username: Optional[str],
        trigger: str,
        cert_path: str,
        key_path: str,
        previous_state: str = "disabled",
        reason: str = None,
    ):
        """Log SSL enablement event with full context."""
        from audit_logging import AuditEvent, AuditEventType, AuditSeverity

        if not self.audit_logger:
            return

        # Extract certificate metadata for audit
        cert_metadata = SSLCertificateValidator.extract_certificate_metadata(
            Path(cert_path)
        )

        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            username=username or "system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="ssl_configuration",
            resource_id="ssl_status",
            action="SSL enabled",
            details={
                "operation": "ssl_enablement",
                "trigger": trigger,  # "manual", "auto", "startup"
                "previous_state": previous_state,
                "new_state": "enabled",
                "cert_path": cert_path,
                "key_path": key_path,
                "reason": reason or "SSL certificate and key configured",
                "certificate_info": (
                    cert_metadata.get("metadata", {})
                    if cert_metadata["success"]
                    else None
                ),
                "timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
            success=True,
            error_message=None,
        )

        await self.audit_logger.log_event_async(event)

    async def log_ssl_disabled(
        self, user_id: Optional[int], username: Optional[str], reason: str = None
    ):
        """Log SSL disablement event."""
        from audit_logging import AuditEvent, AuditEventType, AuditSeverity

        if not self.audit_logger:
            return

        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            username=username or "system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="ssl_configuration",
            resource_id="ssl_status",
            action="SSL disabled",
            details={
                "operation": "ssl_disablement",
                "previous_state": "enabled",
                "new_state": "disabled",
                "reason": reason or "SSL manually disabled",
                "timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
            success=True,
            error_message=None,
        )

        await self.audit_logger.log_event_async(event)

    async def log_certificate_upload(
        self,
        user_id: int,
        username: str,
        file_path: Path,
        file_size: int,
        upload_result: Dict[str, Any],
        cert_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log certificate upload with comprehensive metadata."""
        from audit_logging import AuditEvent, AuditEventType, AuditSeverity

        if not self.audit_logger:
            return

        # Extract certificate metadata if not provided
        if not cert_metadata:
            cert_validation = SSLCertificateValidator.extract_certificate_metadata(
                file_path
            )
            cert_metadata = cert_validation.get("metadata", {})

        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="ssl_certificate",
            resource_id=str(file_path.name),
            action="SSL certificate uploaded",
            details={
                "operation": "certificate_upload",
                "filename": file_path.name,
                "file_path": str(file_path),
                "file_size": file_size,
                "file_hash": upload_result.get("file_info", {}).get("sha256"),
                "certificate_metadata": cert_metadata,
                "security_scan": {
                    "quarantine_path": upload_result.get("quarantine_path"),
                    "scan_passed": True,
                    "warnings": upload_result.get("warnings", []),
                },
                "upload_timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
            success=True,
            error_message=None,
        )

        await self.audit_logger.log_event_async(event)

    async def log_private_key_upload(
        self,
        user_id: int,
        username: str,
        file_path: Path,
        file_size: int,
        upload_result: Dict[str, Any],
        key_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log private key upload with security context."""
        from audit_logging import AuditEvent, AuditEventType, AuditSeverity

        if not self.audit_logger:
            return

        # Extract key metadata if not provided
        if not key_metadata:
            key_validation = SSLCertificateValidator.validate_private_key(file_path)
            key_metadata = key_validation.get("metadata", {})

        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            severity=AuditSeverity.WARNING,  # Higher severity for private key
            user_id=user_id,
            username=username,
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="ssl_private_key",
            resource_id=str(file_path.name),
            action="SSL private key uploaded",
            details={
                "operation": "private_key_upload",
                "filename": file_path.name,
                "file_path": str(file_path),
                "file_size": file_size,
                "file_hash": upload_result.get("file_info", {}).get("sha256"),
                "key_metadata": key_metadata,
                "permissions_set": "0o600",
                "security_scan": {
                    "quarantine_path": upload_result.get("quarantine_path"),
                    "scan_passed": True,
                    "warnings": upload_result.get("warnings", []),
                },
                "upload_timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
            success=True,
            error_message=None,
        )

        await self.audit_logger.log_event_async(event)

    async def log_ssl_startup(
        self,
        success: bool,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        port: Optional[int] = None,
        error: Optional[str] = None,
        auto_enabled: bool = False,
    ):
        """Log SSL server startup event."""
        from audit_logging import AuditEvent, AuditEventType, AuditSeverity

        if not self.audit_logger:
            return

        # Extract certificate metadata if available
        cert_metadata = None
        if success and cert_path:
            cert_validation = SSLCertificateValidator.extract_certificate_metadata(
                Path(cert_path)
            )
            cert_metadata = cert_validation.get("metadata", {})

        event = AuditEvent(
            event_type=(
                AuditEventType.SYSTEM_STARTUP
                if success
                else AuditEventType.SYSTEM_ERROR
            ),
            severity=AuditSeverity.INFO if success else AuditSeverity.ERROR,
            user_id=None,
            username="system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="ssl_server",
            resource_id=f"port_{port}" if port else None,
            action="SSL server startup" if success else "SSL server startup failed",
            details={
                "operation": "ssl_startup",
                "success": success,
                "cert_path": cert_path,
                "key_path": key_path,
                "port": port,
                "auto_enabled": auto_enabled,
                "certificate_info": cert_metadata if success else None,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
            success=success,
            error_message=error,
        )

        await self.audit_logger.log_event_async(event)

    async def log_security_scan(
        self,
        file_path: str,
        file_type: str,
        scan_result: Dict[str, Any],
        user_id: Optional[int] = None,
        username: Optional[str] = None,
    ):
        """Log security scan results for SSL files."""
        from audit_logging import AuditEvent, AuditEventType, AuditSeverity

        if not self.audit_logger:
            return

        # Determine severity based on scan results
        if not scan_result.get("valid", False):
            severity = AuditSeverity.WARNING
        elif scan_result.get("warnings", []):
            severity = AuditSeverity.INFO
        else:
            severity = AuditSeverity.DEBUG

        event = AuditEvent(
            event_type=(
                AuditEventType.SECURITY_VIOLATION
                if not scan_result.get("valid")
                else AuditEventType.SYSTEM_CONFIG_CHANGED
            ),
            severity=severity,
            user_id=user_id,
            username=username or "system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="ssl_security_scan",
            resource_id=file_path,
            action="SSL file security scan",
            details={
                "operation": "security_scan",
                "file_path": file_path,
                "file_type": file_type,
                "scan_valid": scan_result.get("valid", False),
                "errors": scan_result.get("errors", []),
                "warnings": scan_result.get("warnings", []),
                "file_info": scan_result.get("file_info", {}),
                "timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
            success=scan_result.get("valid", False),
            error_message=(
                "; ".join(scan_result.get("errors", []))
                if not scan_result.get("valid")
                else None
            ),
        )

        await self.audit_logger.log_event_async(event)

    async def log_certificate_expiry_check(
        self,
        cert_path: str,
        days_until_expiry: int,
        is_expired: bool,
        will_expire_soon: bool,
    ):
        """Log certificate expiry check results."""
        from audit_logging import AuditEvent, AuditEventType, AuditSeverity

        if not self.audit_logger:
            return

        # Determine severity
        if is_expired:
            severity = AuditSeverity.CRITICAL
        elif will_expire_soon:
            severity = AuditSeverity.WARNING
        else:
            severity = AuditSeverity.INFO

        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            severity=severity,
            user_id=None,
            username="system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="ssl_certificate",
            resource_id=cert_path,
            action="Certificate expiry check",
            details={
                "operation": "expiry_check",
                "cert_path": cert_path,
                "days_until_expiry": days_until_expiry,
                "is_expired": is_expired,
                "will_expire_soon": will_expire_soon,
                "warning_threshold_days": 30,
                "check_timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
            success=True,
            error_message=None,
        )

        await self.audit_logger.log_event_async(event)


# Helper function to integrate with existing code
async def create_enhanced_ssl_audit_event(
    audit_logger,
    event_type: str,
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    details: Dict[str, Any],
    severity: str = "INFO",
    success: bool = True,
    error_message: Optional[str] = None,
):
    """
    Create an enhanced SSL audit event with comprehensive logging.

    This is a convenience function to be integrated into existing SSL operations.
    """
    from audit_logging import AuditEvent, AuditEventType, AuditSeverity

    if not audit_logger:
        return

    # Map string severity to enum
    severity_map = {
        "DEBUG": AuditSeverity.DEBUG,
        "INFO": AuditSeverity.INFO,
        "WARNING": AuditSeverity.WARNING,
        "ERROR": AuditSeverity.ERROR,
        "CRITICAL": AuditSeverity.CRITICAL,
    }

    # Enhance details with timestamp
    enhanced_details = {
        **details,
        "timestamp": datetime.now().isoformat(),
        "event_category": "ssl",
    }

    event = AuditEvent(
        event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,  # Use existing type for now
        severity=severity_map.get(severity, AuditSeverity.INFO),
        user_id=user_id,
        username=username or "system",
        ip_address=None,
        user_agent=None,
        session_id=None,
        resource_type="ssl",
        resource_id=details.get("resource_id"),
        action=action,
        details=enhanced_details,
        timestamp=datetime.now(),
        success=success,
        error_message=error_message,
    )

    await audit_logger.log_event_async(event)
