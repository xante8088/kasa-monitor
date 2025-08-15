#!/usr/bin/env python3
"""Database migration script for Kasa Monitor.

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

import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Migration:
    """Base class for database migrations."""

    def __init__(self, version: str, description: str):
        """Initialize migration.

        Args:
            version: Migration version
            description: Migration description
        """
        self.version = version
        self.description = description
        self.applied_at = None

    def up(self, conn: sqlite3.Connection):
        """Apply migration (upgrade).

        Args:
            conn: Database connection
        """
        raise NotImplementedError

    def down(self, conn: sqlite3.Connection):
        """Rollback migration (downgrade).

        Args:
            conn: Database connection
        """
        raise NotImplementedError

    def verify(self, conn: sqlite3.Connection) -> bool:
        """Verify migration was applied correctly.

        Args:
            conn: Database connection

        Returns:
            True if migration is valid
        """
        return True


class MigrationManager:
    """Manages database migrations."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize migration manager.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.migrations = []
        self._init_migration_table()
        self._load_migrations()

    def _init_migration_table(self):
        """Initialize migration tracking table."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT
                )
            """
            )
            conn.commit()
        finally:
            conn.close()

    def _load_migrations(self):
        """Load all available migrations."""
        # Define migrations in order
        self.migrations = [
            Migration001_AddIndexes(),
            Migration002_AddAuditTables(),
            Migration003_AddPluginTables(),
            Migration004_AddPerformanceTables(),
            Migration005_AddAdvancedFeatures(),
        ]

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions.

        Returns:
            List of applied version strings
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations.

        Returns:
            List of pending migrations
        """
        applied = self.get_applied_migrations()
        return [m for m in self.migrations if m.version not in applied]

    def apply_migration(self, migration: Migration):
        """Apply a single migration.

        Args:
            migration: Migration to apply
        """
        logger.info(f"Applying migration {migration.version}: {migration.description}")

        conn = sqlite3.connect(self.db_path)
        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            # Apply migration
            migration.up(conn)

            # Verify migration
            if not migration.verify(conn):
                raise Exception(f"Migration {migration.version} verification failed")

            # Record migration
            conn.execute(
                """
                INSERT INTO schema_migrations (version, description)
                VALUES (?, ?)
            """,
                (migration.version, migration.description),
            )

            # Commit transaction
            conn.commit()

            logger.info(f"Migration {migration.version} applied successfully")

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Migration {migration.version} failed: {e}")
            raise
        finally:
            conn.close()

    def rollback_migration(self, migration: Migration):
        """Rollback a single migration.

        Args:
            migration: Migration to rollback
        """
        logger.info(
            f"Rolling back migration {migration.version}: {migration.description}"
        )

        conn = sqlite3.connect(self.db_path)
        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            # Rollback migration
            migration.down(conn)

            # Remove migration record
            conn.execute(
                "DELETE FROM schema_migrations WHERE version = ?", (migration.version,)
            )

            # Commit transaction
            conn.commit()

            logger.info(f"Migration {migration.version} rolled back successfully")

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Rollback of {migration.version} failed: {e}")
            raise
        finally:
            conn.close()

    def migrate(self, target_version: Optional[str] = None):
        """Apply all pending migrations up to target version.

        Args:
            target_version: Target version to migrate to
        """
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return

        logger.info(f"Found {len(pending)} pending migrations")

        for migration in pending:
            if target_version and migration.version > target_version:
                break
            self.apply_migration(migration)

    def rollback(self, steps: int = 1):
        """Rollback last N migrations.

        Args:
            steps: Number of migrations to rollback
        """
        applied = self.get_applied_migrations()

        if not applied:
            logger.info("No migrations to rollback")
            return

        # Get migrations to rollback
        to_rollback = applied[-steps:] if steps <= len(applied) else applied

        # Find migration objects
        for version in reversed(to_rollback):
            migration = next((m for m in self.migrations if m.version == version), None)
            if migration:
                self.rollback_migration(migration)
            else:
                logger.warning(f"Migration {version} not found in codebase")

    def status(self):
        """Show migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        logger.info("Migration Status:")
        logger.info(f"  Applied: {len(applied)} migrations")
        logger.info(f"  Pending: {len(pending)} migrations")

        if applied:
            logger.info("\nApplied Migrations:")
            for version in applied:
                migration = next(
                    (m for m in self.migrations if m.version == version), None
                )
                if migration:
                    logger.info(f"  {version}: {migration.description}")
                else:
                    logger.info(f"  {version}: (migration not found in codebase)")

        if pending:
            logger.info("\nPending Migrations:")
            for migration in pending:
                logger.info(f"  {migration.version}: {migration.description}")


# Migration implementations


class Migration001_AddIndexes(Migration):
    """Add performance indexes to database."""

    def __init__(self):
        super().__init__("001", "Add performance indexes")

    def up(self, conn: sqlite3.Connection):
        """Apply migration."""
        # Add indexes for device_readings
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_device_readings_device_timestamp 
            ON device_readings(device_ip, timestamp DESC)
        """
        )

        # Add indexes for user_sessions
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id 
            ON user_sessions(user_id)
        """
        )

        # Add indexes for audit_logs
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id 
            ON audit_logs(user_id, timestamp DESC)
        """
        )

    def down(self, conn: sqlite3.Connection):
        """Rollback migration."""
        conn.execute("DROP INDEX IF EXISTS idx_device_readings_device_timestamp")
        conn.execute("DROP INDEX IF EXISTS idx_user_sessions_user_id")
        conn.execute("DROP INDEX IF EXISTS idx_audit_logs_user_id")


class Migration002_AddAuditTables(Migration):
    """Add audit logging tables."""

    def __init__(self):
        super().__init__("002", "Add audit logging tables")

    def up(self, conn: sqlite3.Connection):
        """Apply migration."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

    def down(self, conn: sqlite3.Connection):
        """Rollback migration."""
        conn.execute("DROP TABLE IF EXISTS audit_logs")


class Migration003_AddPluginTables(Migration):
    """Add plugin system tables."""

    def __init__(self):
        super().__init__("003", "Add plugin system tables")

    def up(self, conn: sqlite3.Connection):
        """Apply migration."""
        # Plugin registry table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_registry (
                plugin_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                manifest TEXT NOT NULL,
                state TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                install_path TEXT,
                config TEXT,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_loaded TIMESTAMP,
                error_message TEXT
            )
        """
        )

        # Hook definitions table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hook_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                plugin_id TEXT,
                hook_type TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                conditions TEXT,
                async_hook BOOLEAN DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, plugin_id)
            )
        """
        )

    def down(self, conn: sqlite3.Connection):
        """Rollback migration."""
        conn.execute("DROP TABLE IF EXISTS plugin_registry")
        conn.execute("DROP TABLE IF EXISTS hook_definitions")


class Migration004_AddPerformanceTables(Migration):
    """Add performance monitoring tables."""

    def __init__(self):
        super().__init__("004", "Add performance monitoring tables")

    def up(self, conn: sqlite3.Connection):
        """Apply migration."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                tags TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_perf_metrics_name_time 
            ON performance_metrics(metric_name, timestamp DESC)
        """
        )

    def down(self, conn: sqlite3.Connection):
        """Rollback migration."""
        conn.execute("DROP TABLE IF EXISTS performance_metrics")


class Migration005_AddAdvancedFeatures(Migration):
    """Add tables for advanced features."""

    def __init__(self):
        super().__init__("005", "Add advanced feature tables")

    def up(self, conn: sqlite3.Connection):
        """Apply migration."""
        # API versioning table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_versions (
                version TEXT PRIMARY KEY,
                deprecated BOOLEAN DEFAULT 0,
                sunset_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Testing results table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_suite TEXT NOT NULL,
                test_name TEXT NOT NULL,
                result TEXT NOT NULL,
                duration_ms INTEGER,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    def down(self, conn: sqlite3.Connection):
        """Rollback migration."""
        conn.execute("DROP TABLE IF EXISTS api_versions")
        conn.execute("DROP TABLE IF EXISTS test_results")


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(description="Database migrations for Kasa Monitor")
    parser.add_argument("--db", default="kasa_monitor.db", help="Database path")
    parser.add_argument(
        "command", choices=["migrate", "rollback", "status"], help="Migration command"
    )
    parser.add_argument("--target", help="Target version for migration")
    parser.add_argument(
        "--steps", type=int, default=1, help="Number of migrations to rollback"
    )

    args = parser.parse_args()

    # Create migration manager
    manager = MigrationManager(args.db)

    # Execute command
    if args.command == "migrate":
        manager.migrate(args.target)
    elif args.command == "rollback":
        manager.rollback(args.steps)
    elif args.command == "status":
        manager.status()


if __name__ == "__main__":
    main()
