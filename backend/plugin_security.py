"""Plugin Security and Signing System

Provides cryptographic signing and verification for plugins to ensure authenticity
and integrity of plugin packages.

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
import hashlib
import json
import os
import secrets
import zipfile
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


class SignatureAlgorithm(Enum):
    """Supported signature algorithms."""

    RSA_PSS_SHA256 = "RSA-PSS-SHA256"
    RSA_PKCS1_SHA256 = "RSA-PKCS1-SHA256"


class TrustLevel(Enum):
    """Plugin trust levels."""

    OFFICIAL = "official"  # Signed by official Kasa Monitor key
    VERIFIED = "verified"  # Signed by verified developer
    COMMUNITY = "community"  # Signed by community member
    UNSIGNED = "unsigned"  # No signature verification
    INVALID = "invalid"  # Invalid or tampered signature


class PluginSigner:
    """Handles plugin signing operations."""

    def __init__(self, private_key_path: Optional[str] = None):
        """Initialize plugin signer.

        Args:
            private_key_path: Path to private key file
        """
        self.private_key_path = private_key_path
        self.private_key = None

        if private_key_path and Path(private_key_path).exists():
            self.load_private_key(private_key_path)

    def generate_key_pair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """Generate a new RSA key pair.

        Args:
            key_size: Size of the RSA key in bits

        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        # Generate private key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )

        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    def load_private_key(self, key_path: str, password: Optional[bytes] = None):
        """Load private key from file.

        Args:
            key_path: Path to private key file
            password: Password for encrypted key (optional)
        """
        with open(key_path, "rb") as key_file:
            self.private_key = serialization.load_pem_private_key(
                key_file.read(), password=password
            )

    def sign_plugin(
        self,
        plugin_path: str,
        output_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Sign a plugin package.

        Args:
            plugin_path: Path to plugin ZIP file
            output_path: Output path for signed plugin (optional)
            metadata: Additional metadata to include in signature

        Returns:
            Path to signed plugin file
        """
        if not self.private_key:
            raise ValueError("No private key loaded")

        if not output_path:
            base_path = Path(plugin_path)
            output_path = str(
                base_path.parent / f"{base_path.stem}_signed{base_path.suffix}"
            )

        # Calculate plugin hash
        plugin_hash = self._calculate_file_hash(plugin_path)

        # Create signature metadata
        signature_data = {
            "version": "1.0",
            "algorithm": SignatureAlgorithm.RSA_PSS_SHA256.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "plugin_hash": plugin_hash,
            "signer": metadata.get("signer", "Unknown") if metadata else "Unknown",
            "metadata": metadata or {},
        }

        # Create signature
        signature_json = json.dumps(signature_data, sort_keys=True)
        signature_bytes = signature_json.encode("utf-8")

        signature = self.private_key.sign(
            signature_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )

        # Create signed plugin
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as signed_zip:
            # Copy original plugin contents
            with zipfile.ZipFile(plugin_path, "r") as original_zip:
                for item in original_zip.infolist():
                    data = original_zip.read(item.filename)
                    signed_zip.writestr(item, data)

            # Add signature files
            signed_zip.writestr("SIGNATURE.json", signature_json)
            signed_zip.writestr(
                "SIGNATURE.sig", base64.b64encode(signature).decode("utf-8")
            )

        return output_path

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


class PluginVerifier:
    """Handles plugin signature verification."""

    def __init__(self, trusted_keys_dir: str = "./keys/trusted"):
        """Initialize plugin verifier.

        Args:
            trusted_keys_dir: Directory containing trusted public keys
        """
        self.trusted_keys_dir = Path(trusted_keys_dir)
        self.trusted_keys_dir.mkdir(parents=True, exist_ok=True)
        self.trusted_keys = {}
        self.load_trusted_keys()

    def load_trusted_keys(self):
        """Load all trusted public keys."""
        self.trusted_keys = {}

        for key_file in self.trusted_keys_dir.glob("*.pem"):
            try:
                with open(key_file, "rb") as f:
                    public_key = serialization.load_pem_public_key(f.read())
                    key_name = key_file.stem
                    self.trusted_keys[key_name] = public_key
            except Exception as e:
                print(f"Failed to load trusted key {key_file}: {e}")

    def add_trusted_key(self, key_name: str, public_key_pem: bytes) -> bool:
        """Add a trusted public key.

        Args:
            key_name: Name for the key
            public_key_pem: PEM-encoded public key

        Returns:
            True if key was added successfully
        """
        try:
            public_key = serialization.load_pem_public_key(public_key_pem)
            key_path = self.trusted_keys_dir / f"{key_name}.pem"

            with open(key_path, "wb") as f:
                f.write(public_key_pem)

            self.trusted_keys[key_name] = public_key
            return True
        except Exception as e:
            print(f"Failed to add trusted key {key_name}: {e}")
            return False

    def verify_plugin(self, plugin_path: str) -> Dict[str, Any]:
        """Verify a plugin's signature.

        Args:
            plugin_path: Path to plugin file

        Returns:
            Verification result dictionary
        """
        result = {
            "verified": False,
            "trust_level": TrustLevel.UNSIGNED,
            "signature_valid": False,
            "signer": None,
            "timestamp": None,
            "errors": [],
        }

        try:
            with zipfile.ZipFile(plugin_path, "r") as plugin_zip:
                # Check if signature files exist
                if "SIGNATURE.json" not in plugin_zip.namelist():
                    result["errors"].append("No signature found")
                    return result

                if "SIGNATURE.sig" not in plugin_zip.namelist():
                    result["errors"].append("Signature file missing")
                    return result

                # Read signature data
                signature_json = plugin_zip.read("SIGNATURE.json").decode("utf-8")
                signature_b64 = plugin_zip.read("SIGNATURE.sig").decode("utf-8")
                signature_data = json.loads(signature_json)
                signature = base64.b64decode(signature_b64)

                result["signer"] = signature_data.get("signer")
                result["timestamp"] = signature_data.get("timestamp")

                # Verify signature against trusted keys
                signature_bytes = signature_json.encode("utf-8")

                for key_name, public_key in self.trusted_keys.items():
                    try:
                        # Use constant-time comparison for algorithm verification
                        provided_algo = signature_data.get("algorithm", "")
                        expected_algo = SignatureAlgorithm.RSA_PSS_SHA256.value
                        if secrets.compare_digest(
                            str(provided_algo), str(expected_algo)
                        ):
                            public_key.verify(
                                signature,
                                signature_bytes,
                                padding.PSS(
                                    mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=padding.PSS.MAX_LENGTH,
                                ),
                                hashes.SHA256(),
                            )
                        else:
                            # Fallback to PKCS1v15
                            public_key.verify(
                                signature,
                                signature_bytes,
                                padding.PKCS1v15(),
                                hashes.SHA256(),
                            )

                        result["verified"] = True
                        result["signature_valid"] = True
                        result["trust_level"] = self._determine_trust_level(key_name)
                        result["verified_by"] = key_name
                        break

                    except InvalidSignature:
                        continue
                    except Exception as e:
                        result["errors"].append(
                            f"Verification error with key {key_name}: {str(e)}"
                        )

                if not result["signature_valid"]:
                    result["errors"].append(
                        "Signature verification failed with all trusted keys"
                    )
                    result["trust_level"] = TrustLevel.INVALID

        except zipfile.BadZipFile:
            result["errors"].append("Invalid ZIP file")
        except json.JSONDecodeError:
            result["errors"].append("Invalid signature format")
        except Exception as e:
            result["errors"].append(f"Verification error: {str(e)}")

        return result

    def _determine_trust_level(self, key_name: str) -> TrustLevel:
        """Determine trust level based on key name.

        Args:
            key_name: Name of the signing key

        Returns:
            Trust level
        """
        if key_name.startswith("official_"):
            return TrustLevel.OFFICIAL
        elif key_name.startswith("verified_"):
            return TrustLevel.VERIFIED
        else:
            return TrustLevel.COMMUNITY


class PluginSecurityManager:
    """Manages overall plugin security policies."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize security manager.

        Args:
            config: Security configuration
        """
        self.config = config or {}
        self.verifier = PluginVerifier()

        # Default security policies
        self.default_policies = {
            "require_signature": False,
            "minimum_trust_level": TrustLevel.UNSIGNED,
            "allow_unsigned": True,
            "verify_on_load": True,
            "quarantine_invalid": True,
        }

        self.policies = {**self.default_policies, **self.config.get("policies", {})}

    def check_plugin_security(self, plugin_path: str) -> Dict[str, Any]:
        """Check if a plugin meets security requirements.

        Args:
            plugin_path: Path to plugin file

        Returns:
            Security check result
        """
        result = {
            "allowed": False,
            "trust_level": TrustLevel.UNSIGNED,
            "verification": None,
            "warnings": [],
            "errors": [],
        }

        # Verify signature if required or if signature exists
        verification = self.verifier.verify_plugin(plugin_path)
        result["verification"] = verification
        result["trust_level"] = verification["trust_level"]

        # Check against policies
        if self.policies["require_signature"] and not verification["verified"]:
            result["errors"].append("Signature required but not found or invalid")
            return result

        # Check minimum trust level
        min_trust = self.policies["minimum_trust_level"]
        if isinstance(min_trust, str):
            min_trust = TrustLevel(min_trust)

        trust_hierarchy = {
            TrustLevel.OFFICIAL: 4,
            TrustLevel.VERIFIED: 3,
            TrustLevel.COMMUNITY: 2,
            TrustLevel.UNSIGNED: 1,
            TrustLevel.INVALID: 0,
        }

        if trust_hierarchy[verification["trust_level"]] < trust_hierarchy[min_trust]:
            result["errors"].append(
                f"Plugin trust level {verification['trust_level'].value} below minimum {min_trust.value}"
            )
            return result

        # Check if unsigned plugins are allowed
        if (
            not self.policies["allow_unsigned"]
            and verification["trust_level"] == TrustLevel.UNSIGNED
        ):
            result["errors"].append("Unsigned plugins not allowed")
            return result

        # Add warnings for lower trust levels
        if verification["trust_level"] == TrustLevel.UNSIGNED:
            result["warnings"].append("Plugin is not signed - use at your own risk")
        elif verification["trust_level"] == TrustLevel.COMMUNITY:
            result["warnings"].append(
                "Plugin signed by community member - verify source"
            )

        result["allowed"] = True
        return result

    def update_policies(self, new_policies: Dict[str, Any]) -> bool:
        """Update security policies.

        Args:
            new_policies: New policy configuration

        Returns:
            True if update successful
        """
        try:
            self.policies.update(new_policies)
            return True
        except Exception as e:
            print(f"Failed to update security policies: {e}")
            return False

    def get_policies(self) -> Dict[str, Any]:
        """Get current security policies.

        Returns:
            Current policies
        """
        return self.policies.copy()

    def export_public_key(self, key_name: str) -> Optional[str]:
        """Export a public key for sharing.

        Args:
            key_name: Name of the key

        Returns:
            PEM-encoded public key or None
        """
        if key_name in self.verifier.trusted_keys:
            public_key = self.verifier.trusted_keys[key_name]
            return public_key.public_bytes(
                encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
            ).decode("utf-8")
        return None
