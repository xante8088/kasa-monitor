"""
Data Export Module for Kasa Monitor
Handles CSV, Excel, and PDF export functionality
"""

import base64
import csv
import io
import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)


class DataExporter:
    """Handles data export in various formats"""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom PDF styles"""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#2563eb"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomHeading",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#1f2937"),
                spaceAfter=12,
            )
        )

    async def export_devices_csv(self, user_id: Optional[int] = None) -> bytes:
        """Export devices data to CSV format"""
        devices = await self.db_manager.get_all_devices()

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "device_ip",
                "device_name",
                "device_alias",
                "device_model",
                "device_type",
                "mac_address",
                "location",
                "group_name",
                "is_active",
                "is_monitored",
                "discovered_at",
                "last_seen",
            ],
        )

        writer.writeheader()
        for device in devices:
            writer.writerow(
                {
                    "device_ip": device.get("device_ip"),
                    "device_name": device.get("device_name"),
                    "device_alias": device.get("device_alias"),
                    "device_model": device.get("device_model"),
                    "device_type": device.get("device_type"),
                    "mac_address": device.get("mac_address"),
                    "location": device.get("location"),
                    "group_name": device.get("group_name"),
                    "is_active": device.get("is_active"),
                    "is_monitored": device.get("is_monitored"),
                    "discovered_at": device.get("discovered_at"),
                    "last_seen": device.get("last_seen"),
                }
            )

        return output.getvalue().encode("utf-8")

    async def export_energy_data_csv(
        self,
        device_ip: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> bytes:
        """Export energy consumption data to CSV"""

        # Default to last 30 days if no date range specified
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get readings from database
        query = """
            SELECT 
                device_ip,
                timestamp,
                power_w,
                energy_kwh,
                voltage_v,
                current_a,
                total_kwh
            FROM readings
            WHERE timestamp BETWEEN ? AND ?
        """
        params = [start_date.isoformat(), end_date.isoformat()]

        if device_ip:
            query += " AND device_ip = ?"
            params.append(device_ip)

        query += " ORDER BY timestamp DESC"

        readings = await self.db_manager.execute_query(query, params)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Device IP",
                "Timestamp",
                "Power (W)",
                "Energy (kWh)",
                "Voltage (V)",
                "Current (A)",
                "Total (kWh)",
            ]
        )

        for reading in readings:
            writer.writerow(reading)

        return output.getvalue().encode("utf-8")

    async def export_devices_excel(self, include_energy: bool = False) -> bytes:
        """Export devices and optionally energy data to Excel"""

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Devices sheet
            devices = await self.db_manager.get_all_devices()
            df_devices = pd.DataFrame(devices)
            df_devices.to_excel(writer, sheet_name="Devices", index=False)

            if include_energy:
                # Energy summary sheet
                energy_summary = await self._get_energy_summary()
                df_energy = pd.DataFrame(energy_summary)
                df_energy.to_excel(writer, sheet_name="Energy Summary", index=False)

                # Daily consumption sheet
                daily_data = await self._get_daily_consumption()
                df_daily = pd.DataFrame(daily_data)
                df_daily.to_excel(writer, sheet_name="Daily Consumption", index=False)

        output.seek(0)
        return output.read()

    async def generate_pdf_report(
        self,
        report_type: str = "monthly",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> bytes:
        """Generate comprehensive PDF report"""

        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        story = []

        # Title
        title = f"Kasa Monitor - {report_type.capitalize()} Report"
        story.append(Paragraph(title, self.styles["CustomTitle"]))
        story.append(Spacer(1, 12))

        # Report period
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            if report_type == "daily":
                start_date = end_date - timedelta(days=1)
            elif report_type == "weekly":
                start_date = end_date - timedelta(days=7)
            else:  # monthly
                start_date = end_date - timedelta(days=30)

        period_text = f"Report Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        story.append(Paragraph(period_text, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles["CustomHeading"]))
        summary_data = await self._get_report_summary(start_date, end_date)
        summary_table = Table(
            [
                ["Metric", "Value"],
                ["Total Devices", str(summary_data["total_devices"])],
                ["Active Devices", str(summary_data["active_devices"])],
                ["Total Energy (kWh)", f"{summary_data['total_energy']:.2f}"],
                ["Total Cost", f"${summary_data['total_cost']:.2f}"],
                ["Average Power (W)", f"{summary_data['avg_power']:.2f}"],
                ["Peak Power (W)", f"{summary_data['peak_power']:.2f}"],
            ]
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Device Details
        story.append(Paragraph("Device Performance", self.styles["CustomHeading"]))
        devices_data = await self._get_device_performance(start_date, end_date)

        device_table_data = [
            ["Device", "Energy (kWh)", "Cost ($)", "Avg Power (W)", "Uptime (%)"]
        ]
        for device in devices_data:
            device_table_data.append(
                [
                    device["name"],
                    f"{device['energy']:.2f}",
                    f"{device['cost']:.2f}",
                    f"{device['avg_power']:.2f}",
                    f"{device['uptime']:.1f}",
                ]
            )

        device_table = Table(device_table_data)
        device_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(device_table)
        story.append(PageBreak())

        # Energy Consumption Chart
        story.append(
            Paragraph("Energy Consumption Trends", self.styles["CustomHeading"])
        )
        chart_img = await self._generate_consumption_chart(start_date, end_date)
        if chart_img:
            story.append(chart_img)

        # Recommendations
        story.append(Paragraph("Recommendations", self.styles["CustomHeading"]))
        recommendations = await self._generate_recommendations(
            summary_data, devices_data
        )
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", self.styles["Normal"]))

        # Build PDF
        doc.build(story)
        output.seek(0)
        return output.read()

    async def _get_energy_summary(self) -> List[Dict]:
        """Get energy summary for all devices"""
        query = """
            SELECT 
                device_ip,
                COUNT(*) as reading_count,
                SUM(energy_kwh) as total_energy,
                AVG(power_w) as avg_power,
                MAX(power_w) as max_power,
                MIN(power_w) as min_power
            FROM readings
            WHERE timestamp > datetime('now', '-30 days')
            GROUP BY device_ip
        """
        results = await self.db_manager.execute_query(query)
        return [
            dict(
                zip(
                    [
                        "device_ip",
                        "reading_count",
                        "total_energy",
                        "avg_power",
                        "max_power",
                        "min_power",
                    ],
                    row,
                )
            )
            for row in results
        ]

    async def _get_daily_consumption(self) -> List[Dict]:
        """Get daily consumption data"""
        query = """
            SELECT 
                DATE(timestamp) as date,
                device_ip,
                SUM(energy_kwh) as daily_energy,
                AVG(power_w) as avg_power,
                MAX(power_w) as peak_power
            FROM readings
            WHERE timestamp > datetime('now', '-30 days')
            GROUP BY DATE(timestamp), device_ip
            ORDER BY date DESC
        """
        results = await self.db_manager.execute_query(query)
        return [
            dict(
                zip(
                    ["date", "device_ip", "daily_energy", "avg_power", "peak_power"],
                    row,
                )
            )
            for row in results
        ]

    async def _get_report_summary(
        self, start_date: datetime, end_date: datetime
    ) -> Dict:
        """Get summary data for report"""
        # This is a simplified version - expand based on actual database schema
        devices = await self.db_manager.get_all_devices()
        total_devices = len(devices)
        active_devices = len([d for d in devices if d.get("is_active")])

        # Get energy data
        query = """
            SELECT 
                SUM(energy_kwh) as total_energy,
                AVG(power_w) as avg_power,
                MAX(power_w) as peak_power
            FROM readings
            WHERE timestamp BETWEEN ? AND ?
        """
        result = await self.db_manager.execute_query(
            query, [start_date.isoformat(), end_date.isoformat()]
        )

        if result and result[0]:
            total_energy = result[0][0] or 0
            avg_power = result[0][1] or 0
            peak_power = result[0][2] or 0
        else:
            total_energy = avg_power = peak_power = 0

        # Calculate cost (assuming $0.12/kWh)
        total_cost = total_energy * 0.12

        return {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "total_energy": total_energy,
            "total_cost": total_cost,
            "avg_power": avg_power,
            "peak_power": peak_power,
        }

    async def _get_device_performance(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get performance metrics for each device"""
        query = """
            SELECT 
                d.device_name,
                d.device_ip,
                SUM(r.energy_kwh) as total_energy,
                AVG(r.power_w) as avg_power,
                COUNT(CASE WHEN r.power_w > 0 THEN 1 END) * 100.0 / COUNT(*) as uptime
            FROM devices d
            LEFT JOIN readings r ON d.device_ip = r.device_ip
            WHERE r.timestamp BETWEEN ? AND ?
            GROUP BY d.device_ip, d.device_name
        """

        results = await self.db_manager.execute_query(
            query, [start_date.isoformat(), end_date.isoformat()]
        )

        performance_data = []
        for row in results:
            performance_data.append(
                {
                    "name": row[0] or row[1],
                    "device_ip": row[1],
                    "energy": row[2] or 0,
                    "cost": (row[2] or 0) * 0.12,
                    "avg_power": row[3] or 0,
                    "uptime": row[4] or 0,
                }
            )

        return performance_data

    async def _generate_consumption_chart(
        self, start_date: datetime, end_date: datetime
    ):
        """Generate consumption chart for PDF report"""
        # Get daily consumption data
        query = """
            SELECT 
                DATE(timestamp) as date,
                SUM(energy_kwh) as daily_energy
            FROM readings
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """

        results = await self.db_manager.execute_query(
            query, [start_date.isoformat(), end_date.isoformat()]
        )

        if not results:
            return None

        dates = [datetime.strptime(row[0], "%Y-%m-%d") for row in results]
        consumption = [row[1] for row in results]

        # Create chart
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(dates, consumption, marker="o", linestyle="-", linewidth=2)
        ax.fill_between(dates, consumption, alpha=0.3)

        ax.set_xlabel("Date")
        ax.set_ylabel("Energy Consumption (kWh)")
        ax.set_title("Daily Energy Consumption")
        ax.grid(True, alpha=0.3)

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
        plt.xticks(rotation=45, ha="right")

        plt.tight_layout()

        # Save to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format="png", dpi=100)
        plt.close()

        img_buffer.seek(0)
        # Note: In actual implementation, you'd return an Image object for ReportLab
        # This is simplified for the example
        return None  # Placeholder - actual implementation would return Image object

    async def _generate_recommendations(
        self, summary_data: Dict, devices_data: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on data analysis"""
        recommendations = []

        # High consumption recommendation
        if summary_data["peak_power"] > 2000:
            recommendations.append(
                "Peak power consumption exceeds 2000W. Consider staggering device usage to reduce peak demand."
            )

        # Low efficiency devices
        for device in devices_data:
            if device["uptime"] < 20:
                recommendations.append(
                    f"Device {device['name']} has low utilization ({device['uptime']:.1f}%). "
                    f"Consider if this device needs to remain plugged in."
                )

        # Cost saving opportunities
        high_cost_devices = [
            d for d in devices_data if d["cost"] > summary_data["total_cost"] * 0.3
        ]
        if high_cost_devices:
            recommendations.append(
                f"{len(high_cost_devices)} device(s) account for over 30% of total cost. "
                f"Focus optimization efforts on these devices."
            )

        # General recommendations
        if not recommendations:
            recommendations.append(
                "System is operating efficiently. Continue monitoring for optimization opportunities."
            )

        return recommendations


class BulkOperations:
    """Handle bulk import/export operations"""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    async def bulk_import_devices(self, csv_data: bytes) -> Dict[str, Any]:
        """Bulk import devices from CSV"""
        try:
            # Parse CSV
            csv_file = io.StringIO(csv_data.decode("utf-8"))
            reader = csv.DictReader(csv_file)

            imported = 0
            failed = []

            for row in reader:
                try:
                    # Validate and add device
                    device_data = {
                        "device_ip": row.get("device_ip"),
                        "device_name": row.get("device_name"),
                        "device_alias": row.get("device_alias"),
                        "device_model": row.get("device_model"),
                        "device_type": row.get("device_type"),
                        "mac_address": row.get("mac_address"),
                        "location": row.get("location"),
                        "group_name": row.get("group_name"),
                    }

                    # Add device to database
                    await self.db_manager.add_device(device_data)
                    imported += 1

                except Exception as e:
                    failed.append({"row": row, "error": str(e)})

            return {
                "success": True,
                "imported": imported,
                "failed": len(failed),
                "failures": failed,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def bulk_update_devices(self, updates: List[Dict]) -> Dict[str, Any]:
        """Bulk update device configurations"""
        updated = 0
        failed = []

        for update in updates:
            try:
                device_ip = update.get("device_ip")
                if not device_ip:
                    raise ValueError("device_ip is required")

                # Update device
                await self.db_manager.update_device(device_ip, update)
                updated += 1

            except Exception as e:
                failed.append({"device_ip": device_ip, "error": str(e)})

        return {
            "success": True,
            "updated": updated,
            "failed": len(failed),
            "failures": failed,
        }

    async def bulk_delete_devices(self, device_ips: List[str]) -> Dict[str, Any]:
        """Bulk delete devices"""
        deleted = 0
        failed = []

        for device_ip in device_ips:
            try:
                await self.db_manager.delete_device(device_ip)
                deleted += 1
            except Exception as e:
                failed.append({"device_ip": device_ip, "error": str(e)})

        return {
            "success": True,
            "deleted": deleted,
            "failed": len(failed),
            "failures": failed,
        }
