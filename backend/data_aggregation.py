"""
Data Aggregation Module for Kasa Monitor
Handles data aggregation, downsampling, and statistical calculations
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AggregationPeriod(Enum):
    """Aggregation time periods"""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class DataAggregator:
    """Handles data aggregation and downsampling"""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.aggregation_tasks = {}
        self.is_running = False

    async def start(self):
        """Start aggregation service"""
        self.is_running = True

        # Schedule aggregation tasks
        self.aggregation_tasks["hourly"] = asyncio.create_task(
            self._hourly_aggregation_loop()
        )
        self.aggregation_tasks["daily"] = asyncio.create_task(
            self._daily_aggregation_loop()
        )
        self.aggregation_tasks["cleanup"] = asyncio.create_task(self._cleanup_loop())

        logger.info("Data aggregation service started")

    async def stop(self):
        """Stop aggregation service"""
        self.is_running = False

        # Cancel all tasks
        for task in self.aggregation_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.aggregation_tasks.values(), return_exceptions=True)

        logger.info("Data aggregation service stopped")

    async def _hourly_aggregation_loop(self):
        """Run hourly aggregation every hour"""
        while self.is_running:
            try:
                await self.aggregate_hourly_data()
                await asyncio.sleep(3600)  # Sleep for 1 hour
            except Exception as e:
                logger.error(f"Hourly aggregation error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error

    async def _daily_aggregation_loop(self):
        """Run daily aggregation once per day"""
        while self.is_running:
            try:
                await self.aggregate_daily_data()

                # Calculate time until next midnight
                now = datetime.now()
                tomorrow = now + timedelta(days=1)
                midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day)
                seconds_until_midnight = (midnight - now).total_seconds()

                await asyncio.sleep(seconds_until_midnight)
            except Exception as e:
                logger.error(f"Daily aggregation error: {e}")
                await asyncio.sleep(3600)  # Retry after 1 hour on error

    async def _cleanup_loop(self):
        """Clean up old detailed data based on retention policy"""
        while self.is_running:
            try:
                await self.cleanup_old_data()
                await asyncio.sleep(86400)  # Run once per day
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(3600)

    async def aggregate_hourly_data(self, force_date: Optional[datetime] = None):
        """Aggregate data into hourly summaries"""

        # Determine the hour to aggregate
        if force_date:
            target_hour = force_date.replace(minute=0, second=0, microsecond=0)
        else:
            # Aggregate the previous hour
            target_hour = (datetime.now() - timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )

        next_hour = target_hour + timedelta(hours=1)

        logger.info(f"Aggregating hourly data for {target_hour}")

        # Get all devices
        devices = await self.db_manager.get_all_devices()

        for device in devices:
            device_ip = device["device_ip"]

            # Get readings for the hour
            query = """
                SELECT 
                    COUNT(*) as count,
                    AVG(power_w) as avg_power,
                    MAX(power_w) as max_power,
                    MIN(power_w) as min_power,
                    SUM(energy_kwh) as total_energy,
                    AVG(voltage_v) as avg_voltage,
                    AVG(current_a) as avg_current
                FROM readings
                WHERE device_ip = ?
                    AND timestamp >= ?
                    AND timestamp < ?
            """

            result = await self.db_manager.execute_query(
                query, [device_ip, target_hour.isoformat(), next_hour.isoformat()]
            )

            if result and result[0][0] > 0:  # If there are readings
                # Insert hourly summary
                await self._insert_hourly_summary(
                    device_ip=device_ip,
                    hour=target_hour,
                    count=result[0][0],
                    avg_power=result[0][1],
                    max_power=result[0][2],
                    min_power=result[0][3],
                    total_energy=result[0][4],
                    avg_voltage=result[0][5],
                    avg_current=result[0][6],
                )

    async def aggregate_daily_data(self, force_date: Optional[datetime] = None):
        """Aggregate data into daily summaries"""

        # Determine the day to aggregate
        if force_date:
            target_date = force_date.date()
        else:
            # Aggregate yesterday
            target_date = (datetime.now() - timedelta(days=1)).date()

        logger.info(f"Aggregating daily data for {target_date}")

        # Get all devices
        devices = await self.db_manager.get_all_devices()

        for device in devices:
            device_ip = device["device_ip"]

            # Aggregate from hourly summaries if available, otherwise from raw readings
            summary = await self._get_daily_summary(device_ip, target_date)

            if summary:
                # Calculate cost based on energy consumption
                cost = await self._calculate_daily_cost(
                    device_ip, summary["total_energy"], target_date
                )

                # Insert or update daily summary
                await self._insert_daily_summary(
                    device_ip=device_ip, date=target_date, **summary, cost=cost
                )

    async def aggregate_monthly_data(self, year: int, month: int):
        """Aggregate data into monthly summaries"""

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        logger.info(f"Aggregating monthly data for {year}-{month:02d}")

        # Get all devices
        devices = await self.db_manager.get_all_devices()

        for device in devices:
            device_ip = device["device_ip"]

            # Aggregate from daily summaries
            query = """
                SELECT 
                    COUNT(*) as days,
                    SUM(total_kwh) as total_energy,
                    AVG(average_power_w) as avg_power,
                    MAX(peak_power_w) as max_power,
                    SUM(cost) as total_cost,
                    SUM(on_time_hours) as total_on_time
                FROM daily_summaries
                WHERE device_ip = ?
                    AND date >= ?
                    AND date < ?
            """

            result = await self.db_manager.execute_query(
                query,
                [device_ip, start_date.date().isoformat(), end_date.date().isoformat()],
            )

            if result and result[0][0] > 0:
                await self._insert_monthly_summary(
                    device_ip=device_ip,
                    year=year,
                    month=month,
                    days=result[0][0],
                    total_energy=result[0][1],
                    avg_power=result[0][2],
                    max_power=result[0][3],
                    total_cost=result[0][4],
                    total_on_time=result[0][5],
                )

    async def get_aggregated_data(
        self,
        device_ip: Optional[str] = None,
        period: AggregationPeriod = AggregationPeriod.DAY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get aggregated data for specified period"""

        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        if period == AggregationPeriod.HOUR:
            return await self._get_hourly_data(device_ip, start_date, end_date)
        elif period == AggregationPeriod.DAY:
            return await self._get_daily_data(device_ip, start_date, end_date)
        elif period == AggregationPeriod.WEEK:
            return await self._get_weekly_data(device_ip, start_date, end_date)
        elif period == AggregationPeriod.MONTH:
            return await self._get_monthly_data(device_ip, start_date, end_date)
        else:
            raise ValueError(f"Unsupported aggregation period: {period}")

    async def calculate_statistics(
        self,
        device_ip: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculate statistical metrics for a device"""

        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get raw readings
        query = """
            SELECT power_w, energy_kwh
            FROM readings
            WHERE device_ip = ?
                AND timestamp BETWEEN ? AND ?
                AND power_w IS NOT NULL
        """

        results = await self.db_manager.execute_query(
            query, [device_ip, start_date.isoformat(), end_date.isoformat()]
        )

        if not results:
            return {}

        power_values = [row[0] for row in results]
        energy_values = [row[1] for row in results if row[1] is not None]

        # Calculate statistics
        stats = {
            "count": len(power_values),
            "power": {
                "mean": statistics.mean(power_values),
                "median": statistics.median(power_values),
                "mode": (
                    statistics.mode(power_values)
                    if len(set(power_values)) < len(power_values)
                    else None
                ),
                "stdev": statistics.stdev(power_values) if len(power_values) > 1 else 0,
                "variance": (
                    statistics.variance(power_values) if len(power_values) > 1 else 0
                ),
                "min": min(power_values),
                "max": max(power_values),
                "range": max(power_values) - min(power_values),
                "percentiles": {
                    "25": (
                        statistics.quantiles(power_values, n=4)[0]
                        if len(power_values) > 1
                        else power_values[0]
                    ),
                    "50": statistics.median(power_values),
                    "75": (
                        statistics.quantiles(power_values, n=4)[2]
                        if len(power_values) > 1
                        else power_values[0]
                    ),
                    "90": (
                        statistics.quantiles(power_values, n=10)[8]
                        if len(power_values) > 9
                        else max(power_values)
                    ),
                    "95": (
                        statistics.quantiles(power_values, n=20)[18]
                        if len(power_values) > 19
                        else max(power_values)
                    ),
                },
            },
            "energy": {
                "total": sum(energy_values),
                "mean": statistics.mean(energy_values) if energy_values else 0,
                "max": max(energy_values) if energy_values else 0,
            },
        }

        return stats

    async def get_trend_analysis(
        self,
        device_ip: str,
        period: AggregationPeriod = AggregationPeriod.DAY,
        lookback_periods: int = 30,
    ) -> Dict[str, Any]:
        """Analyze trends in device usage"""

        end_date = datetime.now()

        if period == AggregationPeriod.DAY:
            start_date = end_date - timedelta(days=lookback_periods)
        elif period == AggregationPeriod.WEEK:
            start_date = end_date - timedelta(weeks=lookback_periods)
        elif period == AggregationPeriod.MONTH:
            start_date = end_date - timedelta(days=lookback_periods * 30)
        else:
            start_date = end_date - timedelta(days=lookback_periods)

        # Get aggregated data
        data = await self.get_aggregated_data(device_ip, period, start_date, end_date)

        if len(data) < 2:
            return {"trend": "insufficient_data"}

        # Extract values for trend analysis
        timestamps = [d["timestamp"] for d in data]
        values = [d["avg_power"] for d in data]

        # Calculate linear regression (simplified)
        n = len(values)
        x = list(range(n))

        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        intercept = y_mean - slope * x_mean

        # Determine trend direction
        if abs(slope) < 0.01:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # Calculate percentage change
        if values[0] != 0:
            percent_change = ((values[-1] - values[0]) / values[0]) * 100
        else:
            percent_change = 0

        return {
            "trend": trend,
            "slope": slope,
            "intercept": intercept,
            "percent_change": percent_change,
            "start_value": values[0],
            "end_value": values[-1],
            "average": y_mean,
            "data_points": n,
        }

    async def cleanup_old_data(self, retention_days: Optional[int] = None):
        """Clean up old detailed data based on retention policy"""

        if retention_days is None:
            # Get from configuration or use default
            retention_days = 7  # Keep detailed data for 7 days by default

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        logger.info(f"Cleaning up data older than {cutoff_date}")

        # Delete old raw readings (keep aggregated data)
        query = "DELETE FROM readings WHERE timestamp < ?"
        result = await self.db_manager.execute_query(query, [cutoff_date.isoformat()])

        # Vacuum database to reclaim space
        await self.db_manager.execute_query("VACUUM")

        logger.info("Data cleanup completed")

    # Helper methods

    async def _get_daily_summary(self, device_ip: str, date) -> Optional[Dict]:
        """Get daily summary from hourly data or raw readings"""

        # Try to get from hourly summaries first
        query = """
            SELECT 
                COUNT(*) as hours,
                SUM(total_energy) as total_energy,
                AVG(avg_power) as avg_power,
                MAX(max_power) as peak_power,
                MIN(min_power) as min_power,
                SUM(CASE WHEN avg_power > 0 THEN 1 ELSE 0 END) as on_hours
            FROM hourly_summaries
            WHERE device_ip = ?
                AND DATE(hour) = ?
        """

        result = await self.db_manager.execute_query(
            query, [device_ip, date.isoformat()]
        )

        if result and result[0][0] > 0:
            return {
                "total_kwh": result[0][1],
                "average_power_w": result[0][2],
                "peak_power_w": result[0][3],
                "min_power_w": result[0][4],
                "on_time_hours": result[0][5],
            }

        # Fall back to raw readings
        query = """
            SELECT 
                SUM(energy_kwh) as total_energy,
                AVG(power_w) as avg_power,
                MAX(power_w) as peak_power,
                MIN(power_w) as min_power,
                COUNT(CASE WHEN power_w > 0 THEN 1 END) * 1.0 / COUNT(*) * 24 as on_hours
            FROM readings
            WHERE device_ip = ?
                AND DATE(timestamp) = ?
        """

        result = await self.db_manager.execute_query(
            query, [device_ip, date.isoformat()]
        )

        if result and result[0][0] is not None:
            return {
                "total_kwh": result[0][0],
                "average_power_w": result[0][1],
                "peak_power_w": result[0][2],
                "min_power_w": result[0][3],
                "on_time_hours": result[0][4],
            }

        return None

    async def _calculate_daily_cost(
        self, device_ip: str, energy_kwh: float, date
    ) -> float:
        """Calculate cost for daily energy consumption"""
        # This is a simplified calculation - should use actual rate structure
        # Default to $0.12/kWh if no rate is configured
        rate = 0.12
        return energy_kwh * rate

    async def _insert_hourly_summary(self, **kwargs):
        """Insert hourly summary record"""
        # Create table if not exists
        await self.db_manager.execute_query(
            """
            CREATE TABLE IF NOT EXISTS hourly_summaries (
                device_ip TEXT,
                hour TIMESTAMP,
                count INTEGER,
                avg_power REAL,
                max_power REAL,
                min_power REAL,
                total_energy REAL,
                avg_voltage REAL,
                avg_current REAL,
                PRIMARY KEY (device_ip, hour)
            )
        """
        )

        # Insert or replace summary
        await self.db_manager.execute_query(
            """
            INSERT OR REPLACE INTO hourly_summaries
            (device_ip, hour, count, avg_power, max_power, min_power, total_energy, avg_voltage, avg_current)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                kwargs["device_ip"],
                kwargs["hour"].isoformat(),
                kwargs["count"],
                kwargs["avg_power"],
                kwargs["max_power"],
                kwargs["min_power"],
                kwargs["total_energy"],
                kwargs["avg_voltage"],
                kwargs["avg_current"],
            ],
        )

    async def _insert_daily_summary(self, **kwargs):
        """Insert or update daily summary record"""
        # The table should already exist from the main schema
        # Insert or replace summary
        await self.db_manager.execute_query(
            """
            INSERT OR REPLACE INTO daily_summaries
            (device_ip, date, total_kwh, peak_power_w, average_power_w, min_power_w, on_time_hours, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                kwargs["device_ip"],
                kwargs["date"].isoformat(),
                kwargs["total_kwh"],
                kwargs["peak_power_w"],
                kwargs["average_power_w"],
                kwargs["min_power_w"],
                kwargs["on_time_hours"],
                kwargs["cost"],
            ],
        )

    async def _insert_monthly_summary(self, **kwargs):
        """Insert monthly summary record"""
        # Create table if not exists
        await self.db_manager.execute_query(
            """
            CREATE TABLE IF NOT EXISTS monthly_summaries (
                device_ip TEXT,
                year INTEGER,
                month INTEGER,
                days INTEGER,
                total_energy REAL,
                avg_power REAL,
                max_power REAL,
                total_cost REAL,
                total_on_time REAL,
                PRIMARY KEY (device_ip, year, month)
            )
        """
        )

        # Insert or replace summary
        await self.db_manager.execute_query(
            """
            INSERT OR REPLACE INTO monthly_summaries
            (device_ip, year, month, days, total_energy, avg_power, max_power, total_cost, total_on_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                kwargs["device_ip"],
                kwargs["year"],
                kwargs["month"],
                kwargs["days"],
                kwargs["total_energy"],
                kwargs["avg_power"],
                kwargs["max_power"],
                kwargs["total_cost"],
                kwargs["total_on_time"],
            ],
        )

    async def _get_hourly_data(
        self, device_ip: Optional[str], start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get hourly aggregated data"""
        query = """
            SELECT hour, device_ip, avg_power, max_power, total_energy
            FROM hourly_summaries
            WHERE hour BETWEEN ? AND ?
        """
        params = [start_date.isoformat(), end_date.isoformat()]

        if device_ip:
            query += " AND device_ip = ?"
            params.append(device_ip)

        query += " ORDER BY hour"

        results = await self.db_manager.execute_query(query, params)

        return [
            {
                "timestamp": row[0],
                "device_ip": row[1],
                "avg_power": row[2],
                "max_power": row[3],
                "total_energy": row[4],
            }
            for row in results
        ]

    async def _get_daily_data(
        self, device_ip: Optional[str], start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get daily aggregated data"""
        query = """
            SELECT date, device_ip, average_power_w, peak_power_w, total_kwh, cost
            FROM daily_summaries
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date.date().isoformat(), end_date.date().isoformat()]

        if device_ip:
            query += " AND device_ip = ?"
            params.append(device_ip)

        query += " ORDER BY date"

        results = await self.db_manager.execute_query(query, params)

        return [
            {
                "timestamp": row[0],
                "device_ip": row[1],
                "avg_power": row[2],
                "max_power": row[3],
                "total_energy": row[4],
                "cost": row[5],
            }
            for row in results
        ]

    async def _get_weekly_data(
        self, device_ip: Optional[str], start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get weekly aggregated data"""
        query = """
            SELECT 
                strftime('%Y-W%W', date) as week,
                device_ip,
                AVG(average_power_w) as avg_power,
                MAX(peak_power_w) as max_power,
                SUM(total_kwh) as total_energy,
                SUM(cost) as total_cost
            FROM daily_summaries
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date.date().isoformat(), end_date.date().isoformat()]

        if device_ip:
            query += " AND device_ip = ?"
            params.append(device_ip)

        query += " GROUP BY week, device_ip ORDER BY week"

        results = await self.db_manager.execute_query(query, params)

        return [
            {
                "timestamp": row[0],
                "device_ip": row[1],
                "avg_power": row[2],
                "max_power": row[3],
                "total_energy": row[4],
                "total_cost": row[5],
            }
            for row in results
        ]

    async def _get_monthly_data(
        self, device_ip: Optional[str], start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get monthly aggregated data"""
        query = """
            SELECT 
                printf('%04d-%02d', year, month) as month,
                device_ip,
                avg_power,
                max_power,
                total_energy,
                total_cost
            FROM monthly_summaries
            WHERE (year * 12 + month) BETWEEN ? AND ?
        """

        start_months = start_date.year * 12 + start_date.month
        end_months = end_date.year * 12 + end_date.month
        params = [start_months, end_months]

        if device_ip:
            query += " AND device_ip = ?"
            params.append(device_ip)

        query += " ORDER BY year, month"

        results = await self.db_manager.execute_query(query, params)

        return [
            {
                "timestamp": row[0],
                "device_ip": row[1],
                "avg_power": row[2],
                "max_power": row[3],
                "total_energy": row[4],
                "total_cost": row[5],
            }
            for row in results
        ]
