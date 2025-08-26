"""Integration module for export retention system.

This module initializes and integrates all components of the export retention system.

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
from pathlib import Path
from typing import Optional

from audit_logging import AuditLogger
from export_retention_config import ExportRetentionConfig, apply_env_config
from export_retention_scheduler import ExportRetentionScheduler, initialize_scheduler
from export_retention_service import ExportRetentionService

logger = logging.getLogger(__name__)


class ExportRetentionSystem:
    """Main integration class for the export retention system."""

    def __init__(
        self,
        db_path: str = "kasa_monitor.db",
        exports_dir: str = "exports",
        audit_logger: Optional[AuditLogger] = None,
        auto_start_scheduler: bool = True,
    ):
        """Initialize the export retention system.
        
        Args:
            db_path: Path to the database
            exports_dir: Directory containing export files
            audit_logger: Audit logging instance
            auto_start_scheduler: Whether to auto-start the scheduler
        """
        self.db_path = db_path
        self.exports_dir = Path(exports_dir)
        self.auto_start_scheduler = auto_start_scheduler
        
        # Initialize components
        self.audit_logger = audit_logger or AuditLogger(db_path=db_path)
        self.config_manager = ExportRetentionConfig(db_path=db_path, audit_logger=self.audit_logger)
        self.retention_service = ExportRetentionService(
            db_path=db_path,
            exports_dir=str(exports_dir),
            audit_logger=self.audit_logger,
        )
        self.scheduler = None
        
        logger.info("Export retention system initialized")

    async def initialize(self, apply_env_vars: bool = True) -> bool:
        """Initialize the retention system.
        
        Args:
            apply_env_vars: Whether to apply environment variable configuration
            
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing export retention system...")
            
            # Apply environment variable configuration if requested
            if apply_env_vars:
                applied_count = await apply_env_config(self.config_manager)
                logger.info(f"Applied {applied_count} environment variable configurations")
            
            # Load configuration into retention service
            retention_policies = await self.config_manager.get_retention_policies()
            await self.retention_service.update_retention_policies(retention_policies)
            
            # Initialize scheduler
            cleanup_config = await self.config_manager.get_cleanup_config()
            
            if cleanup_config.get("enabled", True):
                self.scheduler = initialize_scheduler(
                    retention_service=self.retention_service,
                    audit_logger=self.audit_logger,
                    cleanup_hour=cleanup_config.get("cleanup_hour", 2),
                    check_interval_minutes=cleanup_config.get("check_interval_minutes", 60),
                    enable_scheduler=True,
                )
                
                if self.auto_start_scheduler:
                    await self.scheduler.start()
                    logger.info("Export retention scheduler started")
            else:
                logger.info("Export retention scheduler disabled by configuration")
            
            # Run initial maintenance to update existing exports
            await self._update_existing_exports()
            
            logger.info("Export retention system initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize export retention system: {e}")
            return False

    async def _update_existing_exports(self) -> int:
        """Update retention information for existing exports.
        
        Returns:
            Number of exports updated
        """
        try:
            # Get exports without retention information
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT export_id FROM data_exports 
                WHERE expires_at IS NULL 
                AND status = 'active'
                LIMIT 1000
            """)
            
            export_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            updated_count = 0
            for export_id in export_ids:
                if await self.retention_service.update_export_retention(export_id):
                    updated_count += 1
            
            if updated_count > 0:
                logger.info(f"Updated retention information for {updated_count} existing exports")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating existing exports: {e}")
            return 0

    async def shutdown(self):
        """Shutdown the retention system."""
        try:
            if self.scheduler:
                await self.scheduler.stop()
                logger.info("Export retention scheduler stopped")
            
            logger.info("Export retention system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during retention system shutdown: {e}")

    async def run_maintenance(self) -> dict:
        """Run manual maintenance."""
        if self.scheduler:
            return await self.scheduler.force_daily_maintenance()
        else:
            return await self.retention_service.run_daily_maintenance()

    async def run_emergency_cleanup(self) -> tuple:
        """Run emergency cleanup."""
        if self.scheduler:
            results = await self.scheduler.force_storage_cleanup()
            return results["files_deleted"], results["space_freed_mb"]
        else:
            return await self.retention_service.emergency_cleanup()

    async def get_system_status(self) -> dict:
        """Get complete system status."""
        status = {
            "retention_service": await self.retention_service.get_retention_statistics(),
            "config_manager": {
                "initialized": True,
                "retention_policies": await self.config_manager.get_retention_policies(),
                "cleanup_config": await self.config_manager.get_cleanup_config(),
                "storage_config": await self.config_manager.get_storage_config(),
            },
            "scheduler": self.scheduler.get_scheduler_status() if self.scheduler else {
                "is_running": False,
                "enabled": False,
                "reason": "not_initialized"
            }
        }
        
        return status

    def get_retention_service(self) -> ExportRetentionService:
        """Get the retention service instance."""
        return self.retention_service

    def get_config_manager(self) -> ExportRetentionConfig:
        """Get the config manager instance."""
        return self.config_manager

    def get_scheduler(self) -> Optional[ExportRetentionScheduler]:
        """Get the scheduler instance."""
        return self.scheduler


# Global system instance
_retention_system: Optional[ExportRetentionSystem] = None


def get_retention_system() -> Optional[ExportRetentionSystem]:
    """Get the global retention system instance."""
    return _retention_system


async def initialize_retention_system(
    db_path: str = "kasa_monitor.db",
    exports_dir: str = "exports",
    audit_logger: Optional[AuditLogger] = None,
    auto_start_scheduler: bool = True,
    apply_env_vars: bool = True,
) -> ExportRetentionSystem:
    """Initialize the global retention system.
    
    Args:
        db_path: Path to the database
        exports_dir: Directory containing export files
        audit_logger: Audit logging instance
        auto_start_scheduler: Whether to auto-start the scheduler
        apply_env_vars: Whether to apply environment variable configuration
        
    Returns:
        Retention system instance
    """
    global _retention_system
    
    if _retention_system:
        logger.warning("Retention system already initialized")
        return _retention_system
    
    _retention_system = ExportRetentionSystem(
        db_path=db_path,
        exports_dir=exports_dir,
        audit_logger=audit_logger,
        auto_start_scheduler=auto_start_scheduler,
    )
    
    success = await _retention_system.initialize(apply_env_vars=apply_env_vars)
    if not success:
        logger.error("Failed to initialize retention system")
        _retention_system = None
        raise RuntimeError("Retention system initialization failed")
    
    logger.info("Global export retention system initialized successfully")
    return _retention_system


async def shutdown_retention_system():
    """Shutdown the global retention system."""
    global _retention_system
    
    if _retention_system:
        await _retention_system.shutdown()
        _retention_system = None
        logger.info("Global retention system shutdown completed")


# Startup integration for main application
async def startup_retention_system():
    """Startup function to be called by main application."""
    try:
        # Get configuration from environment or use defaults
        db_path = os.getenv("KASA_DB_PATH", "kasa_monitor.db")
        exports_dir = os.getenv("EXPORTS_DIR", "exports")
        
        # Check if retention is enabled
        retention_enabled = os.getenv("EXPORT_RETENTION_ENABLED", "true").lower() == "true"
        
        if not retention_enabled:
            logger.info("Export retention system disabled by configuration")
            return None
        
        # Initialize the system
        system = await initialize_retention_system(
            db_path=db_path,
            exports_dir=exports_dir,
            auto_start_scheduler=True,
            apply_env_vars=True,
        )
        
        logger.info("Export retention system startup completed")
        return system
        
    except Exception as e:
        logger.error(f"Failed to start retention system: {e}")
        return None


# Shutdown integration for main application
async def shutdown_retention_system_handler():
    """Shutdown handler to be called by main application."""
    try:
        await shutdown_retention_system()
        logger.info("Export retention system shutdown handler completed")
    except Exception as e:
        logger.error(f"Error in retention system shutdown handler: {e}")


# Health check function
async def health_check_retention_system() -> dict:
    """Health check for retention system."""
    system = get_retention_system()
    
    if not system:
        return {
            "status": "unhealthy",
            "reason": "system_not_initialized",
            "details": {}
        }
    
    try:
        status = await system.get_system_status()
        
        # Check if scheduler is running when it should be
        scheduler_status = status["scheduler"]
        config_enabled = status["config_manager"]["cleanup_config"].get("enabled", True)
        
        is_healthy = True
        issues = []
        
        if config_enabled and not scheduler_status.get("is_running", False):
            is_healthy = False
            issues.append("scheduler_not_running")
        
        # Check storage space
        storage_info = status["retention_service"].get("storage", {})
        if storage_info.get("needs_emergency_cleanup", False):
            is_healthy = False
            issues.append("low_storage_space")
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "issues": issues,
            "details": status
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "reason": "health_check_failed",
            "error": str(e),
            "details": {}
        }