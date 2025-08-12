"""SSL/TLS certificate configuration and management.

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
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SSLConfig:
    """Manages SSL/TLS certificate configuration."""
    
    def __init__(self):
        self.cert_dir = Path(os.getenv("SSL_CERT_DIR", "ssl"))
        self.cert_dir.mkdir(exist_ok=True)
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context if certificates are available."""
        cert_path = os.getenv("SSL_CERT_PATH", self.cert_dir / "cert.pem")
        key_path = os.getenv("SSL_KEY_PATH", self.cert_dir / "key.pem")
        
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            logger.info("SSL certificates not found, running in HTTP mode")
            return None
        
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(cert_path, key_path)
            logger.info("SSL context created successfully")
            return context
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            return None
    
    def install_certificate(self, cert_content: str, key_content: str, ca_content: Optional[str] = None) -> bool:
        """Install SSL certificate files."""
        try:
            cert_path = self.cert_dir / "cert.pem"
            key_path = self.cert_dir / "key.pem"
            
            # Write certificate
            with open(cert_path, 'w') as f:
                f.write(cert_content)
            
            # Write private key
            with open(key_path, 'w') as f:
                f.write(key_content)
            
            # Set secure permissions
            os.chmod(cert_path, 0o644)
            os.chmod(key_path, 0o600)  # Private key should be readable only by owner
            
            # Write CA certificate if provided
            if ca_content:
                ca_path = self.cert_dir / "ca.pem"
                with open(ca_path, 'w') as f:
                    f.write(ca_content)
                os.chmod(ca_path, 0o644)
            
            logger.info("SSL certificates installed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to install certificates: {e}")
            return False
    
    def generate_self_signed_cert(self, hostname: str = "localhost") -> bool:
        """Generate a self-signed certificate for development."""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from datetime import datetime, timedelta
            import ipaddress
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Kasa Monitor"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])
            
            # Build certificate
            cert_builder = x509.CertificateBuilder()
            cert_builder = cert_builder.subject_name(subject)
            cert_builder = cert_builder.issuer_name(issuer)
            cert_builder = cert_builder.public_key(private_key.public_key())
            cert_builder = cert_builder.serial_number(x509.random_serial_number())
            cert_builder = cert_builder.not_valid_before(datetime.utcnow())
            cert_builder = cert_builder.not_valid_after(datetime.utcnow() + timedelta(days=365))
            
            # Add SAN (Subject Alternative Names)
            san_list = [x509.DNSName(hostname)]
            if hostname != "localhost":
                san_list.append(x509.DNSName("localhost"))
            san_list.append(x509.DNSName("127.0.0.1"))
            
            # Try to add IP addresses
            try:
                san_list.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
                if hostname != "localhost":
                    # Try to parse hostname as IP
                    try:
                        san_list.append(x509.IPAddress(ipaddress.ip_address(hostname)))
                    except ValueError:
                        pass
            except Exception:
                pass
            
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False
            )
            
            # Sign certificate
            certificate = cert_builder.sign(private_key, hashes.SHA256())
            
            # Write certificate
            cert_path = self.cert_dir / "cert.pem"
            with open(cert_path, "wb") as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            key_path = self.cert_dir / "key.pem"
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set permissions
            os.chmod(cert_path, 0o644)
            os.chmod(key_path, 0o600)
            
            logger.info(f"Self-signed certificate generated for {hostname}")
            return True
            
        except ImportError:
            logger.error("cryptography package required for certificate generation")
            logger.info("Install with: pip install cryptography")
            return False
        except Exception as e:
            logger.error(f"Failed to generate self-signed certificate: {e}")
            return False
    
    def get_certificate_info(self) -> Optional[Dict[str, Any]]:
        """Get information about installed certificate."""
        cert_path = self.cert_dir / "cert.pem"
        
        if not os.path.exists(cert_path):
            return None
        
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import serialization
            
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            
            certificate = x509.load_pem_x509_certificate(cert_data)
            
            return {
                "subject": certificate.subject.rfc4514_string(),
                "issuer": certificate.issuer.rfc4514_string(),
                "serial_number": str(certificate.serial_number),
                "not_before": certificate.not_valid_before.isoformat(),
                "not_after": certificate.not_valid_after.isoformat(),
                "is_self_signed": certificate.subject == certificate.issuer,
                "algorithm": certificate.signature_algorithm_oid._name,
            }
        
        except Exception as e:
            logger.error(f"Failed to read certificate info: {e}")
            return {"error": str(e)}
    
    def is_https_enabled(self) -> bool:
        """Check if HTTPS is enabled and certificates are available."""
        use_https = os.getenv("USE_HTTPS", "false").lower() == "true"
        
        if not use_https:
            return False
        
        cert_path = self.cert_dir / "cert.pem"
        key_path = self.cert_dir / "key.pem"
        
        return os.path.exists(cert_path) and os.path.exists(key_path)
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration for SSL/TLS."""
        config = {
            "use_https": self.is_https_enabled(),
            "ssl_cert_path": str(self.cert_dir / "cert.pem"),
            "ssl_key_path": str(self.cert_dir / "key.pem"),
            "ssl_ca_path": str(self.cert_dir / "ca.pem"),
        }
        
        if self.is_https_enabled():
            config["certificate_info"] = self.get_certificate_info()
        
        return config