"""
Data Management API endpoints for Kasa Monitor
Handles export, aggregation, and bulk operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
import io

from auth import get_current_user, require_permission
from models import User, Permission
from data_export import DataExporter, BulkOperations
from data_aggregation import DataAggregator, AggregationPeriod
from cache_manager import CacheManager, ResponseCache

router = APIRouter(prefix="/api/data", tags=["data-management"])

# Initialize services (these should be injected via dependency injection in production)
data_exporter = None
bulk_operations = None
data_aggregator = None
cache_manager = None
response_cache = None


def get_data_exporter():
    """Get data exporter instance"""
    global data_exporter
    if not data_exporter:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        data_exporter = DataExporter(db_manager)
    return data_exporter


def get_bulk_operations():
    """Get bulk operations instance"""
    global bulk_operations
    if not bulk_operations:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        bulk_operations = BulkOperations(db_manager)
    return bulk_operations


def get_data_aggregator():
    """Get data aggregator instance"""
    global data_aggregator
    if not data_aggregator:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        data_aggregator = DataAggregator(db_manager)
    return data_aggregator


def get_cache_manager():
    """Get cache manager instance"""
    global cache_manager
    if not cache_manager:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        cache_manager = CacheManager(redis_url=redis_url)
        global response_cache
        response_cache = ResponseCache(cache_manager)
    return cache_manager


# Request/Response Models


class ExportRequest(BaseModel):
    format: str = "csv"  # csv, excel, pdf
    include_energy: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    device_ip: Optional[str] = None


class BulkImportResponse(BaseModel):
    success: bool
    imported: int
    failed: int
    failures: List[Dict[str, Any]] = []


class BulkUpdateRequest(BaseModel):
    updates: List[Dict[str, Any]]


class BulkDeleteRequest(BaseModel):
    device_ips: List[str]


class AggregationRequest(BaseModel):
    period: str = "day"  # minute, hour, day, week, month, year
    device_ip: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class StatisticsResponse(BaseModel):
    device_ip: str
    statistics: Dict[str, Any]
    period: str
    start_date: datetime
    end_date: datetime


class TrendAnalysisResponse(BaseModel):
    device_ip: str
    trend: str
    slope: float
    percent_change: float
    data_points: int


# Export Endpoints


@router.post("/export/devices")
async def export_devices(
    request: ExportRequest, user: User = Depends(get_current_user)
):
    """Export device data in various formats"""
    exporter = get_data_exporter()

    try:
        if request.format == "csv":
            content = await exporter.export_devices_csv(user_id=user.id)
            return StreamingResponse(
                io.BytesIO(content),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=devices.csv"},
            )

        elif request.format == "excel":
            content = await exporter.export_devices_excel(
                include_energy=request.include_energy
            )
            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=devices.xlsx"},
            )

        elif request.format == "pdf":
            content = await exporter.generate_pdf_report(
                report_type="devices",
                start_date=request.start_date,
                end_date=request.end_date,
            )
            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=devices_report.pdf"
                },
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/energy")
async def export_energy_data(
    request: ExportRequest, user: User = Depends(get_current_user)
):
    """Export energy consumption data"""
    exporter = get_data_exporter()

    try:
        if request.format == "csv":
            content = await exporter.export_energy_data_csv(
                device_ip=request.device_ip,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            return StreamingResponse(
                io.BytesIO(content),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=energy_data.csv"},
            )

        elif request.format == "pdf":
            content = await exporter.generate_pdf_report(
                report_type="energy",
                start_date=request.start_date,
                end_date=request.end_date,
            )
            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=energy_report.pdf"
                },
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/report/{report_type}")
async def generate_report(
    report_type: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: User = Depends(get_current_user),
):
    """Generate comprehensive PDF report"""
    if report_type not in ["daily", "weekly", "monthly", "annual"]:
        raise HTTPException(status_code=400, detail="Invalid report type")

    exporter = get_data_exporter()

    try:
        content = await exporter.generate_pdf_report(
            report_type=report_type, start_date=start_date, end_date=end_date
        )

        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={report_type}_report.pdf"
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Bulk Operations Endpoints


@router.post("/bulk/import", response_model=BulkImportResponse)
async def bulk_import_devices(
    file: UploadFile = File(...),
    user: User = Depends(require_permission(Permission.DEVICES_EDIT)),
):
    """Bulk import devices from CSV file"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    bulk_ops = get_bulk_operations()

    try:
        content = await file.read()
        result = await bulk_ops.bulk_import_devices(content)
        return BulkImportResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/update")
async def bulk_update_devices(
    request: BulkUpdateRequest,
    user: User = Depends(require_permission(Permission.DEVICES_EDIT)),
):
    """Bulk update device configurations"""
    bulk_ops = get_bulk_operations()

    try:
        result = await bulk_ops.bulk_update_devices(request.updates)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/delete")
async def bulk_delete_devices(
    request: BulkDeleteRequest,
    user: User = Depends(require_permission(Permission.DEVICES_REMOVE)),
):
    """Bulk delete devices"""
    bulk_ops = get_bulk_operations()

    try:
        result = await bulk_ops.bulk_delete_devices(request.device_ips)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Aggregation Endpoints


@router.get("/aggregation")
async def get_aggregated_data(
    period: str = Query("day"),
    device_ip: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: User = Depends(get_current_user),
):
    """Get aggregated data for specified period"""
    aggregator = get_data_aggregator()
    cache = get_cache_manager()

    # Check cache
    cache_key = f"aggregation:{period}:{device_ip}:{start_date}:{end_date}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        period_enum = AggregationPeriod(period.lower())
        data = await aggregator.get_aggregated_data(
            device_ip=device_ip,
            period=period_enum,
            start_date=start_date,
            end_date=end_date,
        )

        # Cache result
        await cache.set(cache_key, data, ttl=300)

        return data

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid aggregation period")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{device_ip}", response_model=StatisticsResponse)
async def get_device_statistics(
    device_ip: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: User = Depends(get_current_user),
):
    """Get statistical analysis for a device"""
    aggregator = get_data_aggregator()

    try:
        stats = await aggregator.calculate_statistics(
            device_ip=device_ip, start_date=start_date, end_date=end_date
        )

        return StatisticsResponse(
            device_ip=device_ip,
            statistics=stats,
            period="custom",
            start_date=start_date or datetime.now() - timedelta(days=30),
            end_date=end_date or datetime.now(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{device_ip}", response_model=TrendAnalysisResponse)
async def get_trend_analysis(
    device_ip: str,
    period: str = Query("day"),
    lookback: int = Query(30),
    user: User = Depends(get_current_user),
):
    """Get trend analysis for a device"""
    aggregator = get_data_aggregator()

    try:
        period_enum = AggregationPeriod(period.lower())
        analysis = await aggregator.get_trend_analysis(
            device_ip=device_ip, period=period_enum, lookback_periods=lookback
        )

        return TrendAnalysisResponse(device_ip=device_ip, **analysis)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Aggregation Management


@router.post("/aggregation/run")
async def trigger_aggregation(
    period: str = Query("hour"),
    force_date: Optional[datetime] = Query(None),
    user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Manually trigger data aggregation"""
    aggregator = get_data_aggregator()

    try:
        if period == "hour":
            await aggregator.aggregate_hourly_data(force_date)
        elif period == "day":
            await aggregator.aggregate_daily_data(force_date)
        elif period == "month" and force_date:
            await aggregator.aggregate_monthly_data(force_date.year, force_date.month)
        else:
            raise HTTPException(status_code=400, detail="Invalid aggregation period")

        return {"status": "success", "message": f"{period}ly aggregation completed"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aggregation/cleanup")
async def cleanup_old_data(
    retention_days: int = Query(7),
    user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Clean up old detailed data"""
    aggregator = get_data_aggregator()

    try:
        await aggregator.cleanup_old_data(retention_days)
        return {
            "status": "success",
            "message": f"Cleaned up data older than {retention_days} days",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cache Management


@router.get("/cache/stats")
async def get_cache_statistics(
    user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get cache statistics"""
    cache = get_cache_manager()
    return cache.get_stats()


@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(None),
    user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Clear cache entries"""
    cache = get_cache_manager()
    count = await cache.clear(pattern)
    return {"status": "success", "message": f"Cleared {count} cache entries"}


# Service Management


@router.post("/services/start")
async def start_data_services(
    user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Start data management services"""
    aggregator = get_data_aggregator()

    try:
        await aggregator.start()
        return {"status": "success", "message": "Data services started"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/services/stop")
async def stop_data_services(
    user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Stop data management services"""
    aggregator = get_data_aggregator()

    try:
        await aggregator.stop()
        return {"status": "success", "message": "Data services stopped"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
