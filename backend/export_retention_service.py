"""Export Retention Service for managing export file lifecycle.

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

import asyncio
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from audit_logging import AuditEvent, AuditEventType, AuditLogger, AuditSeverity

logger = logging.getLogger(__name__)


class ExportStatus(Enum):
    """Export lifecycle states."""

    ACTIVE = "active"
    EXPIRES_SOON = "expires_soon"
    EXPIRED = "expired"
    ARCHIVED = "archived"
    DELETED = "deleted"


class RetentionPolicyType(Enum):
    """Types of retention policies."""

    DEFAULT = "default"
    FORMAT_BASED = "format_based"
    SIZE_BASED = "size_based"
    USER_BASED = "user_based"
    CUSTOM = "custom"


# Default retention policies in days
DEFAULT_RETENTION_POLICIES = {
    "default": 30,  # 30 days default
    "csv": 7,  # CSV exports - 7 days (frequent, small)
    "excel": 14,  # Excel exports - 14 days (medium use)
    "json": 30,  # JSON exports - 30 days (less frequent)
    "sqlite": 90,  # SQLite exports - 90 days (archive use)
    "large_export": 3,  # Large exports (>100MB) - 3 days only
}

# Storage thresholds in bytes
EMERGENCY_CLEANUP_THRESHOLD = 1 * 1024 * 1024 * 1024  # 1GB
LOW_STORAGE_WARNING_THRESHOLD = 5 * 1024 * 1024 * 1024  # 5GB
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB


class ExportRetentionService:
    """Service for managing export file retention and cleanup."""

    def __init__(
        self,
        db_path: str = "kasa_monitor.db",
        exports_dir: str = "exports",
        audit_logger: Optional[AuditLogger] = None,
        retention_policies: Optional[Dict[str, int]] = None,
    ):
        """Initialize export retention service.

        Args:
            db_path: Path to the database
            exports_dir: Directory containing export files
            audit_logger: Audit logging instance
            retention_policies: Custom retention policies
        """
        self.db_path = db_path
        self.exports_dir = Path(exports_dir)
        self.audit_logger = audit_logger or AuditLogger(db_path=db_path)
        self.retention_policies = (
            retention_policies or DEFAULT_RETENTION_POLICIES.copy()
        )

        # Ensure exports directory exists
        self.exports_dir.mkdir(exist_ok=True)

        # Initialize database schema
        self._init_retention_schema()

        logger.info("Export retention service initialized")

    def _init_retention_schema(self):
        """Initialize database schema for retention tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if retention columns exist in data_exports table
            cursor.execute("PRAGMA table_info(data_exports)")
            columns = [column[1] for column in cursor.fetchall()]

            # Add retention tracking columns if they don't exist
            if "expires_at" not in columns:
                cursor.execute(
                    "ALTER TABLE data_exports ADD COLUMN expires_at TIMESTAMP"
                )

            if "accessed_at" not in columns:
                cursor.execute(
                    "ALTER TABLE data_exports ADD COLUMN accessed_at TIMESTAMP"
                )

            if "retention_period" not in columns:
                cursor.execute(
                    "ALTER TABLE data_exports ADD COLUMN retention_period INTEGER"
                )

            if "status" not in columns:
                cursor.execute(
                    "ALTER TABLE data_exports ADD COLUMN status TEXT DEFAULT 'active'"
                )
            else:
                # Update existing rows to have status if NULL
                cursor.execute(
                    "UPDATE data_exports SET status = 'active' WHERE status IS NULL"
                )

            if "download_count" not in columns:
                cursor.execute(
                    "ALTER TABLE data_exports ADD COLUMN download_count INTEGER DEFAULT 0"
                )

            if "user_role" not in columns:
                cursor.execute("ALTER TABLE data_exports ADD COLUMN user_role TEXT")

            # Create retention policies table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS export_retention_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_type TEXT NOT NULL,
                    policy_key TEXT NOT NULL,
                    retention_days INTEGER NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(policy_type, policy_key)
                )
            """
            )

            # Create retention audit table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS export_retention_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    export_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT,
                    retention_days INTEGER,
                    file_size INTEGER,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for better performance
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_exports_expires_at 
                ON data_exports(expires_at)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_exports_status_created 
                ON data_exports(status, created_at)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_retention_audit_export 
                ON export_retention_audit(export_id, timestamp)
            """
            )

            # Insert default retention policies if they don't exist
            for policy_key, days in DEFAULT_RETENTION_POLICIES.items():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO export_retention_policies 
                    (policy_type, policy_key, retention_days, description)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        "format_based" if policy_key != "default" else "default",
                        policy_key,
                        days,
                        f"Default retention policy for {policy_key}",
                    ),
                )

            conn.commit()
            logger.info("Export retention database schema initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing retention schema: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    async def calculate_retention_period(self, export_data: Dict) -> int:
        """Calculate retention period based on export characteristics.

        Args:
            export_data: Export metadata

        Returns:
            Retention period in days
        """
        base_retention = self.retention_policies.get(
            export_data.get("format", ""), self.retention_policies["default"]
        )

        # Extend retention for frequently accessed files
        download_count = export_data.get("download_count", 0)
        if download_count > 5:
            base_retention += 7  # Extra week for popular exports

        # Reduce retention for large files
        file_size = export_data.get("file_size", 0)
        if file_size > LARGE_FILE_THRESHOLD:
            base_retention = min(
                base_retention, self.retention_policies.get("large_export", 3)
            )

        # Admin exports get longer retention
        user_role = export_data.get("user_role", "")
        if user_role == "admin":
            base_retention += 14  # Extra 2 weeks for admin exports

        return max(1, base_retention)  # Minimum 1 day retention

    async def update_export_retention(self, export_id: str) -> bool:
        """Update retention information for an export.

        Args:
            export_id: Export identifier

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get export data
            cursor.execute(
                """
                SELECT e.*, u.is_admin 
                FROM data_exports e 
                LEFT JOIN users u ON e.user_id = u.id 
                WHERE e.export_id = ?
            """,
                (export_id,),
            )

            row = cursor.fetchone()
            if not row:
                logger.warning(f"Export {export_id} not found for retention update")
                return False

            # Create export data dict
            export_data = {
                "format": row[5],  # format column
                "file_size": row[4],  # file_size column
                "download_count": row[17] if len(row) > 17 else 0,  # download_count
                "user_role": (
                    "admin" if row[-1] else "user"
                ),  # is_admin from users table
            }

            # Calculate retention period
            retention_days = await self.calculate_retention_period(export_data)

            # Calculate expiration date
            created_at = (
                datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6]
            )
            expires_at = created_at + timedelta(days=retention_days)

            # Update export with retention info
            cursor.execute(
                """
                UPDATE data_exports 
                SET retention_period = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE export_id = ?
            """,
                (retention_days, expires_at, export_id),
            )

            # Log retention update
            cursor.execute(
                """
                INSERT INTO export_retention_audit 
                (export_id, action, retention_days, file_size, reason)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    export_id,
                    "retention_calculated",
                    retention_days,
                    export_data["file_size"],
                    f"Calculated retention: {retention_days} days based on format, size, and user role",
                ),
            )

            conn.commit()

            # Log audit event
            await self.audit_logger.log_event_async(
                AuditEvent(
                    event_type=AuditEventType.DATA_EXPORT,
                    severity=AuditSeverity.INFO,
                    user_id=row[10] if row[10] else None,  # user_id
                    username=None,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="export_retention",
                    resource_id=export_id,
                    action="retention_period_calculated",
                    details={
                        "retention_days": retention_days,
                        "expires_at": expires_at.isoformat(),
                        "file_size": export_data["file_size"],
                        "format": export_data["format"],
                    },
                    timestamp=datetime.now(),
                    success=True,
                )
            )

            return True

        except Exception as e:
            logger.error(f"Error updating retention for export {export_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    async def get_expired_exports(self) -> List[Dict]:
        """Get list of expired exports ready for cleanup.

        Returns:
            List of expired export records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            cursor = conn.execute(
                """
                SELECT * FROM data_exports 
                WHERE status IN ('active', 'expires_soon') 
                AND expires_at IS NOT NULL 
                AND expires_at < CURRENT_TIMESTAMP
                ORDER BY expires_at
            """
            )

            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    async def get_expiring_exports(self, hours_ahead: int = 24) -> List[Dict]:
        """Get exports expiring soon.

        Args:
            hours_ahead: Hours to look ahead for expiring exports

        Returns:
            List of exports expiring soon
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            expiry_threshold = datetime.now() + timedelta(hours=hours_ahead)

            cursor = conn.execute(
                """
                SELECT * FROM data_exports 
                WHERE status = 'active' 
                AND expires_at IS NOT NULL 
                AND expires_at BETWEEN CURRENT_TIMESTAMP AND ?
                ORDER BY expires_at
            """,
                (expiry_threshold,),
            )

            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    async def mark_exports_expiring_soon(self) -> int:
        """Mark exports that are expiring within 24 hours.

        Returns:
            Number of exports marked as expiring soon
        """
        conn = sqlite3.connect(self.db_path)

        try:
            expiry_threshold = datetime.now() + timedelta(hours=24)

            cursor = conn.execute(
                """
                UPDATE data_exports 
                SET status = 'expires_soon', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'active' 
                AND expires_at IS NOT NULL 
                AND expires_at BETWEEN CURRENT_TIMESTAMP AND ?
            """,
                (expiry_threshold,),
            )

            marked_count = cursor.rowcount
            conn.commit()

            if marked_count > 0:
                logger.info(f"Marked {marked_count} exports as expiring soon")

                # Log audit event
                await self.audit_logger.log_event_async(
                    AuditEvent(
                        event_type=AuditEventType.DATA_EXPORT,
                        severity=AuditSeverity.INFO,
                        user_id=None,
                        username="system",
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="export_retention",
                        resource_id=None,
                        action="mark_exports_expiring_soon",
                        details={"marked_count": marked_count},
                        timestamp=datetime.now(),
                        success=True,
                    )
                )

            return marked_count

        except Exception as e:
            logger.error(f"Error marking expiring exports: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    async def cleanup_expired_exports(self, batch_size: int = 50) -> Tuple[int, int]:
        """Clean up expired exports.

        Args:
            batch_size: Maximum number of exports to process in one batch

        Returns:
            Tuple of (files_deleted, records_updated)
        """
        expired_exports = await self.get_expired_exports()

        if not expired_exports:
            return 0, 0

        files_deleted = 0
        records_updated = 0

        # Process in batches
        for i in range(0, len(expired_exports), batch_size):
            batch = expired_exports[i : i + batch_size]
            batch_deleted, batch_updated = await self._cleanup_export_batch(batch)
            files_deleted += batch_deleted
            records_updated += batch_updated

            # Small delay between batches to avoid overwhelming the system
            if i + batch_size < len(expired_exports):
                await asyncio.sleep(0.1)

        if files_deleted > 0 or records_updated > 0:
            logger.info(
                f"Cleanup completed: {files_deleted} files deleted, {records_updated} records updated"
            )

            # Log aggregate audit event
            await self.audit_logger.log_event_async(
                AuditEvent(
                    event_type=AuditEventType.DATA_DELETED,
                    severity=AuditSeverity.WARNING,
                    user_id=None,
                    username="system",
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="export_cleanup",
                    resource_id=None,
                    action="cleanup_expired_exports",
                    details={
                        "files_deleted": files_deleted,
                        "records_updated": records_updated,
                        "batch_size": batch_size,
                    },
                    timestamp=datetime.now(),
                    success=True,
                )
            )

        return files_deleted, records_updated

    async def _cleanup_export_batch(self, exports: List[Dict]) -> Tuple[int, int]:
        """Clean up a batch of expired exports.

        Args:
            exports: List of export records to clean up

        Returns:
            Tuple of (files_deleted, records_updated)
        """
        conn = sqlite3.connect(self.db_path)
        files_deleted = 0
        records_updated = 0

        try:
            for export in exports:
                export_id = export["export_id"]
                file_path = export["file_path"]

                try:
                    # Delete physical file
                    if file_path and Path(file_path).exists():
                        Path(file_path).unlink()
                        files_deleted += 1
                        logger.debug(f"Deleted file: {file_path}")

                    # Update database record
                    cursor = conn.execute(
                        """
                        UPDATE data_exports 
                        SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                        WHERE export_id = ?
                    """,
                        (export_id,),
                    )

                    if cursor.rowcount > 0:
                        records_updated += 1

                    # Log retention audit
                    days_since_creation = (
                        datetime.now() - datetime.fromisoformat(export["created_at"])
                    ).days

                    conn.execute(
                        """
                        INSERT INTO export_retention_audit 
                        (export_id, action, old_status, new_status, file_size, reason)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            export_id,
                            "file_deleted",
                            export.get("status", "expired"),
                            "deleted",
                            export.get("file_size", 0),
                            f"Retention policy cleanup - {days_since_creation} days old",
                        ),
                    )

                    # Log individual audit event for sensitive deletions
                    await self.audit_logger.log_event_async(
                        AuditEvent(
                            event_type=AuditEventType.DATA_DELETED,
                            severity=AuditSeverity.WARNING,
                            user_id=export.get("user_id"),
                            username=None,
                            ip_address=None,
                            user_agent=None,
                            session_id=None,
                            resource_type="export_file",
                            resource_id=export_id,
                            action="export_file_deleted",
                            details={
                                "filename": export.get("filename", ""),
                                "file_size": export.get("file_size", 0),
                                "created_date": export.get("created_at", ""),
                                "retention_period_days": export.get(
                                    "retention_period", 0
                                ),
                                "days_since_creation": days_since_creation,
                                "deletion_reason": "retention_policy",
                            },
                            timestamp=datetime.now(),
                            success=True,
                        )
                    )

                except Exception as e:
                    logger.error(f"Error deleting export {export_id}: {e}")
                    # Continue with next export
                    continue

            conn.commit()

        except Exception as e:
            logger.error(f"Error in batch cleanup: {e}")
            conn.rollback()
        finally:
            conn.close()

        return files_deleted, records_updated

    async def check_storage_space(self) -> Dict:
        """Monitor export directory disk usage.

        Returns:
            Storage information dictionary
        """
        try:
            total, used, free = shutil.disk_usage(self.exports_dir)

            storage_info = {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "usage_percent": (used / total) * 100,
                "free_gb": free / (1024**3),
                "needs_emergency_cleanup": free < EMERGENCY_CLEANUP_THRESHOLD,
                "needs_warning": free < LOW_STORAGE_WARNING_THRESHOLD,
            }

            logger.info(
                f"Storage check - Free: {storage_info['free_gb']:.2f}GB, "
                f"Usage: {storage_info['usage_percent']:.1f}%"
            )

            return storage_info

        except Exception as e:
            logger.error(f"Error checking storage space: {e}")
            return {
                "error": str(e),
                "needs_emergency_cleanup": False,
                "needs_warning": False,
            }

    async def emergency_cleanup(self) -> Tuple[int, int]:
        """Perform emergency cleanup when disk space is critically low.

        Returns:
            Tuple of (files_deleted, space_freed_mb)
        """
        logger.warning("Starting emergency cleanup due to low disk space")

        files_deleted = 0
        space_freed = 0

        conn = sqlite3.connect(self.db_path)

        try:
            # Phase 1: Remove expired exports first
            expired_deleted, expired_updated = await self.cleanup_expired_exports()
            files_deleted += expired_deleted

            # Check if we have enough space now
            storage_info = await self.check_storage_space()
            if not storage_info.get("needs_emergency_cleanup", False):
                logger.info(
                    "Emergency cleanup completed after removing expired exports"
                )
                return files_deleted, space_freed

            # Phase 2: Remove large exports older than 1 day
            one_day_ago = datetime.now() - timedelta(days=1)

            cursor = conn.execute(
                """
                SELECT export_id, file_path, file_size FROM data_exports 
                WHERE status = 'active' 
                AND file_size > ? 
                AND created_at < ?
                ORDER BY file_size DESC, created_at ASC
                LIMIT 20
            """,
                (LARGE_FILE_THRESHOLD, one_day_ago),
            )

            large_exports = cursor.fetchall()

            for export_id, file_path, file_size in large_exports:
                try:
                    if file_path and Path(file_path).exists():
                        Path(file_path).unlink()
                        files_deleted += 1
                        space_freed += file_size or 0

                        # Update database
                        conn.execute(
                            """
                            UPDATE data_exports 
                            SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                            WHERE export_id = ?
                        """,
                            (export_id,),
                        )

                        logger.warning(
                            f"Emergency cleanup: deleted large export {export_id}"
                        )

                        # Log audit event
                        await self.audit_logger.log_event_async(
                            AuditEvent(
                                event_type=AuditEventType.DATA_DELETED,
                                severity=AuditSeverity.CRITICAL,
                                user_id=None,
                                username="system",
                                ip_address=None,
                                user_agent=None,
                                session_id=None,
                                resource_type="export_file",
                                resource_id=export_id,
                                action="emergency_cleanup_large_file",
                                details={
                                    "file_size": file_size,
                                    "deletion_reason": "emergency_cleanup_large_file",
                                    "age_days": 1,
                                },
                                timestamp=datetime.now(),
                                success=True,
                            )
                        )

                except Exception as e:
                    logger.error(f"Error deleting large export {export_id}: {e}")
                    continue

            # Phase 3: If still low on space, remove oldest exports
            storage_info = await self.check_storage_space()
            if storage_info.get("needs_emergency_cleanup", False):
                cursor = conn.execute(
                    """
                    SELECT export_id, file_path, file_size FROM data_exports 
                    WHERE status = 'active' 
                    ORDER BY created_at ASC
                    LIMIT 10
                """
                )

                oldest_exports = cursor.fetchall()

                for export_id, file_path, file_size in oldest_exports:
                    try:
                        if file_path and Path(file_path).exists():
                            Path(file_path).unlink()
                            files_deleted += 1
                            space_freed += file_size or 0

                            # Update database
                            conn.execute(
                                """
                                UPDATE data_exports 
                                SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                                WHERE export_id = ?
                            """,
                                (export_id,),
                            )

                            logger.warning(
                                f"Emergency cleanup: deleted old export {export_id}"
                            )

                    except Exception as e:
                        logger.error(f"Error deleting old export {export_id}: {e}")
                        continue

            conn.commit()

            # Log aggregate emergency cleanup event
            await self.audit_logger.log_event_async(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    severity=AuditSeverity.CRITICAL,
                    user_id=None,
                    username="system",
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="storage_management",
                    resource_id=None,
                    action="emergency_cleanup_completed",
                    details={
                        "files_deleted": files_deleted,
                        "space_freed_mb": space_freed / (1024**2),
                        "trigger": "low_disk_space",
                    },
                    timestamp=datetime.now(),
                    success=True,
                )
            )

        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
            conn.rollback()
        finally:
            conn.close()

        logger.warning(
            f"Emergency cleanup completed: {files_deleted} files deleted, "
            f"{space_freed / (1024**2):.2f}MB freed"
        )

        return files_deleted, int(space_freed / (1024**2))

    async def update_retention_policies(self, policies: Dict[str, int]) -> bool:
        """Update retention policies.

        Args:
            policies: Dictionary of policy_key -> retention_days

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)

        try:
            for policy_key, retention_days in policies.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO export_retention_policies 
                    (policy_type, policy_key, retention_days, description, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        "format_based" if policy_key != "default" else "default",
                        policy_key,
                        retention_days,
                        f"Updated retention policy for {policy_key}",
                    ),
                )

            # Update in-memory policies
            self.retention_policies.update(policies)

            conn.commit()

            logger.info(f"Updated retention policies: {policies}")

            # Log audit event
            await self.audit_logger.log_event_async(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                    severity=AuditSeverity.INFO,
                    user_id=None,
                    username="system",
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="retention_policies",
                    resource_id=None,
                    action="retention_policies_updated",
                    details={"updated_policies": policies},
                    timestamp=datetime.now(),
                    success=True,
                )
            )

            return True

        except Exception as e:
            logger.error(f"Error updating retention policies: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    async def get_retention_statistics(self) -> Dict:
        """Get retention and cleanup statistics.

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)

        try:
            stats = {}

            # Export counts by status
            cursor = conn.execute(
                """
                SELECT status, COUNT(*) as count 
                FROM data_exports 
                GROUP BY status
            """
            )
            stats["exports_by_status"] = dict(cursor.fetchall())

            # Expiring soon
            expiring_threshold = datetime.now() + timedelta(hours=24)
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM data_exports 
                WHERE status = 'active' 
                AND expires_at BETWEEN CURRENT_TIMESTAMP AND ?
            """,
                (expiring_threshold,),
            )
            stats["expiring_in_24h"] = cursor.fetchone()[0]

            # Already expired but not cleaned
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM data_exports 
                WHERE status IN ('active', 'expires_soon') 
                AND expires_at < CURRENT_TIMESTAMP
            """
            )
            stats["expired_pending_cleanup"] = cursor.fetchone()[0]

            # Storage usage
            storage_info = await self.check_storage_space()
            stats["storage"] = storage_info

            # Recent cleanup activity
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM export_retention_audit 
                WHERE action = 'file_deleted' 
                AND timestamp > datetime('now', '-7 days')
            """
            )
            stats["files_deleted_last_7_days"] = cursor.fetchone()[0]

            return stats

        except Exception as e:
            logger.error(f"Error getting retention statistics: {e}")
            return {"error": str(e)}
        finally:
            conn.close()

    async def run_daily_maintenance(self) -> Dict:
        """Run daily maintenance tasks.

        Returns:
            Maintenance results
        """
        logger.info("Starting daily export retention maintenance")

        results = {
            "timestamp": datetime.now().isoformat(),
            "tasks_completed": [],
            "errors": [],
        }

        try:
            # Task 1: Mark exports expiring soon
            marked = await self.mark_exports_expiring_soon()
            results["tasks_completed"].append(
                {
                    "task": "mark_expiring_soon",
                    "count": marked,
                }
            )

            # Task 2: Check storage space
            storage_info = await self.check_storage_space()
            results["storage_check"] = storage_info

            # Task 3: Emergency cleanup if needed
            if storage_info.get("needs_emergency_cleanup", False):
                deleted, freed_mb = await self.emergency_cleanup()
                results["tasks_completed"].append(
                    {
                        "task": "emergency_cleanup",
                        "files_deleted": deleted,
                        "space_freed_mb": freed_mb,
                    }
                )
            elif storage_info.get("needs_warning", False):
                # Log low storage warning
                await self.audit_logger.log_event_async(
                    AuditEvent(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.WARNING,
                        user_id=None,
                        username="system",
                        ip_address=None,
                        user_agent=None,
                        session_id=None,
                        resource_type="storage_management",
                        resource_id=None,
                        action="low_storage_warning",
                        details={
                            "free_gb": storage_info.get("free_gb", 0),
                            "usage_percent": storage_info.get("usage_percent", 0),
                        },
                        timestamp=datetime.now(),
                        success=True,
                    )
                )

            # Task 4: Regular cleanup of expired exports
            deleted, updated = await self.cleanup_expired_exports()
            results["tasks_completed"].append(
                {
                    "task": "cleanup_expired",
                    "files_deleted": deleted,
                    "records_updated": updated,
                }
            )

            # Task 5: Update retention info for new exports
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                """
                SELECT export_id FROM data_exports 
                WHERE expires_at IS NULL 
                AND status = 'active'
                LIMIT 100
            """
            )
            exports_to_update = [row[0] for row in cursor.fetchall()]
            conn.close()

            updated_count = 0
            for export_id in exports_to_update:
                if await self.update_export_retention(export_id):
                    updated_count += 1

            if updated_count > 0:
                results["tasks_completed"].append(
                    {
                        "task": "update_retention_info",
                        "count": updated_count,
                    }
                )

        except Exception as e:
            error_msg = f"Error during daily maintenance: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        logger.info(
            f"Daily maintenance completed: {len(results['tasks_completed'])} tasks, "
            f"{len(results['errors'])} errors"
        )

        return results
