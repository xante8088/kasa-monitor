"""
Database models for Kasa Monitor using SQLAlchemy
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Table,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()

# Association tables for many-to-many relationships
user_device_permissions = Table(
    "user_device_permissions",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("device_id", Integer, ForeignKey("devices.id", ondelete="CASCADE")),
    Column("permission_level", String(20), default="read"),
    Column("created_at", DateTime, default=func.now()),
    UniqueConstraint("user_id", "device_id", name="uq_user_device"),
)

device_groups = Table(
    "device_groups",
    Base.metadata,
    Column("device_id", Integer, ForeignKey("devices.id", ondelete="CASCADE")),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE")),
    Column("created_at", DateTime, default=func.now()),
    UniqueConstraint("device_id", "group_id", name="uq_device_group"),
)


class User(Base):
    """User model with authentication and permissions"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # 2FA fields
    totp_secret = Column(String(100), nullable=True)
    two_factor_enabled = Column(Boolean, default=False)
    backup_codes = Column(JSON, nullable=True)

    # Session management
    last_login = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    session_count = Column(Integer, default=0)

    # Password policy
    password_changed_at = Column(DateTime, default=func.now())
    password_expires_at = Column(DateTime, nullable=True)
    password_history = Column(JSON, nullable=True)
    force_password_change = Column(Boolean, default=False)

    # Access control
    allowed_ips = Column(JSON, nullable=True)  # List of allowed IP addresses/ranges
    access_schedule = Column(JSON, nullable=True)  # Time-based access rules

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    devices = relationship(
        "Device", secondary=user_device_permissions, back_populates="users"
    )
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )

    @validates("email")
    def validate_email(self, key, email):
        if "@" not in email:
            raise ValueError("Invalid email address")
        return email.lower()


class Device(Base):
    """Kasa smart device model"""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    alias = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=False, index=True)
    mac_address = Column(String(17), nullable=True)
    model = Column(String(50), nullable=True)
    device_type = Column(String(30), nullable=True)
    hardware_version = Column(String(20), nullable=True)
    firmware_version = Column(String(20), nullable=True)

    # Status fields
    is_online = Column(Boolean, default=False, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime, nullable=True)
    last_state_change = Column(DateTime, nullable=True)

    # Power monitoring
    supports_power_monitoring = Column(Boolean, default=False)
    current_power = Column(Float, nullable=True)
    today_energy = Column(Float, nullable=True)
    month_energy = Column(Float, nullable=True)

    # Configuration
    config = Column(JSON, nullable=True)
    calibration_factor = Column(Float, default=1.0)

    # Metadata
    discovered_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship(
        "User", secondary=user_device_permissions, back_populates="devices"
    )
    groups = relationship("Group", secondary=device_groups, back_populates="devices")
    energy_readings = relationship(
        "EnergyReading", back_populates="device", cascade="all, delete-orphan"
    )
    schedules = relationship(
        "Schedule", back_populates="device", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "Alert", back_populates="device", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_device_status", "is_online", "is_enabled"),
        CheckConstraint("current_power >= 0", name="check_positive_power"),
    )


class Group(Base):
    """Device grouping for bulk operations"""

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    group_type = Column(String(30), default="manual")  # manual, dynamic, location

    # Dynamic group criteria
    criteria = Column(JSON, nullable=True)  # For dynamic groups

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    devices = relationship("Device", secondary=device_groups, back_populates="groups")
    children = relationship("Group", backref="parent", remote_side=[id])


class EnergyReading(Base):
    """Energy consumption readings"""

    __tablename__ = "energy_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Power metrics
    power = Column(Float, nullable=True)  # Current power in watts
    voltage = Column(Float, nullable=True)
    current = Column(Float, nullable=True)
    power_factor = Column(Float, nullable=True)

    # Energy metrics
    energy = Column(Float, nullable=True)  # Energy in kWh
    total_energy = Column(Float, nullable=True)

    # Quality metrics
    frequency = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)

    # Relationships
    device = relationship("Device", back_populates="energy_readings")

    __table_args__ = (
        Index("idx_energy_device_time", "device_id", "timestamp"),
        Index("idx_energy_timestamp", "timestamp"),
    )


class EnergyAggregation(Base):
    """Aggregated energy data for reporting"""

    __tablename__ = "energy_aggregations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    aggregation_type = Column(String(20), nullable=False)  # hourly, daily, monthly
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # Aggregated metrics
    avg_power = Column(Float, nullable=True)
    min_power = Column(Float, nullable=True)
    max_power = Column(Float, nullable=True)
    total_energy = Column(Float, nullable=True)

    # Statistical metrics
    std_dev = Column(Float, nullable=True)
    sample_count = Column(Integer, default=0)
    uptime_seconds = Column(Integer, nullable=True)

    # Cost metrics
    energy_cost = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index(
            "idx_aggregation_lookup", "device_id", "aggregation_type", "period_start"
        ),
        UniqueConstraint(
            "device_id", "aggregation_type", "period_start", name="uq_aggregation"
        ),
    )


class Schedule(Base):
    """Device scheduling rules"""

    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Schedule configuration
    schedule_type = Column(String(30), nullable=False)  # time, sunrise, sunset, custom
    cron_expression = Column(String(100), nullable=True)
    time_value = Column(String(10), nullable=True)
    days_of_week = Column(JSON, nullable=True)

    # Actions
    action = Column(String(20), nullable=False)  # on, off, toggle, scene
    action_data = Column(JSON, nullable=True)

    # Advanced options
    random_delay_minutes = Column(Integer, default=0)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    holiday_mode = Column(String(20), nullable=True)  # skip, only, normal

    # Metadata
    last_triggered = Column(DateTime, nullable=True)
    next_trigger = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    device = relationship("Device", back_populates="schedules")

    __table_args__ = (Index("idx_schedule_active", "is_active", "next_trigger"),)


class Alert(Base):
    """Alert configurations and history"""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=True
    )
    alert_type = Column(String(30), nullable=False)  # threshold, offline, error, custom
    severity = Column(String(20), nullable=False)  # info, warning, error, critical
    is_active = Column(Boolean, default=True, nullable=False)

    # Alert configuration
    condition = Column(JSON, nullable=False)  # Alert trigger conditions
    threshold_value = Column(Float, nullable=True)
    threshold_type = Column(String(20), nullable=True)  # above, below, equals, change

    # Alert state
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Notification settings
    notification_channels = Column(JSON, nullable=True)  # email, webhook, websocket
    notification_sent = Column(Boolean, default=False)
    escalation_level = Column(Integer, default=0)

    # Metadata
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    device = relationship("Device", back_populates="alerts")

    __table_args__ = (
        Index("idx_alert_active", "is_active", "is_triggered"),
        Index("idx_alert_device", "device_id", "alert_type"),
    )


class APIKey(Base):
    """API key authentication"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)

    # Permissions
    scopes = Column(JSON, nullable=True)  # List of allowed scopes
    device_ids = Column(JSON, nullable=True)  # Specific device access

    # Validity
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)

    # Rate limiting
    rate_limit = Column(Integer, nullable=True)  # Requests per minute
    rate_limit_remaining = Column(Integer, nullable=True)
    rate_limit_reset = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    rotated_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("idx_api_key_active", "is_active", "expires_at"),)


class AuditLog(Base):
    """Comprehensive audit logging"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)

    # Request details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(255), nullable=True)

    # Result
    status = Column(String(20), nullable=False)  # success, failure, error
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Additional data
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "timestamp"),
        Index("idx_audit_action", "action", "status"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )


class UserSession(Base):
    """User session management"""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_token = Column(String(255), unique=True, nullable=False, index=True)

    # Session details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    device_info = Column(JSON, nullable=True)

    # Validity
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=func.now())
    terminated_at = Column(DateTime, nullable=True)

    # Security
    refresh_token = Column(String(255), nullable=True)
    refresh_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_session_active", "is_active", "expires_at"),
        Index("idx_session_user", "user_id", "is_active"),
    )


class SystemConfig(Base):
    """System configuration storage"""

    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True)
    value_type = Column(String(20), nullable=False)  # string, int, float, bool, json
    category = Column(String(50), nullable=True, index=True)

    # Metadata
    description = Column(Text, nullable=True)
    is_sensitive = Column(Boolean, default=False)
    is_readonly = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class BackupMetadata(Base):
    """Database backup tracking"""

    __tablename__ = "backup_metadata"

    id = Column(Integer, primary_key=True, index=True)
    backup_name = Column(String(200), unique=True, nullable=False)
    backup_type = Column(String(30), nullable=False)  # manual, scheduled, auto

    # Backup details
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False)

    # Status
    status = Column(String(20), nullable=False)  # completed, failed, corrupted
    is_encrypted = Column(Boolean, default=False)
    is_compressed = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    description = Column(Text, nullable=True)
    retention_days = Column(Integer, default=30)

    __table_args__ = (
        Index("idx_backup_created", "created_at"),
        Index("idx_backup_type", "backup_type", "status"),
    )


# Create indexes for better query performance
Index("idx_user_login", User.username, User.is_active)
Index("idx_device_discovery", Device.ip_address, Device.is_online)
Index("idx_energy_recent", EnergyReading.timestamp.desc())
