"""Data Export Service for device data.

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
import csv
import io
import json
import sqlite3
import tempfile
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Export request model."""
    
    devices: List[str] = Field(..., description="Device IDs to export")
    date_range: Dict[str, str] = Field(..., description="Start and end dates")
    format: str = Field(..., description="Export format (csv, excel, json, etc.)")
    aggregation: str = Field(default="raw", description="Data aggregation level")
    metrics: List[str] = Field(default=["power", "energy"], description="Metrics to include")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")


class ExportResult(BaseModel):
    """Export result model."""
    
    export_id: str = Field(..., description="Unique export identifier")
    filename: str = Field(..., description="Generated filename")
    file_path: str = Field(..., description="Full file path")
    file_size: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Export format")
    created_at: datetime = Field(..., description="Export creation time")
    devices_count: int = Field(..., description="Number of devices exported")
    records_count: int = Field(..., description="Number of data records")
    status: str = Field(default="completed", description="Export status")


class BaseExportFormatter(ABC):
    """Base class for export formatters."""
    
    def __init__(self):
        self.format_name = ""
        self.file_extension = ""
        self.mime_type = ""
    
    @abstractmethod
    async def format_data(self, data: List[Dict], metadata: Dict, options: Dict) -> bytes:
        """Format data according to the specific format."""
        pass
    
    def get_filename(self, base_name: str, timestamp: datetime) -> str:
        """Generate filename with proper extension."""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{base_name}_{timestamp_str}.{self.file_extension}"


class CSVFormatter(BaseExportFormatter):
    """CSV export formatter."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "CSV"
        self.file_extension = "csv"
        self.mime_type = "text/csv"
    
    async def format_data(self, data: List[Dict], metadata: Dict, options: Dict) -> bytes:
        """Format data as CSV."""
        if not data:
            return b""
        
        output = io.StringIO()
        
        # Add metadata header if requested
        if options.get("include_metadata", True):
            output.write(f"# Export created: {metadata.get('created_at')}\n")
            output.write(f"# Devices: {', '.join(metadata.get('devices', []))}\n")
            output.write(f"# Date range: {metadata.get('date_range', {}).get('start')} to {metadata.get('date_range', {}).get('end')}\n")
            output.write(f"# Records: {len(data)}\n")
            output.write("\n")
        
        # Write CSV data
        if data:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(
                output, 
                fieldnames=fieldnames,
                delimiter=options.get("delimiter", ","),
                quoting=csv.QUOTE_MINIMAL
            )
            writer.writeheader()
            writer.writerows(data)
        
        return output.getvalue().encode('utf-8')


class ExcelFormatter(BaseExportFormatter):
    """Excel export formatter."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "Excel"
        self.file_extension = "xlsx"
        self.mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    async def format_data(self, data: List[Dict], metadata: Dict, options: Dict) -> bytes:
        """Format data as Excel file."""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Create main data sheet
            if data:
                df = pd.DataFrame(data)
                
                # Convert timestamp columns to datetime
                timestamp_cols = [col for col in df.columns if 'timestamp' in col.lower()]
                for col in timestamp_cols:
                    df[col] = pd.to_datetime(df[col])
                
                df.to_excel(writer, sheet_name='Device Data', index=False)
                
                # Format the worksheet
                worksheet = writer.sheets['Device Data']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Create summary sheet
            summary_data = {
                'Export Information': [
                    ['Export ID', metadata.get('export_id', '')],
                    ['Created At', metadata.get('created_at', '')],
                    ['Format', metadata.get('format', '')],
                    ['Records Count', len(data)],
                    ['Devices Count', len(metadata.get('devices', []))],
                    ['Date Range Start', metadata.get('date_range', {}).get('start', '')],
                    ['Date Range End', metadata.get('date_range', {}).get('end', '')],
                    ['Aggregation', metadata.get('aggregation', '')],
                    ['Metrics', ', '.join(metadata.get('metrics', []))],
                ]
            }
            
            summary_df = pd.DataFrame(summary_data['Export Information'], columns=['Property', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Create device list sheet
            if metadata.get('devices'):
                devices_df = pd.DataFrame({'Device ID': metadata['devices']})
                devices_df.to_excel(writer, sheet_name='Devices', index=False)
        
        return output.getvalue()


class JSONFormatter(BaseExportFormatter):
    """JSON export formatter."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "JSON"
        self.file_extension = "json"
        self.mime_type = "application/json"
    
    async def format_data(self, data: List[Dict], metadata: Dict, options: Dict) -> bytes:
        """Format data as JSON."""
        export_data = {
            "metadata": metadata,
            "data": data
        }
        
        # Pretty print if requested
        indent = 2 if options.get("pretty_print", True) else None
        
        return json.dumps(export_data, indent=indent, default=str, ensure_ascii=False).encode('utf-8')


class SQLiteFormatter(BaseExportFormatter):
    """SQLite database export formatter."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "SQLite"
        self.file_extension = "db"
        self.mime_type = "application/x-sqlite3"
    
    async def format_data(self, data: List[Dict], metadata: Dict, options: Dict) -> bytes:
        """Format data as SQLite database."""
        # Create temporary file for SQLite database
        with tempfile.NamedTemporaryFile() as temp_file:
            conn = sqlite3.connect(temp_file.name)
            
            # Create metadata table
            conn.execute("""
                CREATE TABLE export_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Insert metadata
            for key, value in metadata.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                conn.execute("INSERT INTO export_metadata (key, value) VALUES (?, ?)", (key, str(value)))
            
            # Create data table if we have data
            if data:
                df = pd.DataFrame(data)
                df.to_sql('device_data', conn, if_exists='replace', index=False)
            
            conn.commit()
            conn.close()
            
            # Read the database file
            with open(temp_file.name, 'rb') as f:
                return f.read()


class DataExportService:
    """Main data export service."""
    
    def __init__(self, db_path: str = "kasa_monitor.db", exports_dir: str = "exports"):
        self.db_path = db_path
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(exist_ok=True)
        
        # Initialize formatters
        self.formatters = {
            'csv': CSVFormatter(),
            'excel': ExcelFormatter(),
            'json': JSONFormatter(),
            'sqlite': SQLiteFormatter(),
        }
        
        # Initialize exports tracking database
        self._init_exports_db()
    
    def _init_exports_db(self):
        """Initialize exports tracking database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_exports (
                export_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                format TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                devices_count INTEGER NOT NULL,
                records_count INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                request_data TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    async def export_data(self, request: ExportRequest) -> ExportResult:
        """Export device data according to the request."""
        export_id = str(uuid4())
        created_at = datetime.now()
        
        # Validate request
        if not request.devices:
            raise ValueError("At least one device must be selected")
        
        if request.format not in self.formatters:
            raise ValueError(f"Unsupported format: {request.format}")
        
        # Query data
        data = await self._query_device_data(request)
        
        # Prepare metadata
        metadata = {
            "export_id": export_id,
            "created_at": created_at.isoformat(),
            "format": request.format,
            "devices": request.devices,
            "date_range": request.date_range,
            "aggregation": request.aggregation,
            "metrics": request.metrics,
            "options": request.options
        }
        
        # Format data
        formatter = self.formatters[request.format]
        formatted_data = await formatter.format_data(data, metadata, request.options)
        
        # Generate filename and save file
        base_name = f"device_export_{len(request.devices)}devices"
        filename = formatter.get_filename(base_name, created_at)
        file_path = self.exports_dir / filename
        
        # Handle compression if requested
        if request.options.get("compression") == "zip":
            zip_path = file_path.with_suffix(f".{file_path.suffix}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(filename, formatted_data)
            file_path = zip_path
            filename = zip_path.name
            
            with open(zip_path, 'rb') as f:
                file_size = len(f.read())
        else:
            with open(file_path, 'wb') as f:
                f.write(formatted_data)
            file_size = len(formatted_data)
        
        # Create export result
        result = ExportResult(
            export_id=export_id,
            filename=filename,
            file_path=str(file_path),
            file_size=file_size,
            format=request.format,
            created_at=created_at,
            devices_count=len(request.devices),
            records_count=len(data),
            status="completed"
        )
        
        # Save export record
        await self._save_export_record(result, request)
        
        return result
    
    async def _query_device_data(self, request: ExportRequest) -> List[Dict]:
        """Query device data from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Build query based on aggregation level
            if request.aggregation == "raw":
                query = """
                    SELECT device_ip as device_id, timestamp, current_power_w as power, 
                           today_energy_kwh as energy, voltage, current
                    FROM device_readings 
                    WHERE device_ip IN ({}) 
                    AND timestamp BETWEEN ? AND ?
                    ORDER BY device_ip, timestamp
                """.format(','.join('?' * len(request.devices)))
            
            elif request.aggregation == "hourly":
                query = """
                    SELECT 
                        device_ip as device_id,
                        datetime(timestamp, 'start of hour') as timestamp,
                        AVG(current_power_w) as power,
                        MAX(today_energy_kwh) - MIN(today_energy_kwh) as energy,
                        AVG(voltage) as voltage,
                        AVG(current) as current
                    FROM device_readings 
                    WHERE device_ip IN ({}) 
                    AND timestamp BETWEEN ? AND ?
                    GROUP BY device_ip, datetime(timestamp, 'start of hour')
                    ORDER BY device_ip, timestamp
                """.format(','.join('?' * len(request.devices)))
            
            elif request.aggregation == "daily":
                query = """
                    SELECT 
                        device_ip as device_id,
                        date(timestamp) as timestamp,
                        AVG(current_power_w) as power,
                        MAX(today_energy_kwh) - MIN(today_energy_kwh) as energy,
                        AVG(voltage) as voltage,
                        AVG(current) as current
                    FROM device_readings 
                    WHERE device_ip IN ({}) 
                    AND timestamp BETWEEN ? AND ?
                    GROUP BY device_ip, date(timestamp)
                    ORDER BY device_ip, timestamp
                """.format(','.join('?' * len(request.devices)))
            
            else:
                raise ValueError(f"Unsupported aggregation: {request.aggregation}")
            
            # Execute query
            params = request.devices + [request.date_range["start"], request.date_range["end"]]
            cursor = conn.execute(query, params)
            
            # Convert to list of dicts, filtering by requested metrics
            data = []
            for row in cursor.fetchall():
                record = dict(row)
                
                # Filter metrics if specified
                if request.metrics and request.metrics != ["all"]:
                    filtered_record = {
                        "device_id": record["device_id"],
                        "timestamp": record["timestamp"]
                    }
                    for metric in request.metrics:
                        if metric in record:
                            filtered_record[metric] = record[metric]
                    record = filtered_record
                
                data.append(record)
            
            return data
            
        finally:
            conn.close()
    
    async def _save_export_record(self, result: ExportResult, request: ExportRequest):
        """Save export record to database."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute("""
                INSERT INTO data_exports (
                    export_id, filename, file_path, file_size, format,
                    created_at, devices_count, records_count, status, request_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.export_id,
                result.filename,
                result.file_path,
                result.file_size,
                result.format,
                result.created_at,
                result.devices_count,
                result.records_count,
                result.status,
                request.json()
            ))
            conn.commit()
            
        finally:
            conn.close()
    
    async def get_export_history(self, limit: int = 50) -> List[Dict]:
        """Get export history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT export_id, filename, file_size, format, created_at,
                       devices_count, records_count, status
                FROM data_exports
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    async def get_export_by_id(self, export_id: str) -> Optional[Dict]:
        """Get export details by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT * FROM data_exports WHERE export_id = ?
            """, (export_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        finally:
            conn.close()
    
    def get_available_formats(self) -> Dict[str, Dict[str, str]]:
        """Get available export formats and their details."""
        return {
            name: {
                "name": formatter.format_name,
                "extension": formatter.file_extension,
                "mime_type": formatter.mime_type
            }
            for name, formatter in self.formatters.items()
        }