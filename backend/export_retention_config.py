"""Export retention configuration management.

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

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from audit_logging import AuditEvent, AuditEventType, AuditLogger, AuditSeverity

logger = logging.getLogger(__name__)


class ExportRetentionConfig:
    """Configuration manager for export retention policies."""

    def __init__(self, db_path: str = "kasa_monitor.db", audit_logger: Optional[AuditLogger] = None):
        """Initialize configuration manager.
        
        Args:
            db_path: Path to the database
            audit_logger: Audit logging instance
        """
        self.db_path = db_path
        self.audit_logger = audit_logger or AuditLogger(db_path=db_path)
        
        # Initialize configuration schema
        self._init_config_schema()
        
        # Load default configuration
        self._load_default_config()
        
        logger.info("Export retention configuration manager initialized")

    def _init_config_schema(self):
        """Initialize configuration schema in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if system_config table exists, create if not
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    value_type TEXT NOT NULL DEFAULT 'string',
                    category TEXT,
                    description TEXT,
                    is_sensitive BOOLEAN DEFAULT 0,
                    is_readonly BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER,
                    FOREIGN KEY (updated_by) REFERENCES users(id)
                )
            """)
            
            # Create index for configuration lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_config_key 
                ON system_config(key)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_config_category 
                ON system_config(category)
            """)
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error initializing configuration schema: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _load_default_config(self):
        """Load default configuration values."""
        default_configs = [
            # Export retention settings
            {
                "key": "export.retention.enabled",
                "value": "true",
                "value_type": "boolean",
                "category": "export_retention",
                "description": "Enable export retention policies and cleanup",
            },
            {
                "key": "export.retention.default_days",
                "value": "30",
                "value_type": "integer",
                "category": "export_retention",
                "description": "Default retention period for exports in days",
            },
            {
                "key": "export.retention.csv_days",
                "value": "7",
                "value_type": "integer",
                "category": "export_retention",
                "description": "Retention period for CSV exports in days",
            },
            {
                "key": "export.retention.excel_days",
                "value": "14",
                "value_type": "integer",
                "category": "export_retention",
                "description": "Retention period for Excel exports in days",
            },
            {
                "key": "export.retention.json_days",
                "value": "30",
                "value_type": "integer",
                "category": "export_retention",
                "description": "Retention period for JSON exports in days",
            },
            {
                "key": "export.retention.sqlite_days",
                "value": "90",
                "value_type": "integer",
                "category": "export_retention",
                "description": "Retention period for SQLite exports in days",
            },
            {
                "key": "export.retention.large_export_days",
                "value": "3",
                "value_type": "integer",
                "category": "export_retention",
                "description": "Retention period for large exports (>100MB) in days",
            },
            # Scheduler settings
            {
                "key": "export.cleanup.hour",
                "value": "2",
                "value_type": "integer",
                "category": "export_cleanup",
                "description": "Hour of day to run daily cleanup (0-23)",
            },
            {
                "key": "export.cleanup.check_interval_minutes",
                "value": "60",
                "value_type": "integer",
                "category": "export_cleanup",
                "description": "Minutes between scheduler checks",
            },
            # Storage settings
            {
                "key": "export.storage.max_size_gb",
                "value": "50",
                "value_type": "integer",
                "category": "export_storage",
                "description": "Maximum storage size for exports in GB",
            },
            {
                "key": "export.storage.emergency_threshold_gb",
                "value": "1",
                "value_type": "integer",
                "category": "export_storage",
                "description": "Emergency cleanup threshold in GB of free space",
            },
            {
                "key": "export.storage.warning_threshold_gb",
                "value": "5",
                "value_type": "integer",
                "category": "export_storage",
                "description": "Low storage warning threshold in GB of free space",
            },
            {
                "key": "export.storage.large_file_threshold_mb",
                "value": "100",
                "value_type": "integer",
                "category": "export_storage",
                "description": "File size threshold in MB to consider an export 'large'",
            },
            # User settings
            {
                "key": "export.user.admin_bonus_days",
                "value": "14",
                "value_type": "integer",
                "category": "export_user",
                "description": "Additional retention days for admin exports",
            },
            {
                "key": "export.user.frequent_access_bonus_days",
                "value": "7",
                "value_type": "integer",
                "category": "export_user",
                "description": "Additional retention days for frequently accessed exports",
            },
            {
                "key": "export.user.frequent_access_threshold",
                "value": "5",
                "value_type": "integer",
                "category": "export_user",
                "description": "Download count threshold to consider an export frequently accessed",
            },
        ]
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            for config in default_configs:
                # Insert or ignore (don't overwrite existing values)
                conn.execute("""
                    INSERT OR IGNORE INTO system_config 
                    (key, value, value_type, category, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    config["key"],
                    config["value"],
                    config["value_type"],
                    config["category"],
                    config["description"],
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error loading default configuration: {e}")
            conn.rollback()
        finally:
            conn.close()

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute("""
                SELECT value, value_type FROM system_config 
                WHERE key = ?
            """, (key,))
            
            row = cursor.fetchone()
            if not row:
                return default
            
            value_str, value_type = row
            
            # Convert value based on type
            return self._convert_value(value_str, value_type)
            
        except Exception as e:
            logger.error(f"Error getting config {key}: {e}")
            return default
        finally:
            conn.close()

    async def set_config(self, key: str, value: Any, user_id: Optional[int] = None) -> bool:
        """Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            user_id: User ID making the change
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Get current value for audit logging
            cursor = conn.execute("""
                SELECT value, value_type, is_readonly FROM system_config 
                WHERE key = ?
            """, (key,))
            
            current_row = cursor.fetchone()
            
            # Check if readonly
            if current_row and current_row[2]:  # is_readonly
                logger.warning(f"Attempt to modify readonly config: {key}")
                return False
            
            # Determine value type
            value_type = self._get_value_type(value)
            value_str = self._serialize_value(value, value_type)
            
            old_value = current_row[0] if current_row else None
            
            # Update or insert configuration
            cursor = conn.execute("""
                INSERT OR REPLACE INTO system_config 
                (key, value, value_type, updated_at, updated_by)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (key, value_str, value_type, user_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                logger.info(f"Configuration updated: {key} = {value}")
                
                # Log audit event
                await self.audit_logger.log_event_async(AuditEvent(
                    event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                    severity=AuditSeverity.INFO,
                    user_id=user_id,
                    username=None,
                    ip_address=None,
                    user_agent=None,
                    session_id=None,
                    resource_type="system_config",
                    resource_id=key,
                    action="config_updated",
                    details={
                        "config_key": key,
                        "old_value": old_value,
                        "new_value": value_str,
                        "value_type": value_type,
                    },
                    timestamp=datetime.now(),
                    success=True,
                ))
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    async def get_category_config(self, category: str) -> Dict[str, Any]:
        """Get all configuration values for a category.
        
        Args:
            category: Configuration category
            
        Returns:
            Dictionary of configuration values
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT key, value, value_type, description 
                FROM system_config 
                WHERE category = ?
                ORDER BY key
            """, (category,))
            
            config = {}
            for row in cursor.fetchall():
                key = row["key"]
                value = self._convert_value(row["value"], row["value_type"])
                config[key] = {
                    "value": value,
                    "description": row["description"],
                }
            
            return config
            
        except Exception as e:
            logger.error(f"Error getting category config {category}: {e}")
            return {}
        finally:
            conn.close()

    async def get_retention_policies(self) -> Dict[str, int]:
        """Get all retention policies.
        
        Returns:
            Dictionary of format -> retention days
        """
        retention_config = await self.get_category_config("export_retention")
        
        policies = {}
        
        # Extract retention days from configuration
        for key, config_data in retention_config.items():
            if key.endswith("_days"):
                # Convert key to format name
                format_name = key.replace("export.retention.", "").replace("_days", "")
                if format_name == "default":
                    policies["default"] = config_data["value"]
                else:
                    policies[format_name] = config_data["value"]
        
        return policies

    async def update_retention_policies(self, policies: Dict[str, int], user_id: Optional[int] = None) -> bool:
        """Update retention policies.
        
        Args:
            policies: Dictionary of format -> retention days
            user_id: User ID making the changes
            
        Returns:
            True if all updates successful, False otherwise
        """
        all_success = True
        
        for format_name, retention_days in policies.items():
            if format_name == "default":
                config_key = "export.retention.default_days"
            else:
                config_key = f"export.retention.{format_name}_days"
            
            success = await self.set_config(config_key, retention_days, user_id)
            if not success:
                all_success = False
                logger.error(f"Failed to update retention policy for {format_name}")
        
        if all_success:
            logger.info(f"Updated retention policies: {policies}")
        
        return all_success

    async def get_cleanup_config(self) -> Dict[str, Any]:
        """Get cleanup configuration.
        
        Returns:
            Cleanup configuration
        """
        config = await self.get_category_config("export_cleanup")
        
        # Extract values with defaults
        return {
            "enabled": await self.get_config("export.retention.enabled", True),
            "cleanup_hour": await self.get_config("export.cleanup.hour", 2),
            "check_interval_minutes": await self.get_config("export.cleanup.check_interval_minutes", 60),
        }

    async def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration.
        
        Returns:
            Storage configuration
        """
        config = await self.get_category_config("export_storage")
        
        return {
            "max_size_gb": await self.get_config("export.storage.max_size_gb", 50),
            "emergency_threshold_gb": await self.get_config("export.storage.emergency_threshold_gb", 1),
            "warning_threshold_gb": await self.get_config("export.storage.warning_threshold_gb", 5),
            "large_file_threshold_mb": await self.get_config("export.storage.large_file_threshold_mb", 100),
        }

    async def get_user_config(self) -> Dict[str, Any]:
        """Get user-related configuration.
        
        Returns:
            User configuration
        """
        config = await self.get_category_config("export_user")
        
        return {
            "admin_bonus_days": await self.get_config("export.user.admin_bonus_days", 14),
            "frequent_access_bonus_days": await self.get_config("export.user.frequent_access_bonus_days", 7),
            "frequent_access_threshold": await self.get_config("export.user.frequent_access_threshold", 5),
        }

    def _convert_value(self, value_str: str, value_type: str) -> Any:
        """Convert string value to appropriate type.
        
        Args:
            value_str: String value
            value_type: Value type
            
        Returns:
            Converted value
        """
        if value_str is None:
            return None
        
        try:
            if value_type == "boolean":
                return value_str.lower() in ("true", "1", "yes", "on")
            elif value_type == "integer":
                return int(value_str)
            elif value_type == "float":
                return float(value_str)
            elif value_type == "json":
                return json.loads(value_str)
            else:  # string
                return value_str
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error converting value '{value_str}' to {value_type}: {e}")
            return value_str  # Return as string if conversion fails

    def _get_value_type(self, value: Any) -> str:
        """Get value type string.
        
        Args:
            value: Value to get type for
            
        Returns:
            Value type string
        """
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (dict, list)):
            return "json"
        else:
            return "string"

    def _serialize_value(self, value: Any, value_type: str) -> str:
        """Serialize value to string.
        
        Args:
            value: Value to serialize
            value_type: Value type
            
        Returns:
            Serialized value
        """
        if value_type == "json":
            return json.dumps(value)
        else:
            return str(value)

    async def export_config(self, category: Optional[str] = None) -> Dict:
        """Export configuration to dictionary.
        
        Args:
            category: Optional category filter
            
        Returns:
            Configuration dictionary
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            if category:
                cursor = conn.execute("""
                    SELECT * FROM system_config 
                    WHERE category = ?
                    ORDER BY key
                """, (category,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM system_config 
                    WHERE category LIKE 'export_%'
                    ORDER BY category, key
                """)
            
            config_data = {}
            for row in cursor.fetchall():
                config_data[row["key"]] = {
                    "value": self._convert_value(row["value"], row["value_type"]),
                    "value_type": row["value_type"],
                    "category": row["category"],
                    "description": row["description"],
                    "is_readonly": bool(row["is_readonly"]),
                    "updated_at": row["updated_at"],
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "category": category,
                "configuration": config_data,
            }
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return {"error": str(e)}
        finally:
            conn.close()

    async def import_config(self, config_data: Dict, user_id: Optional[int] = None) -> Dict:
        """Import configuration from dictionary.
        
        Args:
            config_data: Configuration data to import
            user_id: User ID performing the import
            
        Returns:
            Import results
        """
        results = {
            "imported": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
        }
        
        if "configuration" not in config_data:
            results["error_details"].append("Invalid config data format")
            results["errors"] = 1
            return results
        
        for key, config_info in config_data["configuration"].items():
            try:
                value = config_info["value"]
                success = await self.set_config(key, value, user_id)
                
                if success:
                    results["imported"] += 1
                else:
                    results["skipped"] += 1
                    
            except Exception as e:
                results["errors"] += 1
                results["error_details"].append(f"Error importing {key}: {str(e)}")
        
        logger.info(f"Configuration import completed: {results}")
        return results


# Environment variable integration
def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables.
    
    Returns:
        Configuration dictionary
    """
    env_config = {}
    
    # Export retention settings
    if "EXPORT_RETENTION_ENABLED" in os.environ:
        env_config["export.retention.enabled"] = os.getenv("EXPORT_RETENTION_ENABLED", "true")
    
    if "EXPORT_DEFAULT_RETENTION_DAYS" in os.environ:
        env_config["export.retention.default_days"] = os.getenv("EXPORT_DEFAULT_RETENTION_DAYS", "30")
    
    if "EXPORT_CSV_RETENTION_DAYS" in os.environ:
        env_config["export.retention.csv_days"] = os.getenv("EXPORT_CSV_RETENTION_DAYS", "7")
    
    if "EXPORT_CLEANUP_HOUR" in os.environ:
        env_config["export.cleanup.hour"] = os.getenv("EXPORT_CLEANUP_HOUR", "2")
    
    if "EXPORT_MAX_STORAGE_GB" in os.environ:
        env_config["export.storage.max_size_gb"] = os.getenv("EXPORT_MAX_STORAGE_GB", "50")
    
    if "EXPORT_EMERGENCY_CLEANUP_THRESHOLD_GB" in os.environ:
        env_config["export.storage.emergency_threshold_gb"] = os.getenv("EXPORT_EMERGENCY_CLEANUP_THRESHOLD_GB", "1")
    
    return env_config


async def apply_env_config(config_manager: ExportRetentionConfig, user_id: Optional[int] = None) -> int:
    """Apply environment variable configuration.
    
    Args:
        config_manager: Configuration manager instance
        user_id: User ID for audit logging
        
    Returns:
        Number of configuration values applied
    """
    env_config = load_config_from_env()
    applied = 0
    
    for key, value in env_config.items():
        try:
            if await config_manager.set_config(key, value, user_id):
                applied += 1
                logger.info(f"Applied env config: {key} = {value}")
        except Exception as e:
            logger.error(f"Error applying env config {key}: {e}")
    
    return applied