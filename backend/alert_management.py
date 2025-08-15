"""Alert management system with rules engine and escalation.

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

import sqlite3
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import operator
import re
from collections import defaultdict
import statistics


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    EMERGENCY = 5


class AlertStatus(Enum):
    """Alert status states."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


class AlertCategory(Enum):
    """Alert categories."""

    DEVICE = "device"
    ENERGY = "energy"
    SYSTEM = "system"
    SECURITY = "security"
    NETWORK = "network"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


class RuleOperator(Enum):
    """Rule comparison operators."""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class AlertRule:
    """Alert rule definition."""

    name: str
    description: str
    category: AlertCategory
    conditions: List[Dict[str, Any]]
    severity: AlertSeverity
    threshold_count: int = 1
    threshold_window: int = 60  # seconds
    cooldown_period: int = 300  # seconds
    enabled: bool = True
    metadata: Optional[Dict] = None

    def evaluate(self, data: Dict[str, Any]) -> bool:
        """Evaluate rule against data.

        Args:
            data: Data to evaluate

        Returns:
            True if rule matches
        """
        for condition in self.conditions:
            if not self._evaluate_condition(condition, data):
                return False
        return True

    def _evaluate_condition(self, condition: Dict, data: Dict) -> bool:
        """Evaluate single condition.

        Args:
            condition: Condition to evaluate
            data: Data to evaluate against

        Returns:
            True if condition matches
        """
        field = condition.get("field")
        operator_str = condition.get("operator")
        value = condition.get("value")

        # Get field value from data (support nested fields)
        field_value = self._get_field_value(data, field)

        if field_value is None:
            return False

        # Get operator function
        op = self._get_operator(operator_str)

        # Evaluate condition
        try:
            if operator_str in ["contains", "not_contains"]:
                return op(str(value), str(field_value))
            elif operator_str == "matches":
                return bool(re.match(value, str(field_value)))
            elif operator_str in ["in", "not_in"]:
                return op(field_value, value)
            else:
                return op(field_value, value)
        except Exception:
            return False

    def _get_field_value(self, data: Dict, field: str) -> Any:
        """Get field value from data (supports nested fields).

        Args:
            data: Data dictionary
            field: Field path (e.g., "device.status")

        Returns:
            Field value
        """
        parts = field.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _get_operator(self, operator_str: str) -> Callable:
        """Get operator function.

        Args:
            operator_str: Operator string

        Returns:
            Operator function
        """
        operators = {
            "==": operator.eq,
            "!=": operator.ne,
            ">": operator.gt,
            ">=": operator.ge,
            "<": operator.lt,
            "<=": operator.le,
            "contains": operator.contains,
            "not_contains": lambda a, b: not operator.contains(a, b),
            "in": operator.contains,
            "not_in": lambda a, b: not operator.contains(b, a),
        }

        return operators.get(operator_str, operator.eq)


@dataclass
class Alert:
    """Alert instance."""

    rule_name: str
    severity: AlertSeverity
    category: AlertCategory
    title: str
    message: str
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    data: Optional[Dict] = None
    metadata: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["severity"] = self.severity.value
        data["category"] = self.category.value
        data["status"] = self.status.value
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        if self.acknowledged_at:
            data["acknowledged_at"] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            data["resolved_at"] = self.resolved_at.isoformat()
        return data


class AlertManager:
    """Main alert management system."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize alert manager.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.rules = {}
        self.active_alerts = {}
        self.alert_history = defaultdict(list)
        self.callbacks = defaultdict(list)
        self.running = False
        self.monitor_thread = None

        self._init_database()
        self._load_rules()

    def _init_database(self):
        """Initialize alert tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Alert rules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                conditions TEXT NOT NULL,
                severity INTEGER NOT NULL,
                threshold_count INTEGER DEFAULT 1,
                threshold_window INTEGER DEFAULT 60,
                cooldown_period INTEGER DEFAULT 300,
                enabled BOOLEAN DEFAULT 1,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Active alerts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                rule_name TEXT NOT NULL,
                severity INTEGER NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                data TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TIMESTAMP,
                acknowledged_by TEXT,
                resolved_at TIMESTAMP,
                resolved_by TEXT,
                FOREIGN KEY (rule_name) REFERENCES alert_rules(name)
            )
        """
        )

        # Alert history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
            )
        """
        )

        # Escalation policies table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS escalation_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                rules TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Alert suppressions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_suppressions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_pattern TEXT,
                source_pattern TEXT,
                category TEXT,
                severity_min INTEGER,
                severity_max INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                reason TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Alert metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rule_name) REFERENCES alert_rules(name)
            )
        """
        )

        conn.commit()
        conn.close()

    def create_rule(self, rule: AlertRule) -> bool:
        """Create alert rule.

        Args:
            rule: Alert rule

        Returns:
            True if created successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO alert_rules 
                (name, description, category, conditions, severity, 
                 threshold_count, threshold_window, cooldown_period, enabled, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rule.name,
                    rule.description,
                    rule.category.value,
                    json.dumps(rule.conditions),
                    rule.severity.value,
                    rule.threshold_count,
                    rule.threshold_window,
                    rule.cooldown_period,
                    rule.enabled,
                    json.dumps(rule.metadata) if rule.metadata else None,
                ),
            )

            conn.commit()

            # Add to in-memory rules
            self.rules[rule.name] = rule

            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def update_rule(self, rule_name: str, updates: Dict) -> bool:
        """Update alert rule.

        Args:
            rule_name: Rule name
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build update query
        fields = []
        values = []

        for key, value in updates.items():
            fields.append(f"{key} = ?")
            if key == "conditions":
                values.append(json.dumps(value))
            elif key == "metadata":
                values.append(json.dumps(value) if value else None)
            elif key in ["category", "severity"]:
                values.append(value.value if isinstance(value, Enum) else value)
            else:
                values.append(value)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(rule_name)

        query = f"UPDATE alert_rules SET {', '.join(fields)} WHERE name = ?"

        cursor.execute(query, values)
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        # Reload rules
        if success:
            self._load_rules()

        return success

    def delete_rule(self, rule_name: str) -> bool:
        """Delete alert rule.

        Args:
            rule_name: Rule name

        Returns:
            True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM alert_rules WHERE name = ?", (rule_name,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()

        # Remove from in-memory rules
        if success and rule_name in self.rules:
            del self.rules[rule_name]

        return success

    def evaluate(self, data: Dict[str, Any]) -> List[Alert]:
        """Evaluate data against all rules.

        Args:
            data: Data to evaluate

        Returns:
            List of triggered alerts
        """
        alerts = []

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            # Check if in cooldown
            if self._in_cooldown(rule_name):
                continue

            # Check if suppressed
            if self._is_suppressed(rule):
                continue

            # Evaluate rule
            if rule.evaluate(data):
                # Check threshold
                if self._check_threshold(rule_name, rule):
                    alert = self._create_alert(rule, data)
                    alerts.append(alert)
                    self._trigger_alert(alert)

        return alerts

    def _create_alert(self, rule: AlertRule, data: Dict) -> Alert:
        """Create alert from rule and data.

        Args:
            rule: Alert rule
            data: Trigger data

        Returns:
            Alert instance
        """
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            category=rule.category,
            title=f"{rule.name}: {rule.description}",
            message=self._format_message(rule, data),
            source=data.get("source", "system"),
            data=data,
            metadata=rule.metadata,
            created_at=datetime.now(),
        )

        return alert

    def _format_message(self, rule: AlertRule, data: Dict) -> str:
        """Format alert message.

        Args:
            rule: Alert rule
            data: Trigger data

        Returns:
            Formatted message
        """
        message = rule.description

        # Replace placeholders with data values
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in message:
                message = message.replace(placeholder, str(value))

        return message

    def _trigger_alert(self, alert: Alert):
        """Trigger alert and notify callbacks.

        Args:
            alert: Alert to trigger
        """
        # Generate alert ID
        alert_id = self._generate_alert_id()

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO alerts 
            (alert_id, rule_name, severity, category, title, message, 
             source, status, data, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                alert_id,
                alert.rule_name,
                alert.severity.value,
                alert.category.value,
                alert.title,
                alert.message,
                alert.source,
                alert.status.value,
                json.dumps(alert.data) if alert.data else None,
                json.dumps(alert.metadata) if alert.metadata else None,
            ),
        )

        # Add to history
        cursor.execute(
            """
            INSERT INTO alert_history (alert_id, event_type, details)
            VALUES (?, 'triggered', ?)
        """,
            (alert_id, f"Alert triggered: {alert.message}"),
        )

        conn.commit()
        conn.close()

        # Store in memory
        self.active_alerts[alert_id] = alert

        # Trigger callbacks
        self._notify_callbacks(alert)

        # Check escalation
        self._check_escalation(alert)

    def acknowledge_alert(self, alert_id: str, user: str, notes: Optional[str] = None) -> bool:
        """Acknowledge alert.

        Args:
            alert_id: Alert ID
            user: User acknowledging
            notes: Optional notes

        Returns:
            True if acknowledged successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE alerts 
            SET status = 'acknowledged', 
                acknowledged_at = CURRENT_TIMESTAMP,
                acknowledged_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE alert_id = ? AND status = 'active'
        """,
            (user, alert_id),
        )

        success = cursor.rowcount > 0

        if success:
            # Add to history
            cursor.execute(
                """
                INSERT INTO alert_history (alert_id, event_type, user, details)
                VALUES (?, 'acknowledged', ?, ?)
            """,
                (alert_id, user, notes),
            )

            # Update in-memory alert
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
                self.active_alerts[alert_id].acknowledged_at = datetime.now()
                self.active_alerts[alert_id].acknowledged_by = user

        conn.commit()
        conn.close()

        return success

    def resolve_alert(self, alert_id: str, user: str, resolution: Optional[str] = None) -> bool:
        """Resolve alert.

        Args:
            alert_id: Alert ID
            user: User resolving
            resolution: Resolution details

        Returns:
            True if resolved successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE alerts 
            SET status = 'resolved', 
                resolved_at = CURRENT_TIMESTAMP,
                resolved_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE alert_id = ?
        """,
            (user, alert_id),
        )

        success = cursor.rowcount > 0

        if success:
            # Add to history
            cursor.execute(
                """
                INSERT INTO alert_history (alert_id, event_type, user, details)
                VALUES (?, 'resolved', ?, ?)
            """,
                (alert_id, user, resolution),
            )

            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]

        conn.commit()
        conn.close()

        return success

    def create_suppression(
        self,
        rule_pattern: Optional[str] = None,
        source_pattern: Optional[str] = None,
        category: Optional[AlertCategory] = None,
        severity_range: Optional[Tuple[AlertSeverity, AlertSeverity]] = None,
        duration_hours: int = 24,
        reason: str = "",
        created_by: str = "system",
    ) -> bool:
        """Create alert suppression.

        Args:
            rule_pattern: Rule name pattern
            source_pattern: Source pattern
            category: Alert category
            severity_range: Severity range to suppress
            duration_hours: Suppression duration
            reason: Suppression reason
            created_by: User creating suppression

        Returns:
            True if created successfully
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO alert_suppressions 
            (rule_pattern, source_pattern, category, severity_min, severity_max,
             start_time, end_time, reason, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                rule_pattern,
                source_pattern,
                category.value if category else None,
                severity_range[0].value if severity_range else None,
                severity_range[1].value if severity_range else None,
                start_time,
                end_time,
                reason,
                created_by,
            ),
        )

        conn.commit()
        conn.close()

        return True

    def get_active_alerts(
        self,
        category: Optional[AlertCategory] = None,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Dict]:
        """Get active alerts.

        Args:
            category: Filter by category
            severity: Filter by severity

        Returns:
            List of active alerts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT alert_id, rule_name, severity, category, title, message,
                   source, status, data, created_at, acknowledged_at, acknowledged_by
            FROM alerts
            WHERE status IN ('active', 'acknowledged')
        """
        params = []

        if category:
            query += " AND category = ?"
            params.append(category.value)

        if severity:
            query += " AND severity >= ?"
            params.append(severity.value)

        query += " ORDER BY severity DESC, created_at DESC"

        cursor.execute(query, params)

        alerts = []
        for row in cursor.fetchall():
            alerts.append(
                {
                    "alert_id": row[0],
                    "rule_name": row[1],
                    "severity": row[2],
                    "category": row[3],
                    "title": row[4],
                    "message": row[5],
                    "source": row[6],
                    "status": row[7],
                    "data": json.loads(row[8]) if row[8] else None,
                    "created_at": row[9],
                    "acknowledged_at": row[10],
                    "acknowledged_by": row[11],
                }
            )

        conn.close()
        return alerts

    def get_alert_history(self, alert_id: str) -> List[Dict]:
        """Get alert history.

        Args:
            alert_id: Alert ID

        Returns:
            Alert history events
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT event_type, user, details, timestamp
            FROM alert_history
            WHERE alert_id = ?
            ORDER BY timestamp DESC
        """,
            (alert_id,),
        )

        history = []
        for row in cursor.fetchall():
            history.append(
                {
                    "event_type": row[0],
                    "user": row[1],
                    "details": row[2],
                    "timestamp": row[3],
                }
            )

        conn.close()
        return history

    def get_metrics(
        self,
        rule_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """Get alert metrics.

        Args:
            rule_name: Filter by rule
            start_date: Start date
            end_date: End date

        Returns:
            Alert metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query
        query = "SELECT COUNT(*), AVG(severity), MAX(severity) FROM alerts WHERE 1=1"
        params = []

        if rule_name:
            query += " AND rule_name = ?"
            params.append(rule_name)

        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)

        cursor.execute(query, params)
        count, avg_severity, max_severity = cursor.fetchone()

        # Get resolution times
        cursor.execute(
            """
            SELECT AVG(julianday(resolved_at) - julianday(created_at)) * 24 * 60
            FROM alerts
            WHERE resolved_at IS NOT NULL
        """
            + (" AND rule_name = ?" if rule_name else ""),
            [rule_name] if rule_name else [],
        )

        avg_resolution_time = cursor.fetchone()[0]

        conn.close()

        return {
            "total_alerts": count or 0,
            "average_severity": avg_severity or 0,
            "max_severity": max_severity or 0,
            "average_resolution_time_minutes": avg_resolution_time or 0,
        }

    def register_callback(self, callback: Callable, severity: Optional[AlertSeverity] = None):
        """Register alert callback.

        Args:
            callback: Callback function
            severity: Minimum severity to trigger callback
        """
        self.callbacks[severity or "all"].append(callback)

    def _load_rules(self):
        """Load rules from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name, description, category, conditions, severity,
                   threshold_count, threshold_window, cooldown_period, enabled, metadata
            FROM alert_rules
            WHERE enabled = 1
        """
        )

        self.rules = {}
        for row in cursor.fetchall():
            rule = AlertRule(
                name=row[0],
                description=row[1],
                category=AlertCategory(row[2]),
                conditions=json.loads(row[3]),
                severity=AlertSeverity(row[4]),
                threshold_count=row[5],
                threshold_window=row[6],
                cooldown_period=row[7],
                enabled=bool(row[8]),
                metadata=json.loads(row[9]) if row[9] else None,
            )
            self.rules[rule.name] = rule

        conn.close()

    def _in_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown.

        Args:
            rule_name: Rule name

        Returns:
            True if in cooldown
        """
        if rule_name not in self.alert_history:
            return False

        rule = self.rules[rule_name]
        last_alert_time = self.alert_history[rule_name][-1]

        return (datetime.now() - last_alert_time).total_seconds() < rule.cooldown_period

    def _is_suppressed(self, rule: AlertRule) -> bool:
        """Check if alert is suppressed.

        Args:
            rule: Alert rule

        Returns:
            True if suppressed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM alert_suppressions
            WHERE (rule_pattern IS NULL OR ? LIKE rule_pattern)
            AND (category IS NULL OR category = ?)
            AND (severity_min IS NULL OR ? >= severity_min)
            AND (severity_max IS NULL OR ? <= severity_max)
            AND start_time <= CURRENT_TIMESTAMP
            AND end_time >= CURRENT_TIMESTAMP
        """,
            (rule.name, rule.category.value, rule.severity.value, rule.severity.value),
        )

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    def _check_threshold(self, rule_name: str, rule: AlertRule) -> bool:
        """Check if threshold is met.

        Args:
            rule_name: Rule name
            rule: Alert rule

        Returns:
            True if threshold is met
        """
        # Track rule triggers
        now = datetime.now()

        if rule_name not in self.alert_history:
            self.alert_history[rule_name] = []

        # Clean old entries
        cutoff = now - timedelta(seconds=rule.threshold_window)
        self.alert_history[rule_name] = [t for t in self.alert_history[rule_name] if t > cutoff]

        # Add current trigger
        self.alert_history[rule_name].append(now)

        # Check threshold
        return len(self.alert_history[rule_name]) >= rule.threshold_count

    def _check_escalation(self, alert: Alert):
        """Check and handle alert escalation.

        Args:
            alert: Alert to check
        """
        # TODO: Implement escalation policies
        pass

    def _notify_callbacks(self, alert: Alert):
        """Notify registered callbacks.

        Args:
            alert: Alert to notify about
        """
        # Notify severity-specific callbacks
        for callback in self.callbacks.get(alert.severity, []):
            try:
                callback(alert)
            except Exception:
                pass

        # Notify general callbacks
        for callback in self.callbacks.get("all", []):
            try:
                callback(alert)
            except Exception:
                pass

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID.

        Returns:
            Alert ID
        """
        import hashlib

        timestamp = datetime.now().isoformat()
        random_part = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"ALT-{timestamp[:10]}-{random_part}"
