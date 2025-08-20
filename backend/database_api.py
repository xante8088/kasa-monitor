"""
Database Management API endpoints for Kasa Monitor
Provides backup, restore, migration, and health check endpoints
"""

import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import alembic.command
import alembic.config
from audit_logging import AuditEvent, AuditEventType, AuditLogger, AuditSeverity
from backup_manager import BackupManager
from database_pool import get_async_session, get_pool
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/database", tags=["database"])

# Initialize backup manager
backup_manager = None
audit_logger = None


def get_audit_logger() -> Optional[AuditLogger]:
    """Get the global audit logger instance"""
    global audit_logger
    if audit_logger is None:
        try:
            audit_logger = AuditLogger(
                db_path="kasa_monitor.db", log_dir="./logs/audit"
            )
        except Exception as e:
            logger.error(f"Failed to initialize audit logger: {e}")
    return audit_logger


def get_backup_manager() -> BackupManager:
    """Get or create backup manager instance"""
    global backup_manager
    if backup_manager is None:
        db_path = os.getenv("DATABASE_PATH", "data/kasa_monitor.db")
        backup_dir = os.getenv("BACKUP_DIR", "/backups")
        encryption_key = os.getenv("BACKUP_ENCRYPTION_KEY")
        retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

        backup_manager = BackupManager(
            db_path=db_path,
            backup_dir=backup_dir,
            encryption_key=encryption_key,
            retention_days=retention_days,
            audit_logger=get_audit_logger(),
        )

        # Start scheduler for automatic backups
        backup_manager.start_scheduler()

        # Schedule automatic backups if configured
        backup_schedule = os.getenv("BACKUP_SCHEDULE", "0 2 * * *")
        if backup_schedule:
            backup_manager.schedule_automatic_backups(backup_schedule)
            logger.info(f"Automatic backups scheduled: {backup_schedule}")

    return backup_manager


@router.get("/health")
async def database_health():
    """Check database health and connection pool status"""
    pool = get_pool()
    health_status = await pool.async_health_check()

    # Add backup status
    bm = get_backup_manager()
    backup_stats = bm.get_backup_statistics()

    return {
        "database": health_status,
        "backups": backup_stats,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/stats")
async def database_statistics():
    """Get detailed database and pool statistics"""
    pool = get_pool()
    stats = pool.get_statistics()

    # Add database size information
    db_path = os.getenv("DATABASE_PATH", "data/kasa_monitor.db")
    if os.path.exists(db_path):
        stats["database_size_mb"] = os.path.getsize(db_path) / (1024 * 1024)

    return stats


@router.post("/backup")
async def create_backup(
    background_tasks: BackgroundTasks,
    backup_type: str = "manual",
    description: str = "",
    compress: bool = True,
    encrypt: bool = True,
):
    """Create a database backup"""
    bm = get_backup_manager()

    # Create backup in background
    result = await bm.create_backup(
        backup_type=backup_type,
        description=description,
        compress=compress,
        encrypt=encrypt,
    )

    if result["status"] == "failed":
        raise HTTPException(
            status_code=500, detail=result.get("error", "Backup failed")
        )

    return result


@router.get("/backups")
async def list_backups(backup_type: Optional[str] = None, limit: Optional[int] = 50):
    """List available backups"""
    bm = get_backup_manager()
    backups = await bm.list_backups(backup_type=backup_type, limit=limit)
    return {"backups": backups, "count": len(backups)}


@router.post("/restore/{backup_name}")
async def restore_backup(
    backup_name: str, target_path: Optional[str] = None, verify_checksum: bool = True
):
    """Restore a database backup"""
    bm = get_backup_manager()

    result = await bm.restore_backup(
        backup_name=backup_name,
        target_path=target_path,
        verify_checksum=verify_checksum,
    )

    if result["status"] == "failed":
        raise HTTPException(
            status_code=500, detail=result.get("error", "Restore failed")
        )

    return result


@router.post("/verify/{backup_name}")
async def verify_backup(backup_name: str):
    """Verify backup integrity"""
    bm = get_backup_manager()
    result = await bm.verify_backup(backup_name)

    if result["status"] == "failed":
        raise HTTPException(
            status_code=400, detail=result.get("error", "Verification failed")
        )

    return result


@router.delete("/backup/{backup_name}")
async def delete_backup(backup_name: str):
    """Delete a specific backup"""
    bm = get_backup_manager()

    # Find and delete backup
    backups = await bm.list_backups()
    for backup in backups:
        if backup["name"] == backup_name:
            backup_file = Path(bm.backup_dir) / backup["filename"]
            if backup_file.exists():
                backup_file.unlink()

                # Update metadata
                bm.metadata["backups"] = [
                    b for b in bm.metadata["backups"] if b["name"] != backup_name
                ]
                bm._save_metadata()

                return {"message": f"Backup {backup_name} deleted successfully"}

    raise HTTPException(status_code=404, detail="Backup not found")


@router.get("/backup/{backup_name}/download")
async def download_backup(backup_name: str):
    """Download a backup file"""
    bm = get_backup_manager()

    # Find backup
    backups = await bm.list_backups()
    for backup in backups:
        if backup["name"] == backup_name:
            backup_file = Path(bm.backup_dir) / backup["filename"]
            if backup_file.exists():
                return FileResponse(
                    path=str(backup_file),
                    filename=backup["filename"],
                    media_type="application/octet-stream",
                )

    raise HTTPException(status_code=404, detail="Backup not found")


@router.post("/backup/upload")
async def upload_backup(file: UploadFile = File(...), description: str = ""):
    """Upload a backup file"""
    # Secure file upload validation
    try:
        from security_fixes.critical.file_upload_security import SecureFileUploadManager

        upload_manager = SecureFileUploadManager()
        upload_result = await upload_manager.handle_upload(file, "backup")

        bm = get_backup_manager()
        backup_name = (
            f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        )
        backup_path = Path(bm.backup_dir) / backup_name

        # Move approved file from quarantine to backup directory
        if not upload_manager.approve_quarantined_file(
            upload_result["quarantine_path"], str(backup_path)
        ):
            raise HTTPException(status_code=500, detail="Failed to move backup file")

    except ImportError:
        # Fallback to basic validation
        if not file.filename or not file.filename.lower().endswith(
            (".zip", ".7z", ".json")
        ):
            raise HTTPException(status_code=400, detail="Invalid backup file type")

        content = await file.read()
        if len(content) > 100 * 1024 * 1024:  # 100MB limit for backups
            raise HTTPException(status_code=400, detail="Backup file too large")

        bm = get_backup_manager()
        backup_name = (
            f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        )
        backup_path = Path(bm.backup_dir) / backup_name

        with open(backup_path, "wb") as f:
            f.write(content)

    # Add to metadata
    backup_info = {
        "name": backup_name.rsplit(".", 1)[0],
        "filename": backup_name,
        "timestamp": datetime.now().isoformat(),
        "type": "uploaded",
        "description": description or f"Uploaded backup: {file.filename}",
        "size": backup_path.stat().st_size,
        "status": "completed",
    }

    bm.metadata["backups"].append(backup_info)
    bm._save_metadata()

    return backup_info


@router.post("/backup/schedule")
async def schedule_backups(schedule: str = "0 2 * * *", backup_type: str = "scheduled"):
    """Schedule automatic backups"""
    bm = get_backup_manager()

    try:
        bm.schedule_automatic_backups(schedule, backup_type)
        return {
            "message": "Backup schedule updated",
            "schedule": schedule,
            "backup_type": backup_type,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_backups():
    """Manually trigger cleanup of old backups"""
    bm = get_backup_manager()
    removed_count = await bm.cleanup_old_backups()

    return {"message": f"Cleanup completed", "backups_removed": removed_count}


# Migration endpoints
@router.get("/migrations")
async def list_migrations():
    """List all database migrations"""
    try:
        alembic_cfg = alembic.config.Config("alembic.ini")

        # Get current revision
        from alembic import script
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine

        db_path = os.getenv("DATABASE_PATH", "data/kasa_monitor.db")
        engine = create_engine(f"sqlite:///{db_path}")

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()

        # Get all revisions
        script_dir = script.ScriptDirectory.from_config(alembic_cfg)
        revisions = []

        for revision in script_dir.walk_revisions():
            revisions.append(
                {
                    "revision": revision.revision,
                    "description": revision.doc,
                    "branch_labels": revision.branch_labels,
                    "is_current": revision.revision == current_rev,
                }
            )

        return {"current_revision": current_rev, "revisions": revisions}
    except Exception as e:
        logger.error(f"Error listing migrations: {e}")
        return {"current_revision": None, "revisions": [], "error": str(e)}


@router.post("/migrate")
async def run_migration(
    revision: str = "head", background_tasks: BackgroundTasks = None
):
    """Run database migrations"""
    try:
        # Create backup before migration
        bm = get_backup_manager()
        backup_result = await bm.create_backup(
            backup_type="pre_migration",
            description=f"Automatic backup before migration to {revision}",
        )

        # Run migration
        alembic_cfg = alembic.config.Config("alembic.ini")
        alembic.command.upgrade(alembic_cfg, revision)

        return {
            "message": "Migration completed successfully",
            "revision": revision,
            "backup": backup_result["name"],
        }
    except Exception as e:
        logger.error(f"Migration failed: {e}")

        # Log migration failure
        audit_log = get_audit_logger()
        if audit_log:
            try:
                error_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    severity=AuditSeverity.CRITICAL,
                    action="Database migration failed",
                    details={
                        "operation": "database_migration",
                        "target_revision": revision,
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "backup_created": (
                            backup_result.get("name")
                            if "backup_result" in locals()
                            else "unknown"
                        ),
                    },
                )
                await audit_log.log_event_async(error_event)
            except Exception as audit_error:
                logger.error(f"Failed to log migration failure: {audit_error}")

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate/rollback")
async def rollback_migration(revision: str = "-1"):
    """Rollback database migration"""
    try:
        # Create backup before rollback
        bm = get_backup_manager()
        backup_result = await bm.create_backup(
            backup_type="pre_rollback",
            description=f"Automatic backup before rollback to {revision}",
        )

        # Run rollback
        alembic_cfg = alembic.config.Config("alembic.ini")
        alembic.command.downgrade(alembic_cfg, revision)

        return {
            "message": "Rollback completed successfully",
            "revision": revision,
            "backup": backup_result["name"],
        }
    except Exception as e:
        logger.error(f"Rollback failed: {e}")

        # Log rollback failure
        audit_log = get_audit_logger()
        if audit_log:
            try:
                error_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    severity=AuditSeverity.CRITICAL,
                    action="Database rollback failed",
                    details={
                        "operation": "database_rollback",
                        "target_revision": revision,
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "backup_created": (
                            backup_result.get("name")
                            if "backup_result" in locals()
                            else "unknown"
                        ),
                    },
                )
                await audit_log.log_event_async(error_event)
            except Exception as audit_error:
                logger.error(f"Failed to log rollback failure: {audit_error}")

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate/create")
async def create_migration(message: str, autogenerate: bool = True):
    """Create a new migration"""
    try:
        alembic_cfg = alembic.config.Config("alembic.ini")

        if autogenerate:
            alembic.command.revision(alembic_cfg, message=message, autogenerate=True)
        else:
            alembic.command.revision(alembic_cfg, message=message)

        return {
            "message": "Migration created successfully",
            "description": message,
            "autogenerate": autogenerate,
        }
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Connection pool management
@router.post("/pool/optimize")
async def optimize_connection_pool():
    """Optimize connection pool settings"""
    pool = get_pool()
    pool.optimize_pool()

    return {
        "message": "Pool optimization completed",
        "statistics": pool.get_statistics(),
    }


@router.post("/pool/reset")
async def reset_connection_pool():
    """Reset connection pool"""
    pool = get_pool()

    # Close existing connections
    await pool.async_close()

    # Reinitialize
    pool._setup_async_engine()

    return {
        "message": "Connection pool reset successfully",
        "statistics": pool.get_statistics(),
    }


@router.get("/pool/connections")
async def get_active_connections():
    """Get information about active connections"""
    pool = get_pool()

    return {
        "active": pool.active_connections,
        "total": pool.total_connections,
        "failed": pool.failed_connections,
        "pool_size": pool.pool_size,
        "max_overflow": pool.max_overflow,
    }


# Database maintenance
@router.post("/maintenance/vacuum")
async def vacuum_database(db: AsyncSession = Depends(get_async_session)):
    """Run VACUUM on SQLite database"""
    try:
        # Note: VACUUM cannot be run in a transaction
        await db.execute(text("VACUUM"))

        # Get database size after vacuum
        db_path = os.getenv("DATABASE_PATH", "data/kasa_monitor.db")
        size_after = (
            os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0
        )

        return {"message": "Database vacuum completed", "size_mb": size_after}
    except Exception as e:
        logger.error(f"Vacuum failed: {e}")

        # Log vacuum failure
        audit_log = get_audit_logger()
        if audit_log:
            try:
                error_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    severity=AuditSeverity.ERROR,
                    action="Database vacuum operation failed",
                    details={
                        "operation": "database_vacuum",
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "database_path": str(db_path),
                    },
                )
                await audit_log.log_event_async(error_event)
            except Exception as audit_error:
                logger.error(f"Failed to log vacuum failure: {audit_error}")

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/analyze")
async def analyze_database(db: AsyncSession = Depends(get_async_session)):
    """Run ANALYZE on database to update statistics"""
    try:
        await db.execute(text("ANALYZE"))
        return {"message": "Database analysis completed"}
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/integrity-check")
async def check_database_integrity(db: AsyncSession = Depends(get_async_session)):
    """Check database integrity"""
    try:
        result = await db.execute(text("PRAGMA integrity_check"))
        check_result = result.fetchall()

        is_ok = len(check_result) == 1 and check_result[0][0] == "ok"

        return {
            "status": "healthy" if is_ok else "corrupted",
            "result": [row[0] for row in check_result],
        }
    except Exception as e:
        logger.error(f"Integrity check failed: {e}")

        # Log integrity check failure
        audit_log = get_audit_logger()
        if audit_log:
            try:
                error_event = AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    severity=AuditSeverity.CRITICAL,
                    action="Database integrity check failed",
                    details={
                        "operation": "database_integrity_check",
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "check_type": "PRAGMA integrity_check",
                    },
                )
                await audit_log.log_event_async(error_event)
            except Exception as audit_error:
                logger.error(f"Failed to log integrity check failure: {audit_error}")

        raise HTTPException(status_code=500, detail=str(e))
