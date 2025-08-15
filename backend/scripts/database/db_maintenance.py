#!/usr/bin/env python3
"""Database maintenance scripts for Kasa Monitor.

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
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseMaintenance:
    """Database maintenance operations."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize database maintenance.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path

    def vacuum(self):
        """Vacuum database to reclaim space."""
        logger.info("Starting database vacuum...")

        conn = sqlite3.connect(self.db_path)
        try:
            # Get initial size
            initial_size = os.path.getsize(self.db_path)

            # Vacuum database
            conn.execute("VACUUM")
            conn.commit()

            # Get final size
            final_size = os.path.getsize(self.db_path)

            # Calculate space saved
            space_saved = initial_size - final_size
            percentage = (space_saved / initial_size) * 100 if initial_size > 0 else 0

            logger.info(
                f"Vacuum complete. Space saved: {space_saved:,} bytes ({percentage:.1f}%)"
            )
            logger.info(f"Database size: {initial_size:,} -> {final_size:,} bytes")

        finally:
            conn.close()

    def analyze(self):
        """Analyze database to update statistics."""
        logger.info("Analyzing database...")

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("ANALYZE")
            conn.commit()
            logger.info("Database analysis complete")

        finally:
            conn.close()

    def check_integrity(self):
        """Check database integrity."""
        logger.info("Checking database integrity...")

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result[0] == "ok":
                logger.info("Database integrity check passed")
                return True
            else:
                logger.error(f"Database integrity check failed: {result}")
                return False

        finally:
            conn.close()

    def optimize_indexes(self):
        """Rebuild indexes for optimization."""
        logger.info("Optimizing indexes...")

        conn = sqlite3.connect(self.db_path)
        try:
            # Get all indexes
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """
            )
            indexes = cursor.fetchall()

            # Rebuild each index
            for index in indexes:
                logger.info(f"Rebuilding index: {index[0]}")
                conn.execute(f"REINDEX {index[0]}")

            conn.commit()
            logger.info(f"Optimized {len(indexes)} indexes")

        finally:
            conn.close()

    def clean_old_data(self, days: int = 90):
        """Clean old data from database.

        Args:
            days: Number of days to retain
        """
        logger.info(f"Cleaning data older than {days} days...")

        conn = sqlite3.connect(self.db_path)
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Clean old device readings
            cursor = conn.execute(
                """
                DELETE FROM device_readings 
                WHERE timestamp < ?
            """,
                (cutoff_date,),
            )
            readings_deleted = cursor.rowcount

            # Clean old session data
            cursor = conn.execute(
                """
                DELETE FROM user_sessions 
                WHERE created_at < ? AND is_active = 0
            """,
                (cutoff_date,),
            )
            sessions_deleted = cursor.rowcount

            # Clean old audit logs
            cursor = conn.execute(
                """
                DELETE FROM audit_logs 
                WHERE timestamp < ?
            """,
                (cutoff_date,),
            )
            logs_deleted = cursor.rowcount

            # Clean old alert history
            cursor = conn.execute(
                """
                DELETE FROM alert_history 
                WHERE timestamp < ?
            """,
                (cutoff_date,),
            )
            alerts_deleted = cursor.rowcount

            conn.commit()

            logger.info(f"Cleaned old data:")
            logger.info(f"  - Device readings: {readings_deleted}")
            logger.info(f"  - Sessions: {sessions_deleted}")
            logger.info(f"  - Audit logs: {logs_deleted}")
            logger.info(f"  - Alert history: {alerts_deleted}")

        finally:
            conn.close()

    def get_statistics(self):
        """Get database statistics."""
        logger.info("Gathering database statistics...")

        conn = sqlite3.connect(self.db_path)
        try:
            stats = {}

            # Get database size
            stats["size_bytes"] = os.path.getsize(self.db_path)
            stats["size_mb"] = stats["size_bytes"] / (1024 * 1024)

            # Get table counts
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            )
            tables = cursor.fetchall()

            stats["tables"] = {}
            for table in tables:
                table_name = table[0]
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats["tables"][table_name] = count

            # Get index count
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """
            )
            stats["index_count"] = cursor.fetchone()[0]

            # Print statistics
            logger.info("Database Statistics:")
            logger.info(f"  Size: {stats['size_mb']:.2f} MB")
            logger.info(f"  Tables: {len(stats['tables'])}")
            logger.info(f"  Indexes: {stats['index_count']}")
            logger.info("  Table row counts:")
            for table, count in sorted(stats["tables"].items()):
                logger.info(f"    - {table}: {count:,}")

            return stats

        finally:
            conn.close()

    def repair_foreign_keys(self):
        """Check and repair foreign key constraints."""
        logger.info("Checking foreign key constraints...")

        conn = sqlite3.connect(self.db_path)
        try:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Check foreign key violations
            cursor = conn.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()

            if violations:
                logger.warning(f"Found {len(violations)} foreign key violations")
                for violation in violations:
                    logger.warning(f"  - Table: {violation[0]}, Row: {violation[1]}")
            else:
                logger.info("No foreign key violations found")

            return len(violations) == 0

        finally:
            conn.close()

    def full_maintenance(self):
        """Perform full database maintenance."""
        logger.info("Starting full database maintenance...")

        # Check integrity first
        if not self.check_integrity():
            logger.error("Database integrity check failed, aborting maintenance")
            return False

        # Get initial statistics
        initial_stats = self.get_statistics()

        # Clean old data
        self.clean_old_data()

        # Optimize indexes
        self.optimize_indexes()

        # Analyze database
        self.analyze()

        # Vacuum database
        self.vacuum()

        # Check foreign keys
        self.repair_foreign_keys()

        # Get final statistics
        final_stats = self.get_statistics()

        # Compare statistics
        logger.info("Maintenance Summary:")
        logger.info(
            f"  Size reduction: {initial_stats['size_mb'] - final_stats['size_mb']:.2f} MB"
        )

        return True


def main():
    """Main entry point for database maintenance script."""
    parser = argparse.ArgumentParser(
        description="Database maintenance for Kasa Monitor"
    )
    parser.add_argument("--db", default="kasa_monitor.db", help="Database path")
    parser.add_argument("--vacuum", action="store_true", help="Vacuum database")
    parser.add_argument("--analyze", action="store_true", help="Analyze database")
    parser.add_argument("--check", action="store_true", help="Check integrity")
    parser.add_argument("--optimize", action="store_true", help="Optimize indexes")
    parser.add_argument(
        "--clean", type=int, metavar="DAYS", help="Clean data older than DAYS"
    )
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--repair", action="store_true", help="Repair foreign keys")
    parser.add_argument("--full", action="store_true", help="Full maintenance")

    args = parser.parse_args()

    # Create maintenance instance
    maintenance = DatabaseMaintenance(args.db)

    # Execute requested operations
    if args.full:
        maintenance.full_maintenance()
    else:
        if args.check:
            maintenance.check_integrity()
        if args.clean:
            maintenance.clean_old_data(args.clean)
        if args.optimize:
            maintenance.optimize_indexes()
        if args.analyze:
            maintenance.analyze()
        if args.vacuum:
            maintenance.vacuum()
        if args.repair:
            maintenance.repair_foreign_keys()
        if args.stats:
            maintenance.get_statistics()

        # Default to showing stats if no operation specified
        if not any(
            [
                args.check,
                args.clean,
                args.optimize,
                args.analyze,
                args.vacuum,
                args.repair,
                args.stats,
            ]
        ):
            maintenance.get_statistics()


if __name__ == "__main__":
    main()
