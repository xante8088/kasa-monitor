"""Background scheduler for export retention tasks.

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
from datetime import datetime, time, timedelta
from typing import Dict, Optional

from audit_logging import AuditEvent, AuditEventType, AuditLogger, AuditSeverity
from export_retention_service import ExportRetentionService

logger = logging.getLogger(__name__)


class ExportRetentionScheduler:
    """Scheduler for automated export retention and cleanup tasks."""

    def __init__(
        self,
        retention_service: ExportRetentionService,
        audit_logger: Optional[AuditLogger] = None,
        cleanup_hour: int = 2,  # 2 AM by default
        check_interval_minutes: int = 60,  # Check every hour
        enable_scheduler: bool = True,
    ):
        """Initialize the retention scheduler.
        
        Args:
            retention_service: Export retention service instance
            audit_logger: Audit logging instance
            cleanup_hour: Hour of day to run daily cleanup (0-23)
            check_interval_minutes: Minutes between scheduler checks
            enable_scheduler: Whether to enable the scheduler
        """
        self.retention_service = retention_service
        self.audit_logger = audit_logger or retention_service.audit_logger
        self.cleanup_hour = max(0, min(23, cleanup_hour))
        self.check_interval = timedelta(minutes=max(1, check_interval_minutes))
        self.enable_scheduler = enable_scheduler
        
        # Scheduler state
        self.is_running = False
        self.last_daily_cleanup = None
        self.last_storage_check = None
        self.scheduler_task = None
        
        # Configuration from environment
        self.cleanup_hour = int(os.getenv("EXPORT_CLEANUP_HOUR", str(cleanup_hour)))
        self.enable_scheduler = os.getenv("EXPORT_RETENTION_ENABLED", "true").lower() == "true"
        
        logger.info(f"Export retention scheduler initialized - "
                   f"cleanup_hour={self.cleanup_hour}, enabled={self.enable_scheduler}")

    async def start(self):
        """Start the retention scheduler."""
        if not self.enable_scheduler:
            logger.info("Export retention scheduler is disabled")
            return
        
        if self.is_running:
            logger.warning("Export retention scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("Export retention scheduler started")
        
        # Log startup event
        await self.audit_logger.log_event_async(AuditEvent(
            event_type=AuditEventType.SYSTEM_STARTUP,
            severity=AuditSeverity.INFO,
            user_id=None,
            username="system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="export_retention_scheduler",
            resource_id=None,
            action="scheduler_started",
            details={
                "cleanup_hour": self.cleanup_hour,
                "check_interval_minutes": self.check_interval.total_seconds() / 60,
            },
            timestamp=datetime.now(),
            success=True,
        ))

    async def stop(self):
        """Stop the retention scheduler."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Export retention scheduler stopped")
        
        # Log shutdown event
        await self.audit_logger.log_event_async(AuditEvent(
            event_type=AuditEventType.SYSTEM_SHUTDOWN,
            severity=AuditSeverity.INFO,
            user_id=None,
            username="system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="export_retention_scheduler",
            resource_id=None,
            action="scheduler_stopped",
            details={},
            timestamp=datetime.now(),
            success=True,
        ))

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Starting export retention scheduler loop")
        
        while self.is_running:
            try:
                now = datetime.now()
                
                # Check if it's time for daily cleanup
                if await self._should_run_daily_cleanup(now):
                    logger.info("Running scheduled daily maintenance")
                    try:
                        results = await self.retention_service.run_daily_maintenance()
                        self.last_daily_cleanup = now.date()
                        
                        # Log successful maintenance
                        await self.audit_logger.log_event_async(AuditEvent(
                            event_type=AuditEventType.DATA_EXPORT,
                            severity=AuditSeverity.INFO,
                            user_id=None,
                            username="system",
                            ip_address=None,
                            user_agent=None,
                            session_id=None,
                            resource_type="export_maintenance",
                            resource_id=None,
                            action="daily_maintenance_completed",
                            details=results,
                            timestamp=now,
                            success=True,
                        ))
                        
                        logger.info(f"Daily maintenance completed: {len(results.get('tasks_completed', []))} tasks")
                        
                    except Exception as e:
                        logger.error(f"Error during daily maintenance: {e}")
                        await self._log_maintenance_error(e, "daily_maintenance")
                
                # Check storage space every hour during business hours
                if await self._should_check_storage(now):
                    try:
                        storage_info = await self.retention_service.check_storage_space()
                        self.last_storage_check = now
                        
                        # Handle storage warnings
                        if storage_info.get("needs_emergency_cleanup", False):
                            logger.warning("Emergency cleanup triggered by low disk space")
                            deleted, freed_mb = await self.retention_service.emergency_cleanup()
                            
                            await self.audit_logger.log_event_async(AuditEvent(
                                event_type=AuditEventType.SYSTEM_ERROR,
                                severity=AuditSeverity.CRITICAL,
                                user_id=None,
                                username="system",
                                ip_address=None,
                                user_agent=None,
                                session_id=None,
                                resource_type="storage_management",
                                resource_id=None,
                                action="emergency_cleanup_triggered",
                                details={
                                    "files_deleted": deleted,
                                    "space_freed_mb": freed_mb,
                                    "storage_info": storage_info,
                                },
                                timestamp=now,
                                success=True,
                            ))
                            
                        elif storage_info.get("needs_warning", False):
                            await self._log_storage_warning(storage_info)
                            
                    except Exception as e:
                        logger.error(f"Error during storage check: {e}")
                        await self._log_maintenance_error(e, "storage_check")
                
                # Regular cleanup of expired exports (more frequent than daily maintenance)
                if now.minute == 0:  # Run at the top of every hour
                    try:
                        # Mark exports expiring soon
                        marked = await self.retention_service.mark_exports_expiring_soon()
                        if marked > 0:
                            logger.info(f"Marked {marked} exports as expiring soon")
                        
                        # Clean up a small batch of expired exports
                        deleted, updated = await self.retention_service.cleanup_expired_exports(batch_size=10)
                        if deleted > 0 or updated > 0:
                            logger.info(f"Hourly cleanup: {deleted} files deleted, {updated} records updated")
                            
                    except Exception as e:
                        logger.error(f"Error during hourly cleanup: {e}")
                        await self._log_maintenance_error(e, "hourly_cleanup")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval.total_seconds())
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in scheduler loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait a minute before retrying
        
        logger.info("Export retention scheduler loop ended")

    async def _should_run_daily_cleanup(self, now: datetime) -> bool:
        """Check if daily cleanup should run.
        
        Args:
            now: Current datetime
            
        Returns:
            True if daily cleanup should run
        """
        # Check if we're at the right hour
        if now.hour != self.cleanup_hour:
            return False
        
        # Check if we haven't run today
        if self.last_daily_cleanup and self.last_daily_cleanup >= now.date():
            return False
        
        return True

    async def _should_check_storage(self, now: datetime) -> bool:
        """Check if storage monitoring should run.
        
        Args:
            now: Current datetime
            
        Returns:
            True if storage check should run
        """
        # Run storage check every hour during business hours (8 AM - 6 PM)
        # or if we haven't checked in the last 4 hours
        if 8 <= now.hour <= 18:
            # Business hours - check every hour
            if not self.last_storage_check or (now - self.last_storage_check) >= timedelta(hours=1):
                return True
        else:
            # Off hours - check every 4 hours
            if not self.last_storage_check or (now - self.last_storage_check) >= timedelta(hours=4):
                return True
        
        return False

    async def _log_maintenance_error(self, error: Exception, task_type: str):
        """Log maintenance task error.
        
        Args:
            error: Exception that occurred
            task_type: Type of maintenance task
        """
        await self.audit_logger.log_event_async(AuditEvent(
            event_type=AuditEventType.SYSTEM_ERROR,
            severity=AuditSeverity.ERROR,
            user_id=None,
            username="system",
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type="export_maintenance",
            resource_id=None,
            action=f"{task_type}_error",
            details={
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            timestamp=datetime.now(),
            success=False,
            error_message=str(error),
        ))

    async def _log_storage_warning(self, storage_info: Dict):
        """Log storage warning.
        
        Args:
            storage_info: Storage information
        """
        await self.audit_logger.log_event_async(AuditEvent(
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
            details=storage_info,
            timestamp=datetime.now(),
            success=True,
        ))

    async def force_daily_maintenance(self) -> Dict:
        """Force run daily maintenance (for manual triggers or API calls).
        
        Returns:
            Maintenance results
        """
        logger.info("Forcing daily maintenance run")
        
        try:
            results = await self.retention_service.run_daily_maintenance()
            self.last_daily_cleanup = datetime.now().date()
            
            # Log forced maintenance
            await self.audit_logger.log_event_async(AuditEvent(
                event_type=AuditEventType.DATA_EXPORT,
                severity=AuditSeverity.INFO,
                user_id=None,
                username="system",
                ip_address=None,
                user_agent=None,
                session_id=None,
                resource_type="export_maintenance",
                resource_id=None,
                action="forced_daily_maintenance",
                details=results,
                timestamp=datetime.now(),
                success=True,
            ))
            
            logger.info("Forced daily maintenance completed")
            return results
            
        except Exception as e:
            logger.error(f"Error during forced daily maintenance: {e}")
            await self._log_maintenance_error(e, "forced_daily_maintenance")
            raise

    async def force_storage_cleanup(self) -> Dict:
        """Force storage cleanup (for manual triggers or API calls).
        
        Returns:
            Cleanup results
        """
        logger.info("Forcing storage cleanup")
        
        try:
            storage_info = await self.retention_service.check_storage_space()
            deleted, freed_mb = await self.retention_service.emergency_cleanup()
            
            results = {
                "storage_before": storage_info,
                "files_deleted": deleted,
                "space_freed_mb": freed_mb,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Log forced cleanup
            await self.audit_logger.log_event_async(AuditEvent(
                event_type=AuditEventType.DATA_DELETED,
                severity=AuditSeverity.WARNING,
                user_id=None,
                username="system",
                ip_address=None,
                user_agent=None,
                session_id=None,
                resource_type="storage_management",
                resource_id=None,
                action="forced_storage_cleanup",
                details=results,
                timestamp=datetime.now(),
                success=True,
            ))
            
            logger.info(f"Forced storage cleanup completed: {deleted} files deleted, {freed_mb}MB freed")
            return results
            
        except Exception as e:
            logger.error(f"Error during forced storage cleanup: {e}")
            await self._log_maintenance_error(e, "forced_storage_cleanup")
            raise

    def get_scheduler_status(self) -> Dict:
        """Get scheduler status information.
        
        Returns:
            Scheduler status
        """
        return {
            "is_running": self.is_running,
            "enabled": self.enable_scheduler,
            "cleanup_hour": self.cleanup_hour,
            "check_interval_minutes": self.check_interval.total_seconds() / 60,
            "last_daily_cleanup": self.last_daily_cleanup.isoformat() if self.last_daily_cleanup else None,
            "last_storage_check": self.last_storage_check.isoformat() if self.last_storage_check else None,
            "next_daily_cleanup": self._get_next_daily_cleanup(),
        }

    def _get_next_daily_cleanup(self) -> str:
        """Get next scheduled daily cleanup time.
        
        Returns:
            Next cleanup time as ISO string
        """
        now = datetime.now()
        
        # Calculate next cleanup time
        next_cleanup = now.replace(hour=self.cleanup_hour, minute=0, second=0, microsecond=0)
        
        # If we've passed today's cleanup time, schedule for tomorrow
        if now >= next_cleanup:
            next_cleanup += timedelta(days=1)
        
        return next_cleanup.isoformat()


# Global scheduler instance
_scheduler_instance: Optional[ExportRetentionScheduler] = None


def get_scheduler() -> Optional[ExportRetentionScheduler]:
    """Get the global scheduler instance."""
    return _scheduler_instance


def initialize_scheduler(
    retention_service: ExportRetentionService,
    audit_logger: Optional[AuditLogger] = None,
    **kwargs
) -> ExportRetentionScheduler:
    """Initialize the global scheduler instance.
    
    Args:
        retention_service: Export retention service
        audit_logger: Audit logger instance
        **kwargs: Additional scheduler configuration
        
    Returns:
        Scheduler instance
    """
    global _scheduler_instance
    
    if _scheduler_instance:
        logger.warning("Scheduler already initialized")
        return _scheduler_instance
    
    _scheduler_instance = ExportRetentionScheduler(
        retention_service=retention_service,
        audit_logger=audit_logger,
        **kwargs
    )
    
    logger.info("Export retention scheduler initialized globally")
    return _scheduler_instance


async def start_scheduler():
    """Start the global scheduler."""
    if _scheduler_instance:
        await _scheduler_instance.start()
    else:
        logger.error("Scheduler not initialized - call initialize_scheduler() first")


async def stop_scheduler():
    """Stop the global scheduler."""
    if _scheduler_instance:
        await _scheduler_instance.stop()