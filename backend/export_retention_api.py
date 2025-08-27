"""API endpoints for export retention management.

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
from datetime import datetime
from typing import Dict, List, Optional

from data_export_service import DataExportService
from export_retention_config import ExportRetentionConfig
from export_retention_scheduler import get_scheduler
from export_retention_service import ExportRetentionService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exports/retention", tags=["Export Retention"])


# Pydantic models
class RetentionPolicyUpdate(BaseModel):
    """Model for updating retention policies."""

    policies: Dict[str, int] = Field(
        ..., description="Format to retention days mapping"
    )


class RetentionConfigUpdate(BaseModel):
    """Model for updating retention configuration."""

    key: str = Field(..., description="Configuration key")
    value: str = Field(..., description="Configuration value")


class ExtendRetentionRequest(BaseModel):
    """Model for extending export retention."""

    export_id: str = Field(..., description="Export ID")
    additional_days: int = Field(
        ..., gt=0, le=365, description="Additional days to extend retention"
    )


class RetentionStats(BaseModel):
    """Model for retention statistics."""

    exports_by_status: Dict[str, int]
    expiring_in_24h: int
    expired_pending_cleanup: int
    storage: Dict
    files_deleted_last_7_days: int


class MaintenanceResults(BaseModel):
    """Model for maintenance results."""

    timestamp: str
    tasks_completed: List[Dict]
    errors: List[str]


# Dependency injection
def get_retention_service() -> ExportRetentionService:
    """Get retention service instance."""
    return ExportRetentionService()


def get_retention_config() -> ExportRetentionConfig:
    """Get retention config instance."""
    return ExportRetentionConfig()


def get_export_service() -> DataExportService:
    """Get data export service instance."""
    return DataExportService()


@router.get("/status", response_model=Dict)
async def get_retention_status(
    current_user: dict = Depends(get_current_user),
    retention_service: ExportRetentionService = Depends(get_retention_service),
):
    """Get export retention system status."""
    try:
        stats = await retention_service.get_retention_statistics()

        # Add scheduler status if available
        scheduler = get_scheduler()
        if scheduler:
            stats["scheduler"] = scheduler.get_scheduler_status()
        else:
            stats["scheduler"] = {"is_running": False, "enabled": False}

        return {"success": True, "data": stats}

    except Exception as e:
        logger.error(f"Error getting retention status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get retention status")


@router.get("/policies", response_model=Dict)
async def get_retention_policies(
    current_user: dict = Depends(get_current_user),
    retention_config: ExportRetentionConfig = Depends(get_retention_config),
):
    """Get current retention policies."""
    try:
        policies = await retention_config.get_retention_policies()
        return {"success": True, "data": policies}

    except Exception as e:
        logger.error(f"Error getting retention policies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get retention policies")


@router.put("/policies", response_model=Dict)
async def update_retention_policies(
    policy_update: RetentionPolicyUpdate,
    current_user: dict = Depends(require_admin),
    retention_config: ExportRetentionConfig = Depends(get_retention_config),
    retention_service: ExportRetentionService = Depends(get_retention_service),
):
    """Update retention policies (admin only)."""
    try:
        # Validate policy values
        for format_name, days in policy_update.policies.items():
            if days < 1 or days > 3650:  # 1 day to 10 years
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid retention days for {format_name}: {days}. Must be between 1 and 3650.",
                )

        # Update in configuration
        success = await retention_config.update_retention_policies(
            policy_update.policies, current_user["id"]
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to update retention policies"
            )

        # Update in retention service
        await retention_service.update_retention_policies(policy_update.policies)

        return {"success": True, "message": "Retention policies updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating retention policies: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update retention policies"
        )


@router.get("/config/{category}", response_model=Dict)
async def get_retention_config(
    category: str,
    current_user: dict = Depends(require_admin),
    retention_config: ExportRetentionConfig = Depends(get_retention_config),
):
    """Get retention configuration for a category (admin only)."""
    try:
        config = await retention_config.get_category_config(category)
        return {"success": True, "data": config}

    except Exception as e:
        logger.error(f"Error getting retention config for {category}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get retention configuration"
        )


@router.put("/config", response_model=Dict)
async def update_retention_config(
    config_update: RetentionConfigUpdate,
    current_user: dict = Depends(require_admin),
    retention_config: ExportRetentionConfig = Depends(get_retention_config),
):
    """Update retention configuration (admin only)."""
    try:
        success = await retention_config.set_config(
            config_update.key, config_update.value, current_user["id"]
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to update configuration"
            )

        return {"success": True, "message": "Configuration updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating retention config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.get("/exports/expiring", response_model=Dict)
async def get_expiring_exports(
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours to look ahead"),
    current_user: dict = Depends(get_current_user),
    export_service: DataExportService = Depends(get_export_service),
):
    """Get user's exports that are expiring soon."""
    try:
        # Regular users see only their exports, admins can see all
        if current_user.get("is_admin", False):
            retention_service = ExportRetentionService()
            exports = await retention_service.get_expiring_exports(hours_ahead)
        else:
            exports = await export_service.get_expiring_exports_for_user(
                current_user["id"], hours_ahead
            )

        return {"success": True, "data": exports}

    except Exception as e:
        logger.error(f"Error getting expiring exports: {e}")
        raise HTTPException(status_code=500, detail="Failed to get expiring exports")


@router.get("/exports/{export_id}/retention", response_model=Dict)
async def get_export_retention_info(
    export_id: str,
    current_user: dict = Depends(get_current_user),
    export_service: DataExportService = Depends(get_export_service),
):
    """Get retention information for a specific export."""
    try:
        # Check if user owns the export or is admin
        export_details = await export_service.get_export_by_id(export_id)
        if not export_details:
            raise HTTPException(status_code=404, detail="Export not found")

        if (
            not current_user.get("is_admin", False)
            and export_details.get("user_id") != current_user["id"]
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        retention_info = await export_service.get_export_retention_info(export_id)
        if not retention_info:
            raise HTTPException(
                status_code=404, detail="Retention information not found"
            )

        return {"success": True, "data": retention_info}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting export retention info: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get retention information"
        )


@router.put("/exports/extend", response_model=Dict)
async def extend_export_retention(
    extend_request: ExtendRetentionRequest,
    current_user: dict = Depends(get_current_user),
    export_service: DataExportService = Depends(get_export_service),
):
    """Extend retention period for an export."""
    try:
        # Check if user owns the export or is admin
        export_details = await export_service.get_export_by_id(extend_request.export_id)
        if not export_details:
            raise HTTPException(status_code=404, detail="Export not found")

        if (
            not current_user.get("is_admin", False)
            and export_details.get("user_id") != current_user["id"]
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        # Extend retention
        success = await export_service.extend_export_retention(
            extend_request.export_id, extend_request.additional_days
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to extend retention")

        return {
            "success": True,
            "message": f"Retention extended by {extend_request.additional_days} days",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extending export retention: {e}")
        raise HTTPException(status_code=500, detail="Failed to extend retention")


@router.post("/maintenance/run", response_model=Dict)
async def force_maintenance(
    current_user: dict = Depends(require_admin),
):
    """Force run daily maintenance (admin only)."""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            # Run maintenance directly if scheduler not available
            retention_service = ExportRetentionService()
            results = await retention_service.run_daily_maintenance()
        else:
            results = await scheduler.force_daily_maintenance()

        return {"success": True, "data": results}

    except Exception as e:
        logger.error(f"Error running forced maintenance: {e}")
        raise HTTPException(status_code=500, detail="Failed to run maintenance")


@router.post("/cleanup/emergency", response_model=Dict)
async def force_emergency_cleanup(
    current_user: dict = Depends(require_admin),
):
    """Force emergency storage cleanup (admin only)."""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            # Run cleanup directly if scheduler not available
            retention_service = ExportRetentionService()
            deleted, freed_mb = await retention_service.emergency_cleanup()
            results = {
                "files_deleted": deleted,
                "space_freed_mb": freed_mb,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            results = await scheduler.force_storage_cleanup()

        return {"success": True, "data": results}

    except Exception as e:
        logger.error(f"Error running emergency cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to run emergency cleanup")


@router.get("/statistics", response_model=Dict)
async def get_retention_statistics(
    current_user: dict = Depends(get_current_user),
    retention_service: ExportRetentionService = Depends(get_retention_service),
):
    """Get detailed retention statistics."""
    try:
        stats = await retention_service.get_retention_statistics()
        return {"success": True, "data": stats}

    except Exception as e:
        logger.error(f"Error getting retention statistics: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get retention statistics"
        )


@router.post("/exports/{export_id}/download", response_model=Dict)
async def record_export_download(
    export_id: str,
    current_user: dict = Depends(get_current_user),
    export_service: DataExportService = Depends(get_export_service),
):
    """Record that an export was downloaded (affects retention calculation)."""
    try:
        # Check if user owns the export or is admin
        export_details = await export_service.get_export_by_id(export_id)
        if not export_details:
            raise HTTPException(status_code=404, detail="Export not found")

        if (
            not current_user.get("is_admin", False)
            and export_details.get("user_id") != current_user["id"]
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        success = await export_service.record_export_download(export_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to record download")

        return {"success": True, "message": "Download recorded"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording export download: {e}")
        raise HTTPException(status_code=500, detail="Failed to record download")


@router.get("/config/export", response_model=Dict)
async def export_retention_config(
    category: Optional[str] = Query(None, description="Optional category filter"),
    current_user: dict = Depends(require_admin),
    retention_config: ExportRetentionConfig = Depends(get_retention_config),
):
    """Export retention configuration (admin only)."""
    try:
        config_data = await retention_config.export_config(category)
        return {"success": True, "data": config_data}

    except Exception as e:
        logger.error(f"Error exporting retention config: {e}")
        raise HTTPException(status_code=500, detail="Failed to export configuration")


@router.post("/config/import", response_model=Dict)
async def import_retention_config(
    config_data: Dict,
    current_user: dict = Depends(require_admin),
    retention_config: ExportRetentionConfig = Depends(get_retention_config),
):
    """Import retention configuration (admin only)."""
    try:
        results = await retention_config.import_config(config_data, current_user["id"])

        if results["errors"] > 0:
            return {
                "success": False,
                "data": results,
                "message": "Import completed with errors",
            }

        return {
            "success": True,
            "data": results,
            "message": "Configuration imported successfully",
        }

    except Exception as e:
        logger.error(f"Error importing retention config: {e}")
        raise HTTPException(status_code=500, detail="Failed to import configuration")
