"""
Database Backup and Restore Manager for Kasa Monitor
Handles automated backups, encryption, compression, and restoration
"""

import os
import shutil
import sqlite3
import json
import hashlib
import logging
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import py7zr
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import aiofiles
import aiofiles.os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backups and restoration"""
    
    def __init__(
        self,
        db_path: str,
        backup_dir: str = "/backups",
        encryption_key: Optional[str] = None,
        retention_days: int = 30
    ):
        """
        Initialize backup manager
        
        Args:
            db_path: Path to the database file
            backup_dir: Directory to store backups
            encryption_key: Optional encryption key for backups
            retention_days: Number of days to retain backups
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.scheduler = AsyncIOScheduler()
        
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
    
    def _setup_encryption(self, password: str) -> Fernet:
        """Setup encryption cipher from password"""
        # Derive a key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'kasa-monitor-backup-salt',  # In production, use random salt
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load backup metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {"backups": [], "last_backup": None, "total_size": 0}
    
    def _save_metadata(self):
        """Save backup metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def get_backup_progress(self) -> Dict[str, Any]:
        """Get current backup progress"""
        return {
            "progress": self.backup_progress,
            "status": self.current_backup_status,
            "in_progress": self.current_backup_status == "in_progress"
        }
    
    async def create_backup(
        self,
        backup_type: str = "manual",
        description: str = "",
        compress: bool = True,
        encrypt: bool = True
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
                "status": "in_progress"
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
            self.metadata["total_size"] = sum(b.get("size", 0) for b in self.metadata["backups"])
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
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_file))
            
            try:
                # Lock database for consistency
                source_conn.execute("BEGIN IMMEDIATE")
                
                # Perform backup with progress callback
                with backup_conn:
                    source_conn.backup(backup_conn, pages=10, progress=self._backup_progress_callback)
                
                source_conn.rollback()
                
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
        
        with py7zr.SevenZipFile(str(compressed_file), 'w') as archive:
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
        
        async with aiofiles.open(backup_file, 'rb') as infile:
            async with aiofiles.open(encrypted_file, 'wb') as outfile:
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
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def restore_backup(
        self,
        backup_name: str,
        target_path: Optional[str] = None,
        verify_checksum: bool = True
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
                "status": "in_progress"
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
                    return {
                        "status": "failed",
                        "error": "Checksum verification failed"
                    }
            
            # Backup current database before restoration
            if Path(target_path or self.db_path).exists():
                await self.create_backup(
                    backup_type="pre_restore",
                    description=f"Automatic backup before restoring {backup_name}"
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
        
        async with aiofiles.open(encrypted_file, 'rb') as infile:
            async with aiofiles.open(decrypted_file, 'wb') as outfile:
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
        
        with py7zr.SevenZipFile(str(compressed_file), 'r') as archive:
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
        # Return empty list for now - schedules not implemented yet
        return []
    
    async def list_backups(
        self,
        backup_type: Optional[str] = None,
        limit: Optional[int] = None
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
                    "error": f"Size mismatch: expected {backup_info.get('size')}, got {actual_size}"
                }
            
            # For encrypted/compressed files, we can't verify checksum directly
            # We would need to decrypt/decompress first
            if not backup_info.get("encrypted") and not backup_info.get("compressed"):
                current_checksum = await self._calculate_checksum(backup_file)
                if current_checksum != backup_info.get("checksum"):
                    return {
                        "status": "failed",
                        "error": "Checksum mismatch"
                    }
            
            return {
                "status": "success",
                "message": "Backup verified successfully",
                "backup_name": backup_name,
                "size": actual_size
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def schedule_automatic_backups(
        self,
        schedule: str = "0 2 * * *",  # Default: 2 AM daily
        backup_type: str = "scheduled"
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
            replace_existing=True
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
    
    async def export_backup(
        self,
        backup_name: str,
        export_path: str
    ) -> Dict[str, Any]:
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
            with open(metadata_export, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            return {
                "status": "success",
                "exported_to": str(export_file),
                "metadata_file": str(metadata_export)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        backups = self.metadata.get("backups", [])
        
        if not backups:
            return {
                "total_backups": 0,
                "total_size": 0,
                "last_backup": None
            }
        
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
            "oldest_backup": sorted_backups[0].get("timestamp") if sorted_backups else None,
            "newest_backup": sorted_backups[-1].get("timestamp") if sorted_backups else None,
            "by_type": by_type,
            "average_size": self.metadata.get("total_size", 0) / len(backups) if backups else 0
        }