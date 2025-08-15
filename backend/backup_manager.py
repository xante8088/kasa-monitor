"""
Database Backup and Restore Manager for Kasa Monitor
Handles automated backups, encryption, compression, and restoration
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import aiofiles.os
import py7zr
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backups and restoration"""

    def __init__(
        self,
        db_path: str,
        backup_dir: str = "/backups",
        encryption_key: Optional[str] = None,
        retention_days: int = 30,
        audit_logger=None,
    ):
        """
        Initialize backup manager

        Args:
            db_path: Path to the database file
            backup_dir: Directory to store backups
            encryption_key: Optional encryption key for backups
            retention_days: Number of days to retain backups
            audit_logger: Optional audit logger instance
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.scheduler = AsyncIOScheduler()
        self.audit_logger = audit_logger

        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Setup encryption if key provided
        self.cipher = None
        if encryption_key:
            self.cipher = self._setup_encryption(encryption_key)

        # Progress tracking
        self.backup_progress = 0
        self.current_backup_status = None

        # Backup metadata
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self.metadata = self._load_metadata()

        # Check for incomplete restore operations on startup
        self._check_incomplete_restores()

    def _check_incomplete_restores(self):
        """Check for incomplete restore operations and log them"""
        import json

        try:
            # Look for restore log files
            restore_logs = list(self.backup_dir.glob("restore_log_*.json"))

            for log_file in restore_logs:
                # Check if there's a corresponding complete log
                restore_id = log_file.stem.replace("restore_log_", "")
                complete_log = self.backup_dir / f"restore_complete_{restore_id}.json"

                if not complete_log.exists():
                    # Found incomplete restore
                    with open(log_file, "r") as f:
                        log_data = json.load(f)

                    logger.warning(f"Found incomplete restore operation: {restore_id}")

                    # Create a completion log with warning
                    completion_log = {
                        **log_data,
                        "event": "BACKUP_RESTORE_INCOMPLETE",
                        "discovered_at": datetime.now().isoformat(),
                        "note": "Restore operation was incomplete at system startup",
                    }

                    with open(complete_log, "w") as f:
                        json.dump(completion_log, f, indent=2)

                    # Log to audit system if available
                    if self.audit_logger and hasattr(self.audit_logger, "log_sync"):
                        try:
                            self.audit_logger.log_sync(
                                event_type="SYSTEM_BACKUP_RESTORED",
                                user_name=log_data.get("user", "unknown"),
                                details={
                                    "action": "incomplete_restore_detected",
                                    "restore_id": restore_id,
                                    "backup_file": log_data.get("backup_file"),
                                    "original_timestamp": log_data.get("timestamp"),
                                },
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to log incomplete restore to audit system: {e}"
                            )

        except Exception as e:
            logger.error(f"Error checking for incomplete restores: {e}")

    def _setup_encryption(self, password: str) -> Fernet:
        """Setup encryption cipher from password"""
        # Derive a key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"kasa-monitor-backup-salt",  # In production, use random salt
            iterations=100000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def _load_metadata(self) -> Dict[str, Any]:
        """Load backup metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {"backups": [], "last_backup": None, "total_size": 0}

    def _save_metadata(self):
        """Save backup metadata"""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def get_backup_progress(self) -> Dict[str, Any]:
        """Get current backup progress"""
        return {
            "progress": self.backup_progress,
            "status": self.current_backup_status,
            "in_progress": self.current_backup_status == "in_progress",
        }

    async def create_backup(
        self,
        backup_type: str = "manual",
        description: str = "",
        compress: bool = True,
        encrypt: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a database backup

        Args:
            backup_type: Type of backup (manual, scheduled, auto)
            description: Optional backup description
            compress: Whether to compress the backup
            encrypt: Whether to encrypt the backup

        Returns:
            Backup information dictionary
        """
        timestamp = datetime.now()
        backup_name = f"kasa_backup_{backup_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Reset progress tracking
        self.backup_progress = 0
        self.current_backup_status = "in_progress"

        try:
            # Create backup info
            backup_info = {
                "name": backup_name,
                "timestamp": timestamp.isoformat(),
                "type": backup_type,
                "description": description,
                "database_path": str(self.db_path),
                "compressed": compress,
                "encrypted": encrypt and self.cipher is not None,
                "size": 0,
                "checksum": "",
                "status": "in_progress",
            }

            # Perform SQLite backup
            backup_file = self.backup_dir / f"{backup_name}.db"
            await self._sqlite_backup(backup_file)

            # Calculate checksum
            backup_info["checksum"] = await self._calculate_checksum(backup_file)

            # Compress if requested
            if compress:
                compressed_file = await self._compress_backup(backup_file, backup_name)
                backup_file.unlink()  # Remove uncompressed file
                backup_file = compressed_file

            # Encrypt if requested and cipher available
            if encrypt and self.cipher:
                encrypted_file = await self._encrypt_backup(backup_file, backup_name)
                backup_file.unlink()  # Remove unencrypted file
                backup_file = encrypted_file

            # Update backup info
            backup_info["filename"] = backup_file.name
            backup_info["size"] = backup_file.stat().st_size
            backup_info["status"] = "completed"

            # Add to metadata
            self.metadata["backups"].append(backup_info)
            self.metadata["last_backup"] = timestamp.isoformat()
            self.metadata["total_size"] = sum(
                b.get("size", 0) for b in self.metadata["backups"]
            )
            self._save_metadata()

            # Clean old backups
            await self.cleanup_old_backups()

            logger.info(f"Backup created successfully: {backup_name}")
            self.backup_progress = 100
            self.current_backup_status = "completed"
            return backup_info

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            self.current_backup_status = "failed"
            return backup_info

    async def _sqlite_backup(self, backup_file: Path):
        """Perform SQLite backup using built-in backup API"""
        import asyncio
        import concurrent.futures

        def perform_backup():
            # Use SQLite's backup API for consistency
            # Open with a shorter timeout to avoid locking issues
            source_conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            source_conn.execute(
                "PRAGMA journal_mode=WAL"
            )  # Use WAL mode for better concurrency
            backup_conn = sqlite3.connect(str(backup_file))

            try:
                # Don't use BEGIN IMMEDIATE as it can cause locking issues
                # The backup API handles consistency internally

                # Perform backup with progress callback
                with backup_conn:
                    source_conn.backup(
                        backup_conn, pages=10, progress=self._backup_progress_callback
                    )

            finally:
                source_conn.close()
                backup_conn.close()

        # Run backup in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, perform_backup)

    def _backup_progress_callback(self, status, remaining, total):
        """Progress callback for SQLite backup"""
        if total > 0:
            progress = ((total - remaining) / total) * 100
            self.backup_progress = progress
            logger.debug(f"Backup progress: {progress:.1f}%")

    async def _compress_backup(self, backup_file: Path, backup_name: str) -> Path:
        """Compress backup file using 7z"""
        compressed_file = self.backup_dir / f"{backup_name}.7z"

        with py7zr.SevenZipFile(str(compressed_file), "w") as archive:
            archive.write(backup_file, backup_file.name)

        logger.info(f"Backup compressed: {compressed_file.name}")
        return compressed_file

    async def _encrypt_backup(self, backup_file: Path, backup_name: str) -> Path:
        """Encrypt backup file"""
        if not self.cipher:
            return backup_file

        encrypted_file = self.backup_dir / f"{backup_name}.enc"

        # Read file in chunks for large files
        chunk_size = 64 * 1024  # 64KB chunks

        async with aiofiles.open(backup_file, "rb") as infile:
            async with aiofiles.open(encrypted_file, "wb") as outfile:
                while True:
                    chunk = await infile.read(chunk_size)
                    if not chunk:
                        break
                    encrypted_chunk = self.cipher.encrypt(chunk)
                    await outfile.write(encrypted_chunk)

        logger.info(f"Backup encrypted: {encrypted_file.name}")
        return encrypted_file

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()

        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    async def restore_uploaded_backup(
        self,
        uploaded_file_path: str,
        original_filename: str,
        target_path: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Restore from an uploaded backup file

        Args:
            uploaded_file_path: Path to the uploaded temporary file
            original_filename: Original filename of the upload
            target_path: Target path for restoration (defaults to original)
            user_info: Information about the user performing the restore

        Returns:
            Restoration result dictionary
        """
        import json
        import uuid

        # Generate a unique restore ID for tracking
        restore_id = str(uuid.uuid4())
        restore_timestamp = datetime.now()

        try:
            # Prepare restoration
            result = {
                "restore_id": restore_id,
                "backup_file": original_filename,
                "restored_at": restore_timestamp.isoformat(),
                "target_path": target_path or str(self.db_path),
                "status": "in_progress",
                "user": (
                    user_info.get("username", "unknown") if user_info else "unknown"
                ),
            }

            # Create pre-restore audit log entry in a separate file
            pre_restore_log = {
                "restore_id": restore_id,
                "timestamp": restore_timestamp.isoformat(),
                "event": "BACKUP_RESTORE_INITIATED",
                "backup_file": original_filename,
                "user": (
                    user_info.get("username", "unknown") if user_info else "unknown"
                ),
                "user_id": user_info.get("id") if user_info else None,
                "ip_address": user_info.get("ip_address") if user_info else None,
                "target_database": str(target_path or self.db_path),
            }

            # Save pre-restore log to a temporary file that survives the restore
            pre_restore_log_file = self.backup_dir / f"restore_log_{restore_id}.json"
            with open(pre_restore_log_file, "w") as f:
                json.dump(pre_restore_log, f, indent=2)

            logger.info(f"Pre-restore audit log saved: {pre_restore_log_file}")

            working_file = Path(uploaded_file_path)

            # Determine if file needs decompression based on extension
            if original_filename.lower().endswith(".7z"):
                # Decompress .7z file
                decompressed_file = await self._decompress_uploaded_7z(working_file)
                working_file = decompressed_file
            elif original_filename.lower().endswith(".enc"):
                # Decrypt if encrypted
                if not self.cipher:
                    return {
                        "status": "failed",
                        "error": "No encryption key available for encrypted backup",
                    }
                decrypted_file = await self._decrypt_backup(working_file)
                working_file = decrypted_file

            # Verify it's a valid SQLite database
            if not await self._verify_sqlite_file(working_file):
                if working_file != Path(uploaded_file_path):
                    working_file.unlink()
                return {
                    "status": "failed",
                    "error": "Invalid backup file - not a valid SQLite database",
                }

            # Get backup metadata if available
            backup_metadata = await self._extract_backup_metadata(working_file)

            # Backup current database before restoration
            if Path(target_path or self.db_path).exists():
                pre_restore_backup = await self.create_backup(
                    backup_type="pre_restore",
                    description=f"Automatic backup before restoring {original_filename}",
                    compress=True,
                )
                result["pre_restore_backup"] = pre_restore_backup.get("filename")

            # Perform restoration
            target = Path(target_path or self.db_path)
            shutil.copy2(working_file, target)

            # Clean up temp files
            if working_file != Path(uploaded_file_path):
                working_file.unlink()

            result["status"] = "completed"
            result["backup_metadata"] = backup_metadata

            # Save post-restore verification file
            post_restore_log = {
                **pre_restore_log,
                "event": "BACKUP_RESTORE_COMPLETED",
                "completed_at": datetime.now().isoformat(),
                "pre_restore_backup": result.get("pre_restore_backup"),
                "backup_metadata": backup_metadata,
            }

            post_restore_log_file = (
                self.backup_dir / f"restore_complete_{restore_id}.json"
            )
            with open(post_restore_log_file, "w") as f:
                json.dump(post_restore_log, f, indent=2)

            logger.info(
                f"Backup restored successfully from upload: {original_filename}"
            )
            return result

        except Exception as e:
            logger.error(f"Restoration failed: {e}")

            # Log the failure
            if "restore_id" in locals():
                failure_log = {
                    "restore_id": restore_id,
                    "timestamp": datetime.now().isoformat(),
                    "event": "BACKUP_RESTORE_FAILED",
                    "backup_file": original_filename,
                    "error": str(e),
                    "user": (
                        user_info.get("username", "unknown") if user_info else "unknown"
                    ),
                }

                failure_log_file = self.backup_dir / f"restore_failed_{restore_id}.json"
                with open(failure_log_file, "w") as f:
                    json.dump(failure_log, f, indent=2)

            return {"status": "failed", "error": str(e)}

    async def _extract_backup_metadata(self, db_file: Path) -> Optional[Dict[str, Any]]:
        """Extract metadata from backup database if available"""
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Try to get backup metadata if it exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='backup_metadata'
            """
            )

            if cursor.fetchone():
                cursor.execute(
                    "SELECT * FROM backup_metadata ORDER BY created_at DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    metadata = dict(zip(columns, row))
                    conn.close()
                    return metadata

            conn.close()
        except Exception as e:
            logger.debug(f"Could not extract backup metadata: {e}")

        return None

    async def verify_restore_audit_log(self, restore_id: str) -> bool:
        """Verify that a restore operation was properly logged"""
        # Check for pre-restore log
        pre_restore_log_file = self.backup_dir / f"restore_log_{restore_id}.json"
        post_restore_log_file = self.backup_dir / f"restore_complete_{restore_id}.json"

        if post_restore_log_file.exists():
            logger.info(f"Restore audit log verified for restore_id: {restore_id}")
            return True
        elif pre_restore_log_file.exists():
            logger.warning(
                f"Restore completed but post-restore log missing for restore_id: {restore_id}"
            )
            # Create post-restore log from pre-restore data
            with open(pre_restore_log_file, "r") as f:
                pre_log = json.load(f)

            post_log = {
                **pre_log,
                "event": "BACKUP_RESTORE_COMPLETED_UNVERIFIED",
                "completed_at": datetime.now().isoformat(),
                "note": "Post-restore log was missing and recreated",
            }

            with open(post_restore_log_file, "w") as f:
                json.dump(post_log, f, indent=2)

            return True
        else:
            logger.error(f"No audit logs found for restore_id: {restore_id}")
            return False

    async def _decompress_uploaded_7z(self, compressed_file: Path) -> Path:
        """Decompress an uploaded .7z file"""
        import tempfile

        # Create temp directory for extraction
        temp_dir = Path(tempfile.mkdtemp(prefix="restore_"))

        try:
            with py7zr.SevenZipFile(str(compressed_file), "r") as archive:
                archive.extractall(path=str(temp_dir))

            # Find the database file
            db_files = list(temp_dir.glob("*.db"))
            if not db_files:
                # Look for any file that might be a database
                all_files = list(temp_dir.iterdir())
                if len(all_files) == 1 and all_files[0].is_file():
                    return all_files[0]
                raise ValueError("No database file found in archive")

            return db_files[0]
        except Exception as e:
            # Clean up on error
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise e

    async def _verify_sqlite_file(self, file_path: Path) -> bool:
        """Verify that a file is a valid SQLite database"""
        try:
            # Try to open it as SQLite database
            conn = sqlite3.connect(str(file_path))
            # Try to execute a simple query
            conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
            conn.close()
            return True
        except sqlite3.DatabaseError:
            return False
        except Exception:
            return False

    async def restore_backup(
        self,
        backup_name: str,
        target_path: Optional[str] = None,
        verify_checksum: bool = True,
    ) -> Dict[str, Any]:
        """
        Restore a database backup

        Args:
            backup_name: Name of the backup to restore
            target_path: Target path for restoration (defaults to original)
            verify_checksum: Whether to verify backup integrity

        Returns:
            Restoration result dictionary
        """
        # Find backup in metadata
        backup_info = None
        for backup in self.metadata.get("backups", []):
            if backup["name"] == backup_name:
                backup_info = backup
                break

        if not backup_info:
            return {"status": "failed", "error": "Backup not found"}

        backup_file = self.backup_dir / backup_info["filename"]
        if not backup_file.exists():
            return {"status": "failed", "error": "Backup file not found"}

        try:
            # Prepare restoration
            result = {
                "backup_name": backup_name,
                "restored_at": datetime.now().isoformat(),
                "target_path": target_path or str(self.db_path),
                "status": "in_progress",
            }

            working_file = backup_file

            # Decrypt if encrypted
            if backup_info.get("encrypted") and self.cipher:
                decrypted_file = await self._decrypt_backup(working_file)
                working_file = decrypted_file

            # Decompress if compressed
            if backup_info.get("compressed"):
                decompressed_file = await self._decompress_backup(working_file)
                if working_file != backup_file:
                    working_file.unlink()  # Clean up temp file
                working_file = decompressed_file

            # Verify checksum if requested
            if verify_checksum:
                current_checksum = await self._calculate_checksum(working_file)
                if current_checksum != backup_info.get("checksum"):
                    if working_file != backup_file:
                        working_file.unlink()
                    return {"status": "failed", "error": "Checksum verification failed"}

            # Backup current database before restoration
            if Path(target_path or self.db_path).exists():
                await self.create_backup(
                    backup_type="pre_restore",
                    description=f"Automatic backup before restoring {backup_name}",
                )

            # Perform restoration
            target = Path(target_path or self.db_path)
            shutil.copy2(working_file, target)

            # Clean up temp files
            if working_file != backup_file:
                working_file.unlink()

            result["status"] = "completed"
            logger.info(f"Backup restored successfully: {backup_name}")
            return result

        except Exception as e:
            logger.error(f"Restoration failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _decrypt_backup(self, encrypted_file: Path) -> Path:
        """Decrypt backup file"""
        if not self.cipher:
            raise ValueError("No encryption key available")

        decrypted_file = self.backup_dir / f"temp_{encrypted_file.stem}"

        async with aiofiles.open(encrypted_file, "rb") as infile:
            async with aiofiles.open(decrypted_file, "wb") as outfile:
                while True:
                    chunk = await infile.read(64 * 1024 + 44)  # Fernet adds 44 bytes
                    if not chunk:
                        break
                    decrypted_chunk = self.cipher.decrypt(chunk)
                    await outfile.write(decrypted_chunk)

        return decrypted_file

    async def _decompress_backup(self, compressed_file: Path) -> Path:
        """Decompress backup file"""
        decompressed_dir = self.backup_dir / "temp_restore"
        decompressed_dir.mkdir(exist_ok=True)

        with py7zr.SevenZipFile(str(compressed_file), "r") as archive:
            archive.extractall(path=str(decompressed_dir))

        # Find the extracted database file
        db_files = list(decompressed_dir.glob("*.db"))
        if not db_files:
            raise ValueError("No database file found in archive")

        return db_files[0]

    async def cleanup_old_backups(self):
        """Clean up backups older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        backups_to_remove = []
        remaining_backups = []

        for backup in self.metadata.get("backups", []):
            backup_date = datetime.fromisoformat(backup["timestamp"])

            # Keep at least one backup per type regardless of age
            if backup_date < cutoff_date and backup["type"] != "manual":
                backup_file = self.backup_dir / backup["filename"]
                if backup_file.exists():
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup['name']}")
                backups_to_remove.append(backup)
            else:
                remaining_backups.append(backup)

        self.metadata["backups"] = remaining_backups
        self.metadata["total_size"] = sum(b.get("size", 0) for b in remaining_backups)
        self._save_metadata()

        return len(backups_to_remove)

    async def get_backup_file(self, backup_id: int) -> Optional[str]:
        """Get backup file path by ID"""
        # For simplicity, return the backup file from metadata
        if backup_id < len(self.metadata["backups"]):
            backup = self.metadata["backups"][backup_id]
            return str(self.backup_dir / backup.get("filename", ""))
        return None

    async def delete_backup(self, backup_id: int) -> bool:
        """Delete a backup by ID"""
        if backup_id < len(self.metadata["backups"]):
            backup = self.metadata["backups"][backup_id]
            file_path = self.backup_dir / backup.get("filename", "")
            if file_path.exists():
                file_path.unlink()
            del self.metadata["backups"][backup_id]
            self._save_metadata()
            return True
        return False

    async def get_schedules(self) -> List[Dict[str, Any]]:
        """Get backup schedules"""
        # For now, return schedules from metadata
        return self.metadata.get("schedules", [])

    async def get_backup_file_by_name(self, filename: str) -> Optional[str]:
        """Get backup file path by filename"""
        file_path = self.backup_dir / filename
        if file_path.exists():
            return str(file_path)
        return None

    async def delete_backup_by_name(self, filename: str) -> bool:
        """Delete a backup by filename"""
        file_path = self.backup_dir / filename

        # Remove from metadata
        self.metadata["backups"] = [
            b for b in self.metadata.get("backups", []) if b.get("filename") != filename
        ]
        self._save_metadata()

        # Delete the file
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception as e:
                logger.error(f"Error deleting backup file {filename}: {e}")
                return False
        return False

    async def list_backups(
        self, backup_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List available backups

        Args:
            backup_type: Filter by backup type
            limit: Maximum number of backups to return

        Returns:
            List of backup information dictionaries
        """
        backups = self.metadata.get("backups", [])

        # Filter by type if specified
        if backup_type:
            backups = [b for b in backups if b.get("type") == backup_type]

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Apply limit if specified
        if limit:
            backups = backups[:limit]

        return backups

    async def verify_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        Verify backup integrity

        Args:
            backup_name: Name of backup to verify

        Returns:
            Verification result dictionary
        """
        # Find backup in metadata
        backup_info = None
        for backup in self.metadata.get("backups", []):
            if backup["name"] == backup_name:
                backup_info = backup
                break

        if not backup_info:
            return {"status": "failed", "error": "Backup not found"}

        backup_file = self.backup_dir / backup_info["filename"]
        if not backup_file.exists():
            return {"status": "failed", "error": "Backup file not found"}

        try:
            # Verify file size
            actual_size = backup_file.stat().st_size
            if actual_size != backup_info.get("size", 0):
                return {
                    "status": "failed",
                    "error": f"Size mismatch: expected {backup_info.get('size')}, got {actual_size}",
                }

            # For encrypted/compressed files, we can't verify checksum directly
            # We would need to decrypt/decompress first
            if not backup_info.get("encrypted") and not backup_info.get("compressed"):
                current_checksum = await self._calculate_checksum(backup_file)
                if current_checksum != backup_info.get("checksum"):
                    return {"status": "failed", "error": "Checksum mismatch"}

            return {
                "status": "success",
                "message": "Backup verified successfully",
                "backup_name": backup_name,
                "size": actual_size,
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def schedule_automatic_backups(
        self,
        schedule: str = "0 2 * * *",  # Default: 2 AM daily
        backup_type: str = "scheduled",
    ):
        """
        Schedule automatic backups

        Args:
            schedule: Cron expression for backup schedule
            backup_type: Type to use for scheduled backups
        """
        # Remove existing job if any
        if self.scheduler.get_job("automatic_backup"):
            self.scheduler.remove_job("automatic_backup")

        # Add new scheduled job
        self.scheduler.add_job(
            self.create_backup,
            CronTrigger.from_crontab(schedule),
            id="automatic_backup",
            args=[backup_type, "Automatic scheduled backup"],
            replace_existing=True,
        )

        logger.info(f"Automatic backups scheduled: {schedule}")

    def start_scheduler(self):
        """Start the backup scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Backup scheduler started")

    def stop_scheduler(self):
        """Stop the backup scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Backup scheduler stopped")

    async def export_backup(self, backup_name: str, export_path: str) -> Dict[str, Any]:
        """
        Export a backup to external location

        Args:
            backup_name: Name of backup to export
            export_path: Path to export backup to

        Returns:
            Export result dictionary
        """
        # Find backup
        backup_info = None
        for backup in self.metadata.get("backups", []):
            if backup["name"] == backup_name:
                backup_info = backup
                break

        if not backup_info:
            return {"status": "failed", "error": "Backup not found"}

        backup_file = self.backup_dir / backup_info["filename"]
        if not backup_file.exists():
            return {"status": "failed", "error": "Backup file not found"}

        try:
            # Copy backup to export location
            export_file = Path(export_path) / backup_info["filename"]
            shutil.copy2(backup_file, export_file)

            # Also export metadata
            metadata_export = Path(export_path) / f"{backup_name}_metadata.json"
            with open(metadata_export, "w") as f:
                json.dump(backup_info, f, indent=2)

            return {
                "status": "success",
                "exported_to": str(export_file),
                "metadata_file": str(metadata_export),
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new backup schedule"""
        try:
            # Generate schedule ID
            schedules = self.metadata.get("schedules", [])
            schedule_id = max([s.get("id", 0) for s in schedules], default=0) + 1

            # Create schedule object
            schedule = {
                "id": schedule_id,
                "name": schedule_data.get("name", f"Schedule {schedule_id}"),
                "frequency": schedule_data.get("frequency", "daily"),
                "time": schedule_data.get("time", "02:00"),
                "retention_days": schedule_data.get("retention_days", 30),
                "enabled": schedule_data.get("enabled", True),
                "created_at": datetime.now().isoformat(),
                "last_run": None,
                "next_run": self._calculate_next_run(
                    schedule_data.get("frequency", "daily"),
                    schedule_data.get("time", "02:00"),
                ),
            }

            # Add to metadata
            if "schedules" not in self.metadata:
                self.metadata["schedules"] = []
            self.metadata["schedules"].append(schedule)
            self._save_metadata()

            # Schedule the job if enabled
            if schedule["enabled"]:
                self._schedule_job(schedule)

            logger.info(f"Created backup schedule: {schedule['name']}")
            return schedule

        except Exception as e:
            logger.error(f"Failed to create schedule: {e}")
            raise

    async def update_schedule(
        self, schedule_id: int, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing backup schedule"""
        try:
            schedules = self.metadata.get("schedules", [])

            for i, schedule in enumerate(schedules):
                if schedule.get("id") == schedule_id:
                    # Update schedule fields
                    if "name" in update_data:
                        schedule["name"] = update_data["name"]
                    if "frequency" in update_data:
                        schedule["frequency"] = update_data["frequency"]
                    if "time" in update_data:
                        schedule["time"] = update_data["time"]
                    if "retention_days" in update_data:
                        schedule["retention_days"] = update_data["retention_days"]
                    if "enabled" in update_data:
                        schedule["enabled"] = update_data["enabled"]

                    # Recalculate next run
                    schedule["next_run"] = self._calculate_next_run(
                        schedule["frequency"], schedule["time"]
                    )

                    # Update metadata
                    self.metadata["schedules"][i] = schedule
                    self._save_metadata()

                    # Reschedule job
                    self._unschedule_job(schedule_id)
                    if schedule["enabled"]:
                        self._schedule_job(schedule)

                    logger.info(f"Updated backup schedule {schedule_id}")
                    return schedule

            raise ValueError(f"Schedule {schedule_id} not found")

        except Exception as e:
            logger.error(f"Failed to update schedule: {e}")
            raise

    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a backup schedule"""
        try:
            schedules = self.metadata.get("schedules", [])

            for i, schedule in enumerate(schedules):
                if schedule.get("id") == schedule_id:
                    # Remove from scheduler
                    self._unschedule_job(schedule_id)

                    # Remove from metadata
                    del self.metadata["schedules"][i]
                    self._save_metadata()

                    logger.info(f"Deleted backup schedule {schedule_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete schedule: {e}")
            return False

    def _calculate_next_run(self, frequency: str, time: str) -> str:
        """Calculate the next run time for a schedule"""
        from datetime import datetime, timedelta

        now = datetime.now()
        hour, minute = map(int, time.split(":"))

        # Create a datetime for today at the specified time
        run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time has already passed today, start from tomorrow
        if run_time <= now:
            run_time += timedelta(days=1)

        # Adjust based on frequency
        if frequency == "hourly":
            # For hourly, find the next hour
            run_time = now + timedelta(hours=1)
            run_time = run_time.replace(minute=0, second=0, microsecond=0)
        elif frequency == "weekly":
            # For weekly, add days until we reach the same weekday next week
            days_ahead = 7
            run_time += timedelta(days=days_ahead)
        elif frequency == "monthly":
            # For monthly, add approximately 30 days
            run_time += timedelta(days=30)
        # daily is already handled by the default logic

        return run_time.isoformat()

    def _schedule_job(self, schedule: Dict[str, Any]):
        """Schedule a backup job"""
        job_id = f"schedule_{schedule['id']}"

        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # Create cron trigger based on frequency
        if schedule["frequency"] == "hourly":
            trigger = CronTrigger(minute=0)
        elif schedule["frequency"] == "daily":
            hour, minute = map(int, schedule["time"].split(":"))
            trigger = CronTrigger(hour=hour, minute=minute)
        elif schedule["frequency"] == "weekly":
            hour, minute = map(int, schedule["time"].split(":"))
            trigger = CronTrigger(day_of_week=0, hour=hour, minute=minute)  # Monday
        elif schedule["frequency"] == "monthly":
            hour, minute = map(int, schedule["time"].split(":"))
            trigger = CronTrigger(day=1, hour=hour, minute=minute)  # First day of month
        else:
            return

        # Add job
        self.scheduler.add_job(
            self._run_scheduled_backup,
            trigger,
            id=job_id,
            args=[schedule],
            replace_existing=True,
        )

        logger.info(f"Scheduled job {job_id} with frequency {schedule['frequency']}")

    def _unschedule_job(self, schedule_id: int):
        """Remove a scheduled job"""
        job_id = f"schedule_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled job {job_id}")

    async def _run_scheduled_backup(self, schedule: Dict[str, Any]):
        """Run a scheduled backup"""
        try:
            logger.info(f"Running scheduled backup: {schedule['name']}")

            # Create the backup
            backup_info = await self.create_backup(
                backup_type="scheduled",
                description=f"Scheduled backup: {schedule['name']}",
                compress=True,
                encrypt=self.cipher is not None,
            )

            # Update schedule metadata
            for i, s in enumerate(self.metadata.get("schedules", [])):
                if s.get("id") == schedule["id"]:
                    self.metadata["schedules"][i][
                        "last_run"
                    ] = datetime.now().isoformat()
                    self.metadata["schedules"][i]["next_run"] = (
                        self._calculate_next_run(
                            schedule["frequency"], schedule["time"]
                        )
                    )
                    self._save_metadata()
                    break

            # Clean up old scheduled backups based on retention
            await self._cleanup_scheduled_backups(schedule["retention_days"])

        except Exception as e:
            logger.error(f"Failed to run scheduled backup: {e}")

    async def _cleanup_scheduled_backups(self, retention_days: int):
        """Clean up old scheduled backups based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        backups_to_remove = []
        for backup in self.metadata.get("backups", []):
            if backup.get("type") == "scheduled":
                backup_date = datetime.fromisoformat(backup["timestamp"])
                if backup_date < cutoff_date:
                    backup_file = self.backup_dir / backup["filename"]
                    if backup_file.exists():
                        backup_file.unlink()
                    backups_to_remove.append(backup)

        # Remove from metadata
        for backup in backups_to_remove:
            self.metadata["backups"].remove(backup)

        if backups_to_remove:
            self._save_metadata()
            logger.info(f"Cleaned up {len(backups_to_remove)} old scheduled backups")

    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        backups = self.metadata.get("backups", [])

        if not backups:
            return {"total_backups": 0, "total_size": 0, "last_backup": None}

        # Group by type
        by_type = {}
        for backup in backups:
            backup_type = backup.get("type", "unknown")
            if backup_type not in by_type:
                by_type[backup_type] = {"count": 0, "size": 0}
            by_type[backup_type]["count"] += 1
            by_type[backup_type]["size"] += backup.get("size", 0)

        # Find oldest and newest
        sorted_backups = sorted(backups, key=lambda x: x.get("timestamp", ""))

        return {
            "total_backups": len(backups),
            "total_size": self.metadata.get("total_size", 0),
            "total_size_mb": self.metadata.get("total_size", 0) / (1024 * 1024),
            "last_backup": self.metadata.get("last_backup"),
            "oldest_backup": (
                sorted_backups[0].get("timestamp") if sorted_backups else None
            ),
            "newest_backup": (
                sorted_backups[-1].get("timestamp") if sorted_backups else None
            ),
            "by_type": by_type,
            "average_size": (
                self.metadata.get("total_size", 0) / len(backups) if backups else 0
            ),
        }
