"""Comprehensive audit logging system.

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
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import logging
from pathlib import Path
import csv
import gzip


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password_change"
    PASSWORD_RESET = "auth.password_reset"
    MFA_ENABLED = "auth.mfa_enabled"
    MFA_DISABLED = "auth.mfa_disabled"
    
    # User management
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role_changed"
    USER_PERMISSIONS_CHANGED = "user.permissions_changed"
    USER_LOCKED = "user.locked"
    USER_UNLOCKED = "user.unlocked"
    
    # Device management
    DEVICE_ADDED = "device.added"
    DEVICE_REMOVED = "device.removed"
    DEVICE_UPDATED = "device.updated"
    DEVICE_CONTROLLED = "device.controlled"
    DEVICE_DISCOVERED = "device.discovered"
    
    # System events
    SYSTEM_CONFIG_CHANGED = "system.config_changed"
    SYSTEM_BACKUP_CREATED = "system.backup_created"
    SYSTEM_BACKUP_RESTORED = "system.backup_restored"
    SYSTEM_UPDATE = "system.update"
    SYSTEM_ERROR = "system.error"
    
    # Data access
    DATA_EXPORTED = "data.exported"
    DATA_IMPORTED = "data.imported"
    DATA_VIEWED = "data.viewed"
    DATA_DELETED = "data.deleted"
    
    # Security events
    SECURITY_VIOLATION = "security.violation"
    PERMISSION_DENIED = "security.permission_denied"
    RATE_LIMIT_EXCEEDED = "security.rate_limit"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    IP_BLOCKED = "security.ip_blocked"
    
    # API events
    API_KEY_CREATED = "api.key_created"
    API_KEY_REVOKED = "api.key_revoked"
    API_REQUEST = "api.request"
    API_ERROR = "api.error"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[int]
    username: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    details: Dict[str, Any]
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class AuditLogger:
    """Main audit logging system."""
    
    def __init__(self, 
                 db_path: str = "kasa_monitor.db",
                 log_dir: str = "/var/log/kasa_monitor/audit",
                 enable_file_logging: bool = True,
                 enable_compression: bool = True,
                 retention_days: int = 90):
        """Initialize audit logger.
        
        Args:
            db_path: Path to database
            log_dir: Directory for audit log files
            enable_file_logging: Enable file-based logging
            enable_compression: Compress old log files
            retention_days: Days to retain logs
        """
        self.db_path = db_path
        self.log_dir = Path(log_dir)
        self.enable_file_logging = enable_file_logging
        self.enable_compression = enable_compression
        self.retention_days = retention_days
        
        if enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self._setup_file_logger()
    
    def _init_database(self):
        """Initialize audit log tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id INTEGER,
                username TEXT,
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT NOT NULL,
                details TEXT,
                success BOOLEAN,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum TEXT
            )
        """)
        
        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON audit_log(timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user 
            ON audit_log(user_id, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event_type 
            ON audit_log(event_type, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_severity 
            ON audit_log(severity, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_resource 
            ON audit_log(resource_type, resource_id)
        """)
        
        # Audit log retention policy
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_retention (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type_pattern TEXT,
                retention_days INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audit log analysis cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_analysis_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_type TEXT,
                parameters TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _setup_file_logger(self):
        """Setup file-based audit logger."""
        if not self.enable_file_logging:
            self.file_logger = None
            return
        
        # Configure Python logging
        self.file_logger = logging.getLogger('audit')
        self.file_logger.setLevel(logging.INFO)
        
        # Create rotating file handler
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file)
        
        # Set format
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        self.file_logger.addHandler(handler)
    
    def log_event(self, event: AuditEvent):
        """Log an audit event.
        
        Args:
            event: Audit event to log
        """
        # Calculate checksum for integrity
        checksum = self._calculate_checksum(event)
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_log 
            (event_type, severity, user_id, username, ip_address, user_agent,
             session_id, resource_type, resource_id, action, details, success,
             error_message, timestamp, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_type.value,
            event.severity.value,
            event.user_id,
            event.username,
            event.ip_address,
            event.user_agent,
            event.session_id,
            event.resource_type,
            event.resource_id,
            event.action,
            json.dumps(event.details),
            event.success,
            event.error_message,
            event.timestamp,
            checksum
        ))
        
        conn.commit()
        conn.close()
        
        # Log to file if enabled
        if self.file_logger:
            log_message = self._format_log_message(event)
            
            if event.severity == AuditSeverity.DEBUG:
                self.file_logger.debug(log_message)
            elif event.severity == AuditSeverity.INFO:
                self.file_logger.info(log_message)
            elif event.severity == AuditSeverity.WARNING:
                self.file_logger.warning(log_message)
            elif event.severity == AuditSeverity.ERROR:
                self.file_logger.error(log_message)
            elif event.severity == AuditSeverity.CRITICAL:
                self.file_logger.critical(log_message)
    
    async def log_event_async(self, event: AuditEvent):
        """Log an audit event asynchronously.
        
        Args:
            event: Audit event to log
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.log_event, event)
    
    def log_login(self, user_id: int, username: str, ip_address: str, 
                  success: bool, error_message: Optional[str] = None):
        """Log login attempt.
        
        Args:
            user_id: User ID
            username: Username
            ip_address: IP address
            success: Whether login was successful
            error_message: Error message if failed
        """
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id if success else None,
            username=username,
            ip_address=ip_address,
            user_agent=None,
            session_id=None,
            resource_type="authentication",
            resource_id=str(user_id) if user_id else None,
            action="login",
            details={"username": username},
            timestamp=datetime.now(),
            success=success,
            error_message=error_message
        )
        self.log_event(event)
    
    def log_data_access(self, user_id: int, resource_type: str, 
                       resource_id: str, action: str, details: Optional[Dict] = None):
        """Log data access event.
        
        Args:
            user_id: User ID
            resource_type: Type of resource
            resource_id: Resource identifier
            action: Action performed
            details: Additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.DATA_VIEWED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=None,
            ip_address=None,
            user_agent=None,
            session_id=None,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            timestamp=datetime.now(),
            success=True
        )
        self.log_event(event)
    
    def log_security_event(self, event_type: AuditEventType, ip_address: str,
                          details: Dict, severity: AuditSeverity = AuditSeverity.WARNING):
        """Log security event.
        
        Args:
            event_type: Type of security event
            ip_address: IP address
            details: Event details
            severity: Event severity
        """
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=None,
            username=None,
            ip_address=ip_address,
            user_agent=None,
            session_id=None,
            resource_type="security",
            resource_id=None,
            action="security_event",
            details=details,
            timestamp=datetime.now(),
            success=False
        )
        self.log_event(event)
    
    def query_logs(self,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  user_id: Optional[int] = None,
                  event_type: Optional[AuditEventType] = None,
                  severity: Optional[AuditSeverity] = None,
                  resource_type: Optional[str] = None,
                  limit: int = 100) -> List[Dict]:
        """Query audit logs.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            user_id: User ID filter
            event_type: Event type filter
            severity: Severity filter
            resource_type: Resource type filter
            limit: Maximum results
            
        Returns:
            List of audit log entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'id': row[0],
                'event_type': row[1],
                'severity': row[2],
                'user_id': row[3],
                'username': row[4],
                'ip_address': row[5],
                'user_agent': row[6],
                'session_id': row[7],
                'resource_type': row[8],
                'resource_id': row[9],
                'action': row[10],
                'details': json.loads(row[11]) if row[11] else {},
                'success': bool(row[12]),
                'error_message': row[13],
                'timestamp': row[14],
                'checksum': row[15]
            })
        
        conn.close()
        return logs
    
    def get_user_activity(self, user_id: int, days: int = 7) -> List[Dict]:
        """Get user activity summary.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            User activity summary
        """
        start_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get activity counts by type
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM audit_log
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY event_type
            ORDER BY count DESC
        """, (user_id, start_date))
        
        activity_counts = {}
        for event_type, count in cursor.fetchall():
            activity_counts[event_type] = count
        
        # Get recent activities
        cursor.execute("""
            SELECT event_type, action, resource_type, resource_id, timestamp
            FROM audit_log
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (user_id, start_date))
        
        recent_activities = []
        for row in cursor.fetchall():
            recent_activities.append({
                'event_type': row[0],
                'action': row[1],
                'resource_type': row[2],
                'resource_id': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        
        return {
            'activity_counts': activity_counts,
            'recent_activities': recent_activities
        }
    
    def generate_compliance_report(self, 
                                  start_date: datetime,
                                  end_date: datetime,
                                  output_format: str = 'json') -> Union[Dict, str]:
        """Generate compliance report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            output_format: Output format (json, csv)
            
        Returns:
            Compliance report data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get summary statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_events,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT ip_address) as unique_ips,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_events,
                COUNT(DISTINCT DATE(timestamp)) as active_days
            FROM audit_log
            WHERE timestamp BETWEEN ? AND ?
        """, (start_date, end_date))
        
        stats = cursor.fetchone()
        
        # Get events by type
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM audit_log
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY event_type
            ORDER BY count DESC
        """, (start_date, end_date))
        
        events_by_type = {}
        for event_type, count in cursor.fetchall():
            events_by_type[event_type] = count
        
        # Get security events
        cursor.execute("""
            SELECT event_type, severity, COUNT(*) as count
            FROM audit_log
            WHERE timestamp BETWEEN ? AND ?
            AND event_type LIKE 'security.%'
            GROUP BY event_type, severity
        """, (start_date, end_date))
        
        security_events = []
        for row in cursor.fetchall():
            security_events.append({
                'event_type': row[0],
                'severity': row[1],
                'count': row[2]
            })
        
        conn.close()
        
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_events': stats[0],
                'unique_users': stats[1],
                'unique_ips': stats[2],
                'failed_events': stats[3],
                'active_days': stats[4]
            },
            'events_by_type': events_by_type,
            'security_events': security_events
        }
        
        if output_format == 'csv':
            return self._report_to_csv(report)
        
        return report
    
    def export_logs(self, 
                   start_date: datetime,
                   end_date: datetime,
                   output_file: str):
        """Export audit logs to file.
        
        Args:
            start_date: Start date
            end_date: End date
            output_file: Output file path
        """
        logs = self.query_logs(start_date=start_date, end_date=end_date, limit=1000000)
        
        output_path = Path(output_file)
        
        if output_path.suffix == '.csv':
            self._export_to_csv(logs, output_path)
        elif output_path.suffix == '.json':
            self._export_to_json(logs, output_path)
        else:
            # Default to JSON
            self._export_to_json(logs, output_path)
        
        # Compress if enabled
        if self.enable_compression:
            self._compress_file(output_path)
    
    def cleanup_old_logs(self):
        """Clean up old audit logs based on retention policy."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get retention policies
        cursor.execute("""
            SELECT event_type_pattern, retention_days
            FROM audit_retention
        """)
        
        policies = cursor.fetchall()
        
        # Apply default retention if no specific policies
        if not policies:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cursor.execute("""
                DELETE FROM audit_log WHERE timestamp < ?
            """, (cutoff_date,))
        else:
            # Apply specific retention policies
            for pattern, retention_days in policies:
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                cursor.execute("""
                    DELETE FROM audit_log 
                    WHERE timestamp < ? AND event_type LIKE ?
                """, (cutoff_date, pattern))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        # Clean up old file logs
        if self.enable_file_logging:
            self._cleanup_file_logs()
        
        return deleted
    
    def verify_integrity(self, start_date: Optional[datetime] = None) -> List[int]:
        """Verify audit log integrity.
        
        Args:
            start_date: Start date for verification
            
        Returns:
            List of compromised log IDs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_log"
        params = []
        
        if start_date:
            query += " WHERE timestamp >= ?"
            params.append(start_date)
        
        cursor.execute(query, params)
        
        compromised = []
        for row in cursor.fetchall():
            # Recreate event from row
            event_data = {
                'event_type': row[1],
                'severity': row[2],
                'user_id': row[3],
                'username': row[4],
                'action': row[10],
                'timestamp': row[14]
            }
            
            # Calculate expected checksum
            expected_checksum = hashlib.sha256(
                json.dumps(event_data, sort_keys=True).encode()
            ).hexdigest()
            
            # Compare with stored checksum
            if row[15] != expected_checksum:
                compromised.append(row[0])
        
        conn.close()
        return compromised
    
    def _calculate_checksum(self, event: AuditEvent) -> str:
        """Calculate checksum for audit event.
        
        Args:
            event: Audit event
            
        Returns:
            Checksum string
        """
        # Create deterministic string from event
        event_data = {
            'event_type': event.event_type.value,
            'severity': event.severity.value,
            'user_id': event.user_id,
            'username': event.username,
            'action': event.action,
            'timestamp': event.timestamp.isoformat()
        }
        
        return hashlib.sha256(
            json.dumps(event_data, sort_keys=True).encode()
        ).hexdigest()
    
    def _format_log_message(self, event: AuditEvent) -> str:
        """Format audit event for file logging.
        
        Args:
            event: Audit event
            
        Returns:
            Formatted log message
        """
        parts = [
            f"[{event.event_type.value}]",
            f"User: {event.username or event.user_id or 'anonymous'}",
            f"IP: {event.ip_address or 'unknown'}",
            f"Action: {event.action}"
        ]
        
        if event.resource_type:
            parts.append(f"Resource: {event.resource_type}/{event.resource_id}")
        
        if not event.success:
            parts.append(f"FAILED: {event.error_message}")
        
        return " | ".join(parts)
    
    def _export_to_csv(self, logs: List[Dict], output_path: Path):
        """Export logs to CSV file.
        
        Args:
            logs: Log entries
            output_path: Output file path
        """
        if not logs:
            return
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = logs[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for log in logs:
                # Convert complex fields to strings
                log_copy = log.copy()
                if 'details' in log_copy:
                    log_copy['details'] = json.dumps(log_copy['details'])
                writer.writerow(log_copy)
    
    def _export_to_json(self, logs: List[Dict], output_path: Path):
        """Export logs to JSON file.
        
        Args:
            logs: Log entries
            output_path: Output file path
        """
        with open(output_path, 'w') as f:
            json.dump(logs, f, indent=2, default=str)
    
    def _compress_file(self, file_path: Path):
        """Compress a file using gzip.
        
        Args:
            file_path: File to compress
        """
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                f_out.writelines(f_in)
        
        # Remove original file
        file_path.unlink()
    
    def _cleanup_file_logs(self):
        """Clean up old file logs."""
        if not self.log_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in self.log_dir.glob("audit_*.log*"):
            # Try to parse date from filename
            try:
                date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < cutoff_date:
                    log_file.unlink()
            except (IndexError, ValueError):
                continue
    
    def _report_to_csv(self, report: Dict) -> str:
        """Convert report to CSV format.
        
        Args:
            report: Report data
            
        Returns:
            CSV string
        """
        import io
        
        output = io.StringIO()
        
        # Write summary section
        output.write("Compliance Report\n")
        output.write(f"Period: {report['period']['start']} to {report['period']['end']}\n")
        output.write("\nSummary\n")
        
        for key, value in report['summary'].items():
            output.write(f"{key},{value}\n")
        
        output.write("\nEvents by Type\n")
        for event_type, count in report['events_by_type'].items():
            output.write(f"{event_type},{count}\n")
        
        output.write("\nSecurity Events\n")
        output.write("Event Type,Severity,Count\n")
        for event in report['security_events']:
            output.write(f"{event['event_type']},{event['severity']},{event['count']}\n")
        
        return output.getvalue()