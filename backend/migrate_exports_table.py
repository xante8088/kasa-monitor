#!/usr/bin/env python3
"""
Database migration script to add user_id column to data_exports table.

This is a critical security migration to support export ownership tracking.
Run this script before deploying the security fixes.

Copyright (C) 2025 Kasa Monitor Contributors
"""

import sqlite3
import os
import sys
from datetime import datetime


def migrate_exports_table(db_path: str = "kasa_monitor.db"):
    """Add user_id column to data_exports table if it doesn't exist."""
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist. Creating new database.")
        return
    
    print(f"Migrating exports table in {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if data_exports table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='data_exports'
        """)
        
        if not cursor.fetchone():
            print("data_exports table does not exist yet. This is normal for new installations.")
            print("The table will be created with user_id column when first used.")
            return
        
        # Check if user_id column already exists
        cursor.execute("PRAGMA table_info(data_exports)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' in columns:
            print("Migration not needed: user_id column already exists")
            return
        
        print("Adding user_id column to data_exports table...")
        
        # Add the user_id column (NULL allowed for existing records)
        cursor.execute("ALTER TABLE data_exports ADD COLUMN user_id INTEGER")
        
        # Commit the migration
        conn.commit()
        
        print("Migration completed successfully!")
        print("Note: Existing export records will have NULL user_id values.")
        print("Only administrators can access exports with NULL user_id values.")
        
        # Try to log the migration (if audit_log table exists)
        try:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='audit_log'
            """)
            
            if cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO audit_log 
                    (event_type, severity, user_id, username, ip_address, user_agent, 
                     session_id, resource_type, resource_id, action, details, success, 
                     error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "system.config_changed",
                        "info", 
                        None,
                        "system",
                        "127.0.0.1",
                        "migration-script",
                        None,
                        "database",
                        "data_exports",
                        "Added user_id column for export ownership tracking",
                        '{"migration": "add_user_id_column", "table": "data_exports"}',
                        True,
                        None,
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
        except Exception as e:
            print(f"Could not log migration to audit table: {e}")
        
    except sqlite3.Error as e:
        print(f"Migration failed: {e}")
        print("This might be due to database corruption or schema issues.")
        print("The new export system will create the table with the correct schema.")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "kasa_monitor.db"
    migrate_exports_table(db_path)