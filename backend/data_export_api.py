"""Data Export API endpoints.

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

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from data_export_service import DataExportService, ExportRequest


class ExportRequestAPI(BaseModel):
    """API model for export requests."""
    
    devices: List[str]
    date_range: Dict[str, str]
    format: str = "csv"
    aggregation: str = "raw"
    metrics: List[str] = ["power", "energy"]
    options: Dict = {}


class DataExportAPIRouter:
    """Data Export API router for FastAPI."""
    
    def __init__(self, app: FastAPI, db_path: str = "kasa_monitor.db"):
        self.app = app
        self.db_path = db_path
        self.export_service = DataExportService(db_path)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/api/exports/formats")
        async def get_export_formats():
            """Get available export formats."""
            return self.export_service.get_available_formats()
        
        @self.app.get("/api/exports/devices")
        async def get_available_devices():
            """Get list of devices that have data for export."""
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            try:
                # Get devices that have data
                cursor = conn.execute("""
                    SELECT DISTINCT device_ip as device_id, 
                           COUNT(*) as record_count,
                           MIN(timestamp) as first_record,
                           MAX(timestamp) as last_record
                    FROM device_readings 
                    GROUP BY device_ip
                    ORDER BY device_ip
                """)
                
                devices = []
                for row in cursor.fetchall():
                    # Get device name from device_info table if available
                    device_cursor = conn.execute(
                        "SELECT alias FROM device_info WHERE device_ip = ?", 
                        (row["device_id"],)
                    )
                    device_row = device_cursor.fetchone()
                    device_name = device_row["alias"] if device_row else row["device_id"]
                    
                    devices.append({
                        "id": row["device_id"],
                        "name": device_name,
                        "record_count": row["record_count"],
                        "first_record": row["first_record"],
                        "last_record": row["last_record"]
                    })
                
                return {"devices": devices}
                
            finally:
                conn.close()
        
        @self.app.get("/api/exports/metrics")
        async def get_available_metrics():
            """Get available metrics for export."""
            return {
                "metrics": [
                    {
                        "id": "power",
                        "name": "Power (W)",
                        "description": "Current power consumption"
                    },
                    {
                        "id": "energy", 
                        "name": "Energy (kWh)",
                        "description": "Cumulative energy consumption"
                    },
                    {
                        "id": "voltage",
                        "name": "Voltage (V)", 
                        "description": "Current voltage"
                    },
                    {
                        "id": "current",
                        "name": "Current (A)",
                        "description": "Current amperage"
                    },
                    {
                        "id": "is_on",
                        "name": "Device Status",
                        "description": "Whether the device is on or off"
                    },
                    {
                        "id": "rssi",
                        "name": "Signal Strength (RSSI)",
                        "description": "WiFi signal strength"
                    }
                ]
            }
        
        @self.app.post("/api/exports/create")
        async def create_export(request: ExportRequestAPI, background_tasks: BackgroundTasks):
            """Create a new data export."""
            try:
                # Convert API request to service request
                export_request = ExportRequest(
                    devices=request.devices,
                    date_range=request.date_range,
                    format=request.format,
                    aggregation=request.aggregation,
                    metrics=request.metrics,
                    options=request.options
                )
                
                # For small exports, process immediately
                # For large exports, we might want to process in background
                if self._is_large_export(export_request):
                    # Add to background tasks for large exports
                    background_tasks.add_task(self._process_large_export, export_request)
                    return {
                        "message": "Large export started in background",
                        "status": "processing"
                    }
                else:
                    # Process immediately for small exports
                    result = await self.export_service.export_data(export_request)
                    return {
                        "export_id": result.export_id,
                        "filename": result.filename,
                        "file_size": result.file_size,
                        "records_count": result.records_count,
                        "status": "completed",
                        "download_url": f"/api/exports/download/{result.export_id}"
                    }
                    
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
        
        @self.app.get("/api/exports/history")
        async def get_export_history(limit: int = 50):
            """Get export history."""
            try:
                history = await self.export_service.get_export_history(limit)
                return {"exports": history}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get export history: {str(e)}")
        
        @self.app.get("/api/exports/{export_id}")
        async def get_export_details(export_id: str):
            """Get export details by ID."""
            try:
                export = await self.export_service.get_export_by_id(export_id)
                if not export:
                    raise HTTPException(status_code=404, detail="Export not found")
                return export
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get export details: {str(e)}")
        
        @self.app.get("/api/exports/download/{export_id}")
        async def download_export(export_id: str):
            """Download export file by ID."""
            try:
                export = await self.export_service.get_export_by_id(export_id)
                if not export:
                    raise HTTPException(status_code=404, detail="Export not found")
                
                file_path = Path(export["file_path"])
                if not file_path.exists():
                    raise HTTPException(status_code=404, detail="Export file not found")
                
                # Determine media type based on format
                formatter = self.export_service.formatters.get(export["format"])
                media_type = formatter.mime_type if formatter else "application/octet-stream"
                
                return FileResponse(
                    path=str(file_path),
                    filename=export["filename"],
                    media_type=media_type
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
        
        @self.app.delete("/api/exports/{export_id}")
        async def delete_export(export_id: str):
            """Delete an export and its file."""
            try:
                export = await self.export_service.get_export_by_id(export_id)
                if not export:
                    raise HTTPException(status_code=404, detail="Export not found")
                
                # Delete file if it exists
                file_path = Path(export["file_path"])
                if file_path.exists():
                    file_path.unlink()
                
                # Delete database record
                conn = sqlite3.connect(self.db_path)
                try:
                    conn.execute("DELETE FROM data_exports WHERE export_id = ?", (export_id,))
                    conn.commit()
                finally:
                    conn.close()
                
                return {"message": "Export deleted successfully"}
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
        
        @self.app.get("/api/exports/preview")
        async def preview_export_data(
            devices: str,  # Comma-separated device IDs
            start_date: str,
            end_date: str,
            aggregation: str = "raw",
            limit: int = 100
        ):
            """Preview export data before creating full export."""
            try:
                device_list = devices.split(",")
                
                # Create a preview request (limit data)
                preview_request = ExportRequest(
                    devices=device_list,
                    date_range={"start": start_date, "end": end_date},
                    format="json",  # Use JSON for preview
                    aggregation=aggregation,
                    metrics=["power", "energy"],  # Basic metrics for preview
                    options={}
                )
                
                # Get limited data for preview
                data = await self.export_service._query_device_data(preview_request)
                
                # Limit results for preview
                preview_data = data[:limit] if len(data) > limit else data
                
                return {
                    "preview_data": preview_data,
                    "total_records": len(data),
                    "preview_records": len(preview_data),
                    "devices_count": len(device_list),
                    "date_range": {"start": start_date, "end": end_date}
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
        
        @self.app.get("/api/exports/stats")
        async def get_export_stats():
            """Get export statistics."""
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            try:
                # Get export statistics
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_exports,
                        SUM(file_size) as total_size,
                        SUM(records_count) as total_records,
                        AVG(file_size) as avg_file_size,
                        format,
                        COUNT(*) as format_count
                    FROM data_exports
                    GROUP BY format
                """)
                
                format_stats = []
                total_exports = 0
                total_size = 0
                total_records = 0
                
                for row in cursor.fetchall():
                    format_stats.append(dict(row))
                    total_exports += row["format_count"]
                    total_size += row["total_size"] or 0
                    total_records += row["total_records"] or 0
                
                # Get recent export activity (last 30 days)
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor = conn.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM data_exports
                    WHERE created_at >= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """, (thirty_days_ago,))
                
                daily_activity = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "total_exports": total_exports,
                    "total_size_bytes": total_size,
                    "total_records": total_records,
                    "format_breakdown": format_stats,
                    "daily_activity": daily_activity
                }
                
            finally:
                conn.close()
    
    def _is_large_export(self, request: ExportRequest) -> bool:
        """Determine if an export is considered large and should be processed in background."""
        # Simple heuristic: more than 3 devices or more than 7 days of data
        device_count = len(request.devices)
        
        try:
            start_date = datetime.fromisoformat(request.date_range["start"].replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(request.date_range["end"].replace('Z', '+00:00'))
            date_range_days = (end_date - start_date).days
            
            return device_count > 3 or date_range_days > 7
        except:
            return False
    
    async def _process_large_export(self, request: ExportRequest):
        """Process large export in background."""
        try:
            result = await self.export_service.export_data(request)
            # Could add notification or webhook here when complete
        except Exception as e:
            # Log error and update export status
            print(f"Background export failed: {e}")