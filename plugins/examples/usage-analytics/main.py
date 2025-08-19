"""Usage Analytics Example Plugin.

This plugin tracks device usage patterns and generates insights
about power consumption, usage times, and efficiency.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    import pandas as pd
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    np = None
    pd = None

from plugin_system import PluginBase

logger = logging.getLogger(__name__)


class UsageAnalyticsPlugin(PluginBase):
    """Example plugin that analyzes device usage patterns."""

    def __init__(self):
        super().__init__()
        self.analysis_interval = 3600  # 1 hour
        self.retention_days = 30
        self.min_usage_threshold = 10.0  # watts
        self.generate_reports = True
        self.analytics_db_path = None
        self.analysis_task = None

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            if not ANALYTICS_AVAILABLE:
                logger.error("Required analytics libraries (pandas, numpy) not available")
                return False

            # Load configuration
            config = await self.get_config()
            self.analysis_interval = config.get('analysis_interval', 3600)
            self.retention_days = config.get('retention_days', 30)
            self.min_usage_threshold = config.get('min_usage_threshold', 10.0)
            self.generate_reports = config.get('generate_reports', True)

            # Setup analytics database
            plugin_data_dir = Path("./plugins/data/usage-analytics")
            plugin_data_dir.mkdir(parents=True, exist_ok=True)
            self.analytics_db_path = plugin_data_dir / "analytics.db"
            
            await self.init_analytics_db()

            # Register hooks
            await self.hook_manager.register_hook(
                'device.reading_updated',
                self.on_device_reading_updated
            )
            await self.hook_manager.register_hook(
                'analytics.report_requested',
                self.on_report_requested
            )

            # Start analysis task
            self.analysis_task = asyncio.create_task(self.analysis_loop())

            logger.info(f"Usage Analytics plugin initialized with {self.analysis_interval}s interval")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Usage Analytics plugin: {e}")
            return False

    async def shutdown(self):
        """Shutdown the plugin."""
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass

        # Unregister hooks
        await self.hook_manager.unregister_hook(
            'device.reading_updated',
            self.on_device_reading_updated
        )
        await self.hook_manager.unregister_hook(
            'analytics.report_requested',
            self.on_report_requested
        )

        logger.info("Usage Analytics plugin shutdown complete")

    async def init_analytics_db(self):
        """Initialize analytics database."""
        conn = sqlite3.connect(str(self.analytics_db_path))
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS device_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_ip TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    avg_power REAL,
                    max_power REAL,
                    min_power REAL,
                    total_energy REAL,
                    active_time INTEGER,
                    inactive_time INTEGER,
                    efficiency_score REAL,
                    usage_pattern TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_ip TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_energy_kwh REAL,
                    avg_power_w REAL,
                    peak_power_w REAL,
                    active_hours REAL,
                    cost_estimate REAL,
                    efficiency_rating TEXT,
                    UNIQUE(device_ip, date)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_device_analytics_timestamp 
                ON device_analytics(device_ip, timestamp)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_summaries_date 
                ON daily_summaries(device_ip, date)
            ''')
            
            conn.commit()
        finally:
            conn.close()

    async def on_device_reading_updated(self, device_data: Dict[str, Any]):
        """Handle device reading updates for analytics."""
        try:
            device_ip = device_data.get('ip')
            current_power = device_data.get('current_power_w', 0)
            timestamp = device_data.get('timestamp', datetime.now(timezone.utc))
            
            # Store raw data point for later analysis
            await self.store_data_point(device_ip, current_power, timestamp)
            
        except Exception as e:
            logger.error(f"Error processing device reading for analytics: {e}")

    async def on_report_requested(self, params: Dict[str, Any]):
        """Handle analytics report requests."""
        try:
            report_type = params.get('type', 'summary')
            device_ip = params.get('device_ip')
            days = params.get('days', 7)
            
            if report_type == 'usage_summary':
                report = await self.generate_usage_summary(device_ip, days)
            elif report_type == 'efficiency_analysis':
                report = await self.generate_efficiency_analysis(device_ip, days)
            elif report_type == 'pattern_analysis':
                report = await self.generate_pattern_analysis(device_ip, days)
            else:
                report = await self.generate_general_summary(days)
                
            # Emit report via hook system
            await self.hook_manager.emit_hook('analytics.report_generated', {
                'type': report_type,
                'device_ip': device_ip,
                'report': report,
                'generated_at': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error generating analytics report: {e}")

    async def analysis_loop(self):
        """Main analytics processing loop."""
        while True:
            try:
                await asyncio.sleep(self.analysis_interval)
                await self.run_periodic_analysis()
                await self.cleanup_old_data()
                
                if self.generate_reports:
                    await self.generate_daily_summaries()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                await asyncio.sleep(60)  # Brief pause before retrying

    async def store_data_point(self, device_ip: str, power: float, timestamp: datetime):
        """Store a data point for later analysis."""
        # For this example, we'll aggregate data points in memory
        # In a real implementation, you might store raw data points
        pass

    async def run_periodic_analysis(self):
        """Run periodic analysis on device data."""
        try:
            # Get recent device data from main database
            devices = await self.db_manager.get_monitored_devices()
            
            for device in devices:
                device_ip = device['ip']
                await self.analyze_device_usage(device_ip)
                
        except Exception as e:
            logger.error(f"Error in periodic analysis: {e}")

    async def analyze_device_usage(self, device_ip: str):
        """Analyze usage patterns for a specific device."""
        try:
            # Get recent readings (last hour)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            # In a real implementation, you'd query device readings
            # For this example, we'll simulate analysis
            
            # Simulate analytics calculations
            avg_power = 250.5
            max_power = 1200.0
            min_power = 15.0
            total_energy = 0.25  # kWh
            active_time = 45 * 60  # 45 minutes in seconds
            inactive_time = 15 * 60  # 15 minutes in seconds
            
            # Calculate efficiency score (0-1)
            efficiency_score = min(avg_power / max_power, 1.0) if max_power > 0 else 0.0
            
            # Determine usage pattern
            if avg_power > self.min_usage_threshold:
                if max_power / avg_power > 3:
                    usage_pattern = "spiky"
                elif max_power / avg_power > 1.5:
                    usage_pattern = "variable"
                else:
                    usage_pattern = "steady"
            else:
                usage_pattern = "idle"
            
            # Store analytics result
            await self.store_analytics_result(
                device_ip, end_time, avg_power, max_power, min_power,
                total_energy, active_time, inactive_time, efficiency_score, usage_pattern
            )
            
        except Exception as e:
            logger.error(f"Error analyzing device {device_ip}: {e}")

    async def store_analytics_result(self, device_ip: str, timestamp: datetime,
                                   avg_power: float, max_power: float, min_power: float,
                                   total_energy: float, active_time: int, inactive_time: int,
                                   efficiency_score: float, usage_pattern: str):
        """Store analytics result in database."""
        conn = sqlite3.connect(str(self.analytics_db_path))
        try:
            conn.execute('''
                INSERT INTO device_analytics 
                (device_ip, timestamp, avg_power, max_power, min_power, total_energy,
                 active_time, inactive_time, efficiency_score, usage_pattern)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (device_ip, timestamp, avg_power, max_power, min_power, total_energy,
                  active_time, inactive_time, efficiency_score, usage_pattern))
            conn.commit()
        finally:
            conn.close()

    async def generate_usage_summary(self, device_ip: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """Generate usage summary report."""
        conn = sqlite3.connect(str(self.analytics_db_path))
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            if device_ip:
                query = '''
                    SELECT AVG(avg_power), MAX(max_power), SUM(total_energy),
                           AVG(efficiency_score), COUNT(*)
                    FROM device_analytics 
                    WHERE device_ip = ? AND timestamp > ?
                '''
                params = (device_ip, cutoff_date)
            else:
                query = '''
                    SELECT AVG(avg_power), MAX(max_power), SUM(total_energy),
                           AVG(efficiency_score), COUNT(*)
                    FROM device_analytics 
                    WHERE timestamp > ?
                '''
                params = (cutoff_date,)
            
            result = conn.execute(query, params).fetchone()
            
            return {
                'period_days': days,
                'device_ip': device_ip,
                'avg_power_w': round(result[0] or 0, 2),
                'peak_power_w': round(result[1] or 0, 2),
                'total_energy_kwh': round(result[2] or 0, 3),
                'avg_efficiency': round(result[3] or 0, 3),
                'data_points': result[4] or 0
            }
            
        finally:
            conn.close()

    async def generate_efficiency_analysis(self, device_ip: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """Generate efficiency analysis report."""
        conn = sqlite3.connect(str(self.analytics_db_path))
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            if device_ip:
                query = '''
                    SELECT usage_pattern, COUNT(*), AVG(efficiency_score)
                    FROM device_analytics 
                    WHERE device_ip = ? AND timestamp > ?
                    GROUP BY usage_pattern
                '''
                params = (device_ip, cutoff_date)
            else:
                query = '''
                    SELECT usage_pattern, COUNT(*), AVG(efficiency_score)
                    FROM device_analytics 
                    WHERE timestamp > ?
                    GROUP BY usage_pattern
                '''
                params = (cutoff_date,)
            
            results = conn.execute(query, params).fetchall()
            
            patterns = {}
            for pattern, count, avg_efficiency in results:
                patterns[pattern] = {
                    'occurrences': count,
                    'avg_efficiency': round(avg_efficiency or 0, 3)
                }
            
            return {
                'period_days': days,
                'device_ip': device_ip,
                'usage_patterns': patterns
            }
            
        finally:
            conn.close()

    async def generate_pattern_analysis(self, device_ip: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """Generate usage pattern analysis."""
        # Simplified pattern analysis
        return {
            'period_days': days,
            'device_ip': device_ip,
            'analysis': 'Pattern analysis would analyze temporal usage patterns, peak hours, etc.'
        }

    async def generate_general_summary(self, days: int = 7) -> Dict[str, Any]:
        """Generate general analytics summary."""
        usage_summary = await self.generate_usage_summary(None, days)
        efficiency_analysis = await self.generate_efficiency_analysis(None, days)
        
        return {
            'summary': usage_summary,
            'efficiency': efficiency_analysis,
            'recommendations': [
                "Monitor devices with low efficiency scores",
                "Consider scheduling for devices with spiky usage patterns",
                "Review inactive devices for potential energy savings"
            ]
        }

    async def generate_daily_summaries(self):
        """Generate daily summary reports."""
        # This would generate daily summary records
        # Simplified for example
        pass

    async def cleanup_old_data(self):
        """Clean up old analytics data."""
        conn = sqlite3.connect(str(self.analytics_db_path))
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            conn.execute('DELETE FROM device_analytics WHERE timestamp < ?', (cutoff_date,))
            conn.execute('DELETE FROM daily_summaries WHERE date < ?', (cutoff_date.date(),))
            conn.commit()
        finally:
            conn.close()

    async def get_status(self) -> Dict[str, Any]:
        """Get plugin status information."""
        conn = sqlite3.connect(str(self.analytics_db_path))
        try:
            analytics_count = conn.execute('SELECT COUNT(*) FROM device_analytics').fetchone()[0]
            summaries_count = conn.execute('SELECT COUNT(*) FROM daily_summaries').fetchone()[0]
            
            return {
                'analysis_interval': self.analysis_interval,
                'retention_days': self.retention_days,
                'analytics_records': analytics_count,
                'daily_summaries': summaries_count,
                'libraries_available': ANALYTICS_AVAILABLE,
                'analysis_active': self.analysis_task is not None and not self.analysis_task.done()
            }
        finally:
            conn.close()

    async def handle_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plugin-specific actions."""
        if action == 'generate_report':
            report_type = params.get('type', 'summary')
            device_ip = params.get('device_ip')
            days = params.get('days', 7)
            
            await self.on_report_requested({
                'type': report_type,
                'device_ip': device_ip,
                'days': days
            })
            
            return {'status': 'success', 'message': f'{report_type} report generation requested'}
            
        elif action == 'cleanup_data':
            await self.cleanup_old_data()
            return {'status': 'success', 'message': 'Old analytics data cleaned up'}
            
        elif action == 'run_analysis':
            await self.run_periodic_analysis()
            return {'status': 'success', 'message': 'Manual analysis completed'}
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}