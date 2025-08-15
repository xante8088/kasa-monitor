"""Performance monitoring system for Kasa Monitor.

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

import time
import psutil
import asyncio
import threading
import sqlite3
import json
import gc
import tracemalloc
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
import functools
import contextvars


class MetricType(Enum):
    """Types of performance metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class PerformanceMetric:
    """Performance metric data."""

    name: str
    value: float
    unit: str
    metric_type: MetricType
    tags: Optional[Dict[str, str]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["metric_type"] = self.metric_type.value
        data["timestamp"] = self.timestamp.isoformat()
        return data


class PerformanceProfiler:
    """Performance profiling utilities."""

    def __init__(self):
        """Initialize profiler."""
        self.profiles = {}
        self.active_profiles = {}
        self._lock = threading.Lock()

    def start_profile(self, name: str):
        """Start profiling a code section.

        Args:
            name: Profile name
        """
        with self._lock:
            self.active_profiles[name] = {
                "start_time": time.perf_counter(),
                "start_memory": psutil.Process().memory_info().rss,
            }

    def end_profile(self, name: str) -> Dict[str, Any]:
        """End profiling and return results.

        Args:
            name: Profile name

        Returns:
            Profile results
        """
        with self._lock:
            if name not in self.active_profiles:
                return {}

            profile = self.active_profiles.pop(name)
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss

            result = {
                "name": name,
                "duration_ms": (end_time - profile["start_time"]) * 1000,
                "memory_delta_mb": (end_memory - profile["start_memory"])
                / (1024 * 1024),
                "timestamp": datetime.now(),
            }

            # Store profile
            if name not in self.profiles:
                self.profiles[name] = []
            self.profiles[name].append(result)

            # Keep only last 100 profiles per name
            if len(self.profiles[name]) > 100:
                self.profiles[name] = self.profiles[name][-100:]

            return result

    def profile(self, name: Optional[str] = None):
        """Decorator for profiling functions.

        Args:
            name: Profile name (defaults to function name)
        """

        def decorator(func):
            profile_name = name or f"{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                self.start_profile(profile_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.end_profile(profile_name)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                self.start_profile(profile_name)
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    self.end_profile(profile_name)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get profiling statistics.

        Args:
            name: Profile name (None for all)

        Returns:
            Profile statistics
        """
        with self._lock:
            if name:
                profiles = self.profiles.get(name, [])
            else:
                profiles = []
                for profile_list in self.profiles.values():
                    profiles.extend(profile_list)

            if not profiles:
                return {}

            durations = [p["duration_ms"] for p in profiles]
            memory_deltas = [p["memory_delta_mb"] for p in profiles]

            return {
                "count": len(profiles),
                "duration": {
                    "min": min(durations),
                    "max": max(durations),
                    "avg": sum(durations) / len(durations),
                    "total": sum(durations),
                },
                "memory": {
                    "min": min(memory_deltas),
                    "max": max(memory_deltas),
                    "avg": sum(memory_deltas) / len(memory_deltas),
                    "total": sum(memory_deltas),
                },
            }


class MemoryMonitor:
    """Monitor memory usage and detect leaks."""

    def __init__(self):
        """Initialize memory monitor."""
        self.snapshots = deque(maxlen=100)
        self.tracemalloc_enabled = False
        self.baseline_snapshot = None

    def start_tracing(self):
        """Start memory tracing."""
        if not self.tracemalloc_enabled:
            tracemalloc.start()
            self.tracemalloc_enabled = True
            self.baseline_snapshot = tracemalloc.take_snapshot()

    def stop_tracing(self):
        """Stop memory tracing."""
        if self.tracemalloc_enabled:
            tracemalloc.stop()
            self.tracemalloc_enabled = False

    def take_snapshot(self) -> Dict[str, Any]:
        """Take memory snapshot.

        Returns:
            Memory statistics
        """
        process = psutil.Process()
        memory_info = process.memory_info()

        snapshot = {
            "timestamp": datetime.now(),
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024),
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 * 1024),
        }

        # Add tracemalloc data if enabled
        if self.tracemalloc_enabled:
            current = tracemalloc.take_snapshot()
            if self.baseline_snapshot:
                top_stats = current.compare_to(self.baseline_snapshot, "lineno")

                # Get top 10 memory allocations
                top_allocations = []
                for stat in top_stats[:10]:
                    top_allocations.append(
                        {
                            "file": (
                                stat.traceback.format()[0]
                                if stat.traceback
                                else "unknown"
                            ),
                            "size_mb": stat.size_diff / (1024 * 1024),
                            "count": stat.count_diff,
                        }
                    )

                snapshot["top_allocations"] = top_allocations

        # Garbage collection stats
        gc_stats = gc.get_stats()
        if gc_stats:
            snapshot["gc"] = {
                "collections": gc_stats[0].get("collections", 0),
                "collected": gc_stats[0].get("collected", 0),
                "uncollectable": gc_stats[0].get("uncollectable", 0),
            }

        self.snapshots.append(snapshot)
        return snapshot

    def detect_leak(self, threshold_mb: float = 100) -> bool:
        """Detect potential memory leak.

        Args:
            threshold_mb: Memory growth threshold in MB

        Returns:
            True if potential leak detected
        """
        if len(self.snapshots) < 10:
            return False

        # Compare current memory to 10 snapshots ago
        old_snapshot = self.snapshots[-10]
        current_snapshot = self.snapshots[-1]

        memory_growth = current_snapshot["rss_mb"] - old_snapshot["rss_mb"]

        return memory_growth > threshold_mb

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics.

        Returns:
            Memory statistics
        """
        if not self.snapshots:
            return {}

        current = self.snapshots[-1]

        # Calculate trends if enough data
        if len(self.snapshots) >= 2:
            memory_values = [s["rss_mb"] for s in self.snapshots]
            trend = memory_values[-1] - memory_values[0]
            avg_memory = sum(memory_values) / len(memory_values)
        else:
            trend = 0
            avg_memory = current["rss_mb"]

        return {
            "current_mb": current["rss_mb"],
            "average_mb": avg_memory,
            "trend_mb": trend,
            "percent_used": current["percent"],
            "leak_detected": self.detect_leak(),
            "gc_stats": current.get("gc", {}),
        }


class QueryPerformanceMonitor:
    """Monitor database query performance."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize query monitor.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.query_stats = defaultdict(list)
        self._lock = threading.Lock()

    def record_query(self, query: str, duration_ms: float, rows_affected: int = 0):
        """Record query execution.

        Args:
            query: SQL query
            duration_ms: Query duration in milliseconds
            rows_affected: Number of rows affected
        """
        # Normalize query for grouping
        normalized = self._normalize_query(query)

        with self._lock:
            self.query_stats[normalized].append(
                {
                    "duration_ms": duration_ms,
                    "rows_affected": rows_affected,
                    "timestamp": datetime.now(),
                }
            )

            # Keep only last 100 executions per query
            if len(self.query_stats[normalized]) > 100:
                self.query_stats[normalized] = self.query_stats[normalized][-100:]

    def _normalize_query(self, query: str) -> str:
        """Normalize query for grouping.

        Args:
            query: SQL query

        Returns:
            Normalized query
        """
        # Remove whitespace and convert to uppercase
        normalized = " ".join(query.split()).upper()

        # Remove specific values (keep structure)
        import re

        # Replace quoted strings
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        # Replace numbers
        normalized = re.sub(r"\b\d+\b", "?", normalized)

        return normalized

    def get_slow_queries(self, threshold_ms: float = 100) -> List[Dict[str, Any]]:
        """Get slow queries.

        Args:
            threshold_ms: Duration threshold in milliseconds

        Returns:
            List of slow queries
        """
        slow_queries = []

        with self._lock:
            for query, executions in self.query_stats.items():
                slow_execs = [e for e in executions if e["duration_ms"] > threshold_ms]

                if slow_execs:
                    durations = [e["duration_ms"] for e in slow_execs]
                    slow_queries.append(
                        {
                            "query": query,
                            "count": len(slow_execs),
                            "avg_duration_ms": sum(durations) / len(durations),
                            "max_duration_ms": max(durations),
                        }
                    )

        # Sort by average duration
        slow_queries.sort(key=lambda x: x["avg_duration_ms"], reverse=True)

        return slow_queries

    def analyze_queries(self) -> Dict[str, Any]:
        """Analyze query performance.

        Returns:
            Query analysis results
        """
        with self._lock:
            if not self.query_stats:
                return {}

            all_executions = []
            for executions in self.query_stats.values():
                all_executions.extend(executions)

            if not all_executions:
                return {}

            durations = [e["duration_ms"] for e in all_executions]

            return {
                "total_queries": len(all_executions),
                "unique_queries": len(self.query_stats),
                "duration": {
                    "min_ms": min(durations),
                    "max_ms": max(durations),
                    "avg_ms": sum(durations) / len(durations),
                    "total_ms": sum(durations),
                },
                "slow_queries": self.get_slow_queries(),
            }


class PerformanceMonitor:
    """Main performance monitoring system."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize performance monitor.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.profiler = PerformanceProfiler()
        self.memory_monitor = MemoryMonitor()
        self.query_monitor = QueryPerformanceMonitor(db_path)

        self.metrics = deque(maxlen=1000)
        self.running = False
        self.monitor_thread = None
        self.monitor_interval = 60  # seconds

        self._init_database()

    def _init_database(self):
        """Initialize performance tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                metric_type TEXT,
                tags TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_perf_metrics_name_time 
            ON performance_metrics(metric_name, timestamp DESC)
        """
        )

        conn.commit()
        conn.close()

    def start(self):
        """Start performance monitoring."""
        if self.running:
            return

        self.running = True
        self.memory_monitor.start_tracing()
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop(self):
        """Stop performance monitoring."""
        self.running = False
        self.memory_monitor.stop_tracing()

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                self._collect_system_metrics()

                # Take memory snapshot
                self.memory_monitor.take_snapshot()

                # Check for issues
                self._check_performance_issues()

            except Exception as e:
                print(f"Error in performance monitor: {e}")

            # Sleep for interval
            time.sleep(self.monitor_interval)

    def _collect_system_metrics(self):
        """Collect system performance metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        self.record_metric("system.cpu.percent", cpu_percent, "%", MetricType.GAUGE)

        # Memory metrics
        memory = psutil.virtual_memory()
        self.record_metric(
            "system.memory.percent", memory.percent, "%", MetricType.GAUGE
        )
        self.record_metric(
            "system.memory.used", memory.used / (1024 * 1024), "MB", MetricType.GAUGE
        )

        # Disk metrics
        disk = psutil.disk_usage("/")
        self.record_metric("system.disk.percent", disk.percent, "%", MetricType.GAUGE)

        # Network metrics
        net_io = psutil.net_io_counters()
        self.record_metric(
            "system.network.bytes_sent", net_io.bytes_sent, "bytes", MetricType.COUNTER
        )
        self.record_metric(
            "system.network.bytes_recv", net_io.bytes_recv, "bytes", MetricType.COUNTER
        )

        # Process metrics
        process = psutil.Process()
        self.record_metric(
            "process.cpu.percent", process.cpu_percent(), "%", MetricType.GAUGE
        )
        self.record_metric(
            "process.memory.rss",
            process.memory_info().rss / (1024 * 1024),
            "MB",
            MetricType.GAUGE,
        )
        self.record_metric(
            "process.threads", process.num_threads(), "count", MetricType.GAUGE
        )

    def _check_performance_issues(self):
        """Check for performance issues and alert."""
        # Check CPU usage
        cpu_percent = psutil.cpu_percent()
        if cpu_percent > 80:
            self.record_alert("high_cpu", f"CPU usage is {cpu_percent}%")

        # Check memory usage
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            self.record_alert("high_memory", f"Memory usage is {memory_percent}%")

        # Check for memory leak
        if self.memory_monitor.detect_leak():
            self.record_alert("memory_leak", "Potential memory leak detected")

        # Check disk space
        disk_percent = psutil.disk_usage("/").percent
        if disk_percent > 90:
            self.record_alert("low_disk", f"Disk usage is {disk_percent}%")

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        metric_type: MetricType,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Record a performance metric.

        Args:
            name: Metric name
            value: Metric value
            unit: Metric unit
            metric_type: Type of metric
            tags: Optional tags
        """
        metric = PerformanceMetric(
            name=name, value=value, unit=unit, metric_type=metric_type, tags=tags
        )

        self.metrics.append(metric)

        # Store in database
        self._store_metric(metric)

    def _store_metric(self, metric: PerformanceMetric):
        """Store metric in database.

        Args:
            metric: Metric to store
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO performance_metrics 
            (metric_name, metric_value, metric_unit, metric_type, tags)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                metric.name,
                metric.value,
                metric.unit,
                metric.metric_type.value,
                json.dumps(metric.tags) if metric.tags else None,
            ),
        )

        conn.commit()
        conn.close()

    def record_alert(self, alert_type: str, message: str):
        """Record performance alert.

        Args:
            alert_type: Type of alert
            message: Alert message
        """
        print(f"[PERFORMANCE ALERT] {alert_type}: {message}")

        # Store as metric
        self.record_metric(
            f"alert.{alert_type}", 1, "count", MetricType.COUNTER, {"message": message}
        )

    def get_metrics(
        self, name: Optional[str] = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get performance metrics.

        Args:
            name: Metric name filter
            hours: Number of hours to retrieve

        Returns:
            List of metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT metric_name, metric_value, metric_unit, metric_type, tags, timestamp
            FROM performance_metrics
            WHERE timestamp > datetime('now', '-{} hours')
        """.format(
            hours
        )

        if name:
            query += " AND metric_name = ?"
            cursor.execute(query, (name,))
        else:
            cursor.execute(query)

        metrics = []
        for row in cursor.fetchall():
            metrics.append(
                {
                    "name": row[0],
                    "value": row[1],
                    "unit": row[2],
                    "type": row[3],
                    "tags": json.loads(row[4]) if row[4] else {},
                    "timestamp": row[5],
                }
            )

        conn.close()
        return metrics

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary.

        Returns:
            Performance summary
        """
        return {
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            },
            "process": {
                "cpu_percent": psutil.Process().cpu_percent(),
                "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024),
                "threads": psutil.Process().num_threads(),
            },
            "memory": self.memory_monitor.get_stats(),
            "queries": self.query_monitor.analyze_queries(),
            "profiles": {
                name: self.profiler.get_stats(name)
                for name in list(self.profiler.profiles.keys())[:10]
            },
        }


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance.

    Returns:
        Performance monitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Decorators for easy use


def profile(name: Optional[str] = None):
    """Decorator for profiling functions.

    Args:
        name: Profile name
    """
    monitor = get_performance_monitor()
    return monitor.profiler.profile(name)


def monitor_query(func):
    """Decorator for monitoring database queries.

    Args:
        func: Function that executes queries
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Try to extract query from args/kwargs
            query = None
            if args and isinstance(args[0], str):
                query = args[0]
            elif "query" in kwargs:
                query = kwargs["query"]

            if query:
                monitor.query_monitor.record_query(query, duration_ms)

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record failed query
            if query:
                monitor.query_monitor.record_query(f"FAILED: {query}", duration_ms)

            raise

    return wrapper
