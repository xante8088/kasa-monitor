"""SSL Certificate Management with CSR generation and file operations.

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

import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SSLCertificateManager:
    """Manages SSL certificate generation, storage, and file operations."""

    def __init__(self, ssl_dir: str = "/app/ssl"):
        """Initialize SSL manager with directory path."""
        self.ssl_dir = Path(ssl_dir)
        self.ssl_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
        
    def generate_private_key(self, key_size: int = 2048) -> str:
        """Generate RSA private key and return as PEM string."""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size
            )
            
            # Serialize to PEM format
            pem_private_key = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            return pem_private_key.decode('utf-8')
            
        except ImportError:
            logger.error("cryptography package required for key generation")
            raise Exception("cryptography package not installed")
        except Exception as e:
            logger.error(f"Failed to generate private key: {e}")
            raise

    def generate_csr(self, 
                    private_key_pem: str,
                    country: str,
                    state: str,
                    city: str,
                    organization: str,
                    organizational_unit: str,
                    common_name: str,
                    email: str,
                    san_domains: Optional[List[str]] = None) -> str:
        """Generate Certificate Signing Request (CSR) and return as PEM string."""
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.x509.oid import ExtensionOID, NameOID

            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )
            
            # Build subject name
            subject_components = []
            if country:
                subject_components.append(x509.NameAttribute(NameOID.COUNTRY_NAME, country))
            if state:
                subject_components.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state))
            if city:
                subject_components.append(x509.NameAttribute(NameOID.LOCALITY_NAME, city))
            if organization:
                subject_components.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))
            if organizational_unit:
                subject_components.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, organizational_unit))
            if common_name:
                subject_components.append(x509.NameAttribute(NameOID.COMMON_NAME, common_name))
            if email:
                subject_components.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, email))
                
            subject = x509.Name(subject_components)
            
            # Create CSR builder
            csr_builder = x509.CertificateSigningRequestBuilder()
            csr_builder = csr_builder.subject_name(subject)
            
            # Add Subject Alternative Names if provided
            if san_domains:
                san_list = [x509.DNSName(domain.strip()) for domain in san_domains if domain.strip()]
                if san_list:
                    csr_builder = csr_builder.add_extension(
                        x509.SubjectAlternativeName(san_list),
                        critical=False
                    )
            
            # Sign the CSR
            csr = csr_builder.sign(private_key, hashes.SHA256())
            
            # Serialize to PEM format
            pem_csr = csr.public_bytes(serialization.Encoding.PEM)
            
            return pem_csr.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to generate CSR: {e}")
            raise

    def save_private_key(self, private_key_pem: str, filename: str = "private.key") -> str:
        """Save private key to file and return file path."""
        try:
            file_path = self.ssl_dir / filename
            
            with open(file_path, 'w') as f:
                f.write(private_key_pem)
            
            # Set secure permissions (readable only by owner)
            os.chmod(file_path, 0o600)
            
            logger.info(f"Private key saved to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save private key: {e}")
            raise

    def save_csr(self, csr_pem: str, filename: str = "certificate.csr") -> str:
        """Save CSR to file and return file path."""
        try:
            file_path = self.ssl_dir / filename
            
            with open(file_path, 'w') as f:
                f.write(csr_pem)
            
            # Set standard permissions
            os.chmod(file_path, 0o644)
            
            logger.info(f"CSR saved to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save CSR: {e}")
            raise

    def generate_csr_and_key(self,
                           country: str,
                           state: str,
                           city: str,
                           organization: str,
                           organizational_unit: str,
                           common_name: str,
                           email: str,
                           san_domains: Optional[List[str]] = None,
                           key_size: int = 2048) -> Tuple[str, str]:
        """Generate both private key and CSR, save to files, return file paths."""
        try:
            # Generate private key
            private_key_pem = self.generate_private_key(key_size)
            
            # Generate CSR
            csr_pem = self.generate_csr(
                private_key_pem=private_key_pem,
                country=country,
                state=state,
                city=city,
                organization=organization,
                organizational_unit=organizational_unit,
                common_name=common_name,
                email=email,
                san_domains=san_domains
            )
            
            # Generate timestamped filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            key_filename = f"private_key_{timestamp}.key"
            csr_filename = f"certificate_{timestamp}.csr"
            
            # Save files
            key_path = self.save_private_key(private_key_pem, key_filename)
            csr_path = self.save_csr(csr_pem, csr_filename)
            
            return key_path, csr_path
            
        except Exception as e:
            logger.error(f"Failed to generate CSR and key: {e}")
            raise

    def list_ssl_files(self) -> List[Dict[str, str]]:
        """List all SSL files in the directory."""
        files = []
        
        try:
            for file_path in self.ssl_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.key', '.csr', '.crt', '.pem']:
                    stat = file_path.stat()
                    files.append({
                        'filename': file_path.name,
                        'path': str(file_path),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'type': self._get_file_type(file_path.suffix)
                    })
                    
        except Exception as e:
            logger.error(f"Failed to list SSL files: {e}")
            
        return sorted(files, key=lambda x: x['modified'], reverse=True)

    def _get_file_type(self, extension: str) -> str:
        """Get human-readable file type from extension."""
        type_map = {
            '.key': 'Private Key',
            '.csr': 'Certificate Signing Request',
            '.crt': 'Certificate',
            '.pem': 'PEM Certificate/Key'
        }
        return type_map.get(extension.lower(), 'SSL File')

    def get_file_content(self, filename: str) -> str:
        """Read and return content of SSL file."""
        try:
            file_path = self.ssl_dir / filename
            
            # Security check: ensure file is within SSL directory
            if not str(file_path.resolve()).startswith(str(self.ssl_dir.resolve())):
                raise ValueError("Invalid file path")
            
            if not file_path.exists():
                raise FileNotFoundError(f"File {filename} not found")
            
            with open(file_path, 'r') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to read file {filename}: {e}")
            raise

    def delete_file(self, filename: str, confirmation_text: str) -> bool:
        """Delete SSL file with confirmation."""
        try:
            # Security check: require exact confirmation text
            if confirmation_text.strip().lower() != "delete":
                raise ValueError("Invalid confirmation text. Type 'delete' to confirm.")
            
            file_path = self.ssl_dir / filename
            
            # Security check: ensure file is within SSL directory
            if not str(file_path.resolve()).startswith(str(self.ssl_dir.resolve())):
                raise ValueError("Invalid file path")
            
            if not file_path.exists():
                raise FileNotFoundError(f"File {filename} not found")
            
            file_path.unlink()
            logger.info(f"SSL file deleted: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {filename}: {e}")
            raise

    def create_zip_archive(self, filenames: List[str]) -> str:
        """Create ZIP archive of selected SSL files and return archive path."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"ssl_files_{timestamp}.zip"
            zip_path = self.ssl_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in filenames:
                    file_path = self.ssl_dir / filename
                    
                    # Security check: ensure file is within SSL directory
                    if not str(file_path.resolve()).startswith(str(self.ssl_dir.resolve())):
                        continue
                        
                    if file_path.exists():
                        zipf.write(file_path, filename)
            
            logger.info(f"ZIP archive created: {zip_filename}")
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Failed to create ZIP archive: {e}")
            raise

    def cleanup_temp_files(self) -> None:
        """Clean up temporary ZIP files older than 1 hour."""
        try:
            import time
            current_time = time.time()
            
            for file_path in self.ssl_dir.glob("ssl_files_*.zip"):
                if file_path.stat().st_mtime < current_time - 3600:  # 1 hour
                    file_path.unlink()
                    logger.info(f"Cleaned up temporary file: {file_path.name}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")