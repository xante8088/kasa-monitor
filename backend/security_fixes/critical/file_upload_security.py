"""
File Upload Security Fix
Critical Security Fix - Prevents malicious file uploads

Copyright (C) 2025 Kasa Monitor Contributors
Licensed under GPL v3
"""

import hashlib
import os
import shutil
import tempfile

try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)


class SecureFileUploadConfig:
    """Configuration for secure file uploads."""

    def __init__(self):
        self.max_file_size = (
            int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024
        )  # Default 10MB
        self.allowed_extensions = self._load_allowed_extensions()
        self.allowed_mime_types = self._load_allowed_mime_types()
        self.quarantine_dir = Path(os.getenv("UPLOAD_QUARANTINE_DIR", "quarantine"))
        self.require_signature_verification = (
            os.getenv("REQUIRE_PLUGIN_SIGNATURES", "true").lower() == "true"
        )

        # Ensure quarantine directory exists
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _load_allowed_extensions(self) -> List[str]:
        """Load allowed file extensions from environment."""
        env_extensions = os.getenv("ALLOWED_UPLOAD_EXTENSIONS", ".zip,.py,.json")
        return [ext.strip().lower() for ext in env_extensions.split(",") if ext.strip()]

    def _load_allowed_mime_types(self) -> Dict[str, List[str]]:
        """Map file extensions to allowed MIME types."""
        return {
            ".zip": ["application/zip", "application/x-zip-compressed"],
            ".py": ["text/plain", "text/x-python"],
            ".json": ["application/json", "text/plain"],
            ".pem": ["text/plain", "application/x-pem-file"],
            ".crt": ["text/plain", "application/x-x509-ca-cert"],
            ".key": ["text/plain", "application/x-pem-file"],
        }


class FileUploadValidator:
    """Validates uploaded files for security."""

    def __init__(self, config: SecureFileUploadConfig = None):
        self.config = config or SecureFileUploadConfig()

    def validate_file(
        self, file: UploadFile, file_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Comprehensive file validation.

        Args:
            file: FastAPI UploadFile object
            file_type: Type of file (plugin, backup, ssl_cert, ssl_key)

        Returns:
            Dict with validation results
        """
        result = {"valid": False, "errors": [], "warnings": [], "file_info": {}}

        try:
            # 1. Validate filename
            filename_validation = self._validate_filename(file.filename)
            if not filename_validation["valid"]:
                result["errors"].extend(filename_validation["errors"])
                return result

            # 2. Check file size
            file_content = file.file.read()
            file.file.seek(0)  # Reset file pointer

            size_validation = self._validate_file_size(len(file_content))
            if not size_validation["valid"]:
                result["errors"].extend(size_validation["errors"])
                return result

            # 3. Validate file extension
            extension = Path(file.filename).suffix.lower()
            ext_validation = self._validate_extension(extension, file_type)
            if not ext_validation["valid"]:
                result["errors"].extend(ext_validation["errors"])
                return result

            # 4. Validate MIME type
            mime_validation = self._validate_mime_type(file_content, extension)
            if not mime_validation["valid"]:
                result["errors"].extend(mime_validation["errors"])
                return result

            # 5. Scan for malicious content
            content_validation = self._validate_content(
                file_content, extension, file_type
            )
            if not content_validation["valid"]:
                result["errors"].extend(content_validation["errors"])
                result["warnings"].extend(content_validation.get("warnings", []))
                return result

            # 6. Calculate file hash
            file_hash = hashlib.sha256(file_content).hexdigest()

            result.update(
                {
                    "valid": True,
                    "file_info": {
                        "filename": file.filename,
                        "size": len(file_content),
                        "extension": extension,
                        "mime_type": mime_validation.get("detected_mime"),
                        "sha256": file_hash,
                    },
                }
            )

            logger.info(
                f"File validation successful: {file.filename} ({file_hash[:16]})"
            )

        except Exception as e:
            logger.error(f"File validation error: {e}")
            result["errors"].append(f"Validation failed: {str(e)}")

        return result

    def _validate_filename(self, filename: str) -> Dict[str, Any]:
        """Validate filename for security issues."""
        result = {"valid": True, "errors": []}

        if not filename:
            result["errors"].append("Filename is required")
            result["valid"] = False
            return result

        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            result["errors"].append("Filename contains invalid path characters")
            result["valid"] = False

        # Check for null bytes
        if "\0" in filename:
            result["errors"].append("Filename contains null bytes")
            result["valid"] = False

        # Check length
        if len(filename) > 255:
            result["errors"].append("Filename too long (max 255 characters)")
            result["valid"] = False

        # Check for dangerous characters
        dangerous_chars = ["<", ">", ":", "|", "?", "*", '"', "'"]
        if any(char in filename for char in dangerous_chars):
            result["errors"].append("Filename contains dangerous characters")
            result["valid"] = False

        return result

    def _validate_file_size(self, size: int) -> Dict[str, Any]:
        """Validate file size against limits."""
        result = {"valid": True, "errors": []}

        if size == 0:
            result["errors"].append("File is empty")
            result["valid"] = False
        elif size > self.config.max_file_size:
            max_mb = self.config.max_file_size / (1024 * 1024)
            result["errors"].append(f"File too large (max {max_mb}MB)")
            result["valid"] = False

        return result

    def _validate_extension(self, extension: str, file_type: str) -> Dict[str, Any]:
        """Validate file extension against allowed types."""
        result = {"valid": True, "errors": []}

        if not extension:
            result["errors"].append("File has no extension")
            result["valid"] = False
            return result

        # Type-specific validation
        allowed_for_type = self._get_allowed_extensions_for_type(file_type)

        if extension not in allowed_for_type:
            result["errors"].append(
                f"Extension '{extension}' not allowed for {file_type}. "
                f"Allowed: {', '.join(allowed_for_type)}"
            )
            result["valid"] = False

        return result

    def _get_allowed_extensions_for_type(self, file_type: str) -> List[str]:
        """Get allowed extensions for specific file type."""
        type_extensions = {
            "plugin": [".zip"],
            "backup": [".zip", ".7z", ".tar.gz", ".json"],
            "ssl_cert": [".pem", ".crt"],
            "ssl_key": [".pem", ".key"],
            "config": [".json", ".yaml", ".yml"],
            "general": self.config.allowed_extensions,
        }

        return type_extensions.get(file_type, self.config.allowed_extensions)

    def _validate_mime_type(self, content: bytes, extension: str) -> Dict[str, Any]:
        """Validate MIME type matches extension."""
        result = {"valid": True, "errors": [], "detected_mime": None}

        if HAS_MAGIC:
            try:
                # Detect MIME type from content
                detected_mime = magic.from_buffer(content, mime=True)
                result["detected_mime"] = detected_mime

                # Get allowed MIME types for extension
                allowed_mimes = self.config.allowed_mime_types.get(extension, [])

                if allowed_mimes and detected_mime not in allowed_mimes:
                    result["errors"].append(
                        f"MIME type '{detected_mime}' doesn't match extension '{extension}'. "
                        f"Expected: {', '.join(allowed_mimes)}"
                    )
                    result["valid"] = False

            except Exception as e:
                logger.warning(f"MIME type detection failed: {e}")
                # Don't fail validation if MIME detection fails
        else:
            # Fallback: Basic header-based detection
            detected_mime = self._detect_mime_fallback(content, extension)
            result["detected_mime"] = detected_mime

        return result

    def _detect_mime_fallback(self, content: bytes, extension: str) -> str:
        """Fallback MIME type detection without python-magic."""
        # Basic signature detection
        if content.startswith(b"PK"):
            return "application/zip"
        elif content.startswith(b"{\n") or content.startswith(b"{ "):
            return "application/json"
        elif extension in [".pem", ".crt", ".key"]:
            if b"-----BEGIN" in content and b"-----END" in content:
                return "text/plain"

        # Default based on extension
        mime_map = {
            ".zip": "application/zip",
            ".json": "application/json",
            ".py": "text/plain",
            ".pem": "text/plain",
            ".crt": "text/plain",
            ".key": "text/plain",
        }

        return mime_map.get(extension, "application/octet-stream")

    def _validate_content(
        self, content: bytes, extension: str, file_type: str
    ) -> Dict[str, Any]:
        """Validate file content for security issues."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Check for embedded executables (PE/ELF headers)
        if self._contains_executable_headers(content):
            result["errors"].append("File contains executable code")
            result["valid"] = False

        # Check for suspicious strings
        suspicious_strings = [
            b"eval(",
            b"exec(",
            b"__import__",
            b"subprocess",
            b"os.system",
            b"shell=True",
            b"<script",
            b"javascript:",
            b"data:text/html",
        ]

        content_lower = content.lower()
        found_suspicious = []
        for suspicious in suspicious_strings:
            if suspicious in content_lower:
                found_suspicious.append(suspicious.decode("utf-8", errors="ignore"))

        if found_suspicious:
            if file_type == "plugin":
                # For plugins, these might be legitimate but should be flagged
                result["warnings"].append(
                    f"Potentially dangerous code patterns found: {', '.join(found_suspicious)}"
                )
            else:
                result["errors"].append(
                    f"Suspicious content detected: {', '.join(found_suspicious)}"
                )
                result["valid"] = False

        # Type-specific validation
        if extension == ".zip":
            zip_validation = self._validate_zip_content(content)
            result["errors"].extend(zip_validation.get("errors", []))
            result["warnings"].extend(zip_validation.get("warnings", []))
            if not zip_validation["valid"]:
                result["valid"] = False

        return result

    def _contains_executable_headers(self, content: bytes) -> bool:
        """Check if content contains executable file headers."""
        # PE header (Windows executables)
        if content.startswith(b"MZ"):
            return True

        # ELF header (Linux executables)
        if content.startswith(b"\x7fELF"):
            return True

        # Mach-O header (macOS executables)
        if content.startswith(b"\xfe\xed\xfa\xce") or content.startswith(
            b"\xfe\xed\xfa\xcf"
        ):
            return True

        return False

    def _validate_zip_content(self, content: bytes) -> Dict[str, Any]:
        """Validate ZIP file content."""
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            import io
            import zipfile

            with zipfile.ZipFile(io.BytesIO(content), "r") as zip_file:
                # Check for zip bombs
                uncompressed_size = sum(info.file_size for info in zip_file.infolist())
                compression_ratio = (
                    uncompressed_size / len(content) if len(content) > 0 else 0
                )

                if compression_ratio > 100:  # Potential zip bomb
                    result["errors"].append(
                        "Suspicious compression ratio - potential zip bomb"
                    )
                    result["valid"] = False

                # Check for path traversal in zip entries
                for info in zip_file.infolist():
                    if ".." in info.filename or info.filename.startswith("/"):
                        result["errors"].append(
                            f"Zip contains path traversal: {info.filename}"
                        )
                        result["valid"] = False

                # Check total uncompressed size
                max_uncompressed = 100 * 1024 * 1024  # 100MB
                if uncompressed_size > max_uncompressed:
                    result["errors"].append(
                        f"Uncompressed size too large: {uncompressed_size / (1024*1024):.1f}MB"
                    )
                    result["valid"] = False

        except zipfile.BadZipFile:
            result["errors"].append("Invalid or corrupted ZIP file")
            result["valid"] = False
        except Exception as e:
            result["errors"].append(f"ZIP validation error: {str(e)}")
            result["valid"] = False

        return result


class SecureFileUploadManager:
    """Manages secure file uploads with quarantine and validation."""

    def __init__(self, config: SecureFileUploadConfig = None):
        self.config = config or SecureFileUploadConfig()
        self.validator = FileUploadValidator(self.config)

    async def handle_upload(
        self,
        file: UploadFile,
        file_type: str = "general",
        allow_overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Handle a file upload with full security validation.

        Args:
            file: FastAPI UploadFile
            file_type: Type of file being uploaded
            allow_overwrite: Whether to allow overwriting existing files

        Returns:
            Dict with upload results and file info
        """
        # Validate the file
        validation_result = self.validator.validate_file(file, file_type)

        if not validation_result["valid"]:
            logger.warning(
                f"File upload rejected: {file.filename}, errors: {validation_result['errors']}"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "File validation failed",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", []),
                },
            )

        # Save file to quarantine first
        try:
            quarantine_path = await self._save_to_quarantine(
                file, validation_result["file_info"]
            )

            result = {
                "success": True,
                "file_info": validation_result["file_info"],
                "quarantine_path": str(quarantine_path),
                "warnings": validation_result.get("warnings", []),
            }

            logger.info(f"File upload successful: {file.filename} -> {quarantine_path}")
            return result

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    async def _save_to_quarantine(
        self, file: UploadFile, file_info: Dict[str, Any]
    ) -> Path:
        """Save uploaded file to quarantine directory."""
        # Generate safe filename
        safe_filename = self._generate_safe_filename(
            file_info["filename"], file_info["sha256"]
        )
        quarantine_path = self.config.quarantine_dir / safe_filename

        # Ensure we don't overwrite existing files
        counter = 1
        original_path = quarantine_path
        while quarantine_path.exists():
            name = original_path.stem
            suffix = original_path.suffix
            quarantine_path = original_path.parent / f"{name}_{counter}{suffix}"
            counter += 1

        # Save file content
        content = await file.read()
        with open(quarantine_path, "wb") as f:
            f.write(content)

        # Set restrictive permissions
        os.chmod(quarantine_path, 0o600)

        return quarantine_path

    def _generate_safe_filename(self, original_filename: str, file_hash: str) -> str:
        """Generate a safe filename for quarantine storage."""
        # Extract extension
        extension = Path(original_filename).suffix.lower()

        # Create safe name with hash prefix
        safe_name = f"{file_hash[:16]}_{Path(original_filename).stem}"

        # Remove any remaining dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        safe_name = "".join(c for c in safe_name if c in safe_chars)

        return safe_name + extension

    def approve_quarantined_file(self, quarantine_path: str, destination: str) -> bool:
        """Move approved file from quarantine to destination."""
        try:
            src_path = Path(quarantine_path)
            dest_path = Path(destination)

            if not src_path.exists():
                logger.error(f"Quarantined file not found: {quarantine_path}")
                return False

            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file then delete original (handles cross-device links)
            shutil.copy2(src_path, dest_path)
            src_path.unlink()

            logger.info(f"File approved and moved: {quarantine_path} -> {destination}")
            return True

        except Exception as e:
            logger.error(f"Failed to approve quarantined file: {e}")
            return False

    def reject_quarantined_file(self, quarantine_path: str) -> bool:
        """Delete rejected file from quarantine."""
        try:
            src_path = Path(quarantine_path)
            if src_path.exists():
                src_path.unlink()
                logger.info(f"Quarantined file rejected and deleted: {quarantine_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to reject quarantined file: {e}")
            return False


# Decorator for secure file uploads
def require_secure_upload(file_type: str = "general", allow_overwrite: bool = False):
    """Decorator to add secure file upload validation to endpoints."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Find UploadFile parameter
            file_param = None
            for key, value in kwargs.items():
                if isinstance(value, UploadFile):
                    file_param = value
                    break

            if not file_param:
                raise HTTPException(status_code=400, detail="No file provided")

            # Validate upload
            upload_manager = SecureFileUploadManager()
            upload_result = await upload_manager.handle_upload(
                file_param, file_type, allow_overwrite
            )

            # Add upload result to kwargs
            kwargs["upload_result"] = upload_result

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Export configuration and classes
__all__ = [
    "SecureFileUploadConfig",
    "FileUploadValidator",
    "SecureFileUploadManager",
    "require_secure_upload",
]
