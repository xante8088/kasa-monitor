"""Device grouping system with hierarchical structure and permissions.

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
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from enum import Enum
from dataclasses import dataclass, asdict
import asyncio


class GroupType(Enum):
    """Device group types."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    SMART = "smart"
    LOCATION = "location"
    CATEGORY = "category"


class GroupPermission(Enum):
    """Group-specific permissions."""
    VIEW = "group.view"
    EDIT = "group.edit"
    DELETE = "group.delete"
    MANAGE_DEVICES = "group.manage_devices"
    EXECUTE_ACTIONS = "group.execute_actions"
    MANAGE_SCHEDULES = "group.manage_schedules"


@dataclass
class DeviceGroup:
    """Device group definition."""
    name: str
    description: str
    group_type: GroupType
    parent_id: Optional[int] = None
    rules: Optional[Dict] = None
    metadata: Optional[Dict] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    enabled: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['group_type'] = self.group_type.value
        return data


@dataclass
class GroupAction:
    """Group action definition."""
    name: str
    action_type: str
    parameters: Dict[str, Any]
    apply_to_all: bool = True
    filter_conditions: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class DeviceGroupManager:
    """Manages device groups and hierarchical organization."""
    
    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize device group manager.
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize device group tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Device groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                group_type TEXT NOT NULL,
                parent_id INTEGER,
                rules TEXT,
                metadata TEXT,
                icon TEXT,
                color TEXT,
                sort_order INTEGER DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES device_groups(id) ON DELETE CASCADE
            )
        """)
        
        # Group members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER NOT NULL,
                device_ip TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by TEXT,
                PRIMARY KEY (group_id, device_ip),
                FOREIGN KEY (group_id) REFERENCES device_groups(id) ON DELETE CASCADE
            )
        """)
        
        # Group permissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_permissions (
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                permission TEXT NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                granted_by TEXT,
                PRIMARY KEY (group_id, user_id, permission),
                FOREIGN KEY (group_id) REFERENCES device_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Group actions history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                action_name TEXT NOT NULL,
                action_type TEXT NOT NULL,
                parameters TEXT,
                executed_by TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                devices_affected INTEGER,
                success_count INTEGER,
                failure_count INTEGER,
                error_details TEXT,
                FOREIGN KEY (group_id) REFERENCES device_groups(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_parent ON device_groups(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_type ON device_groups(group_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_member_device ON group_members(device_ip)")
        
        conn.commit()
        conn.close()
    
    def create_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new device group.
        
        Args:
            group: Device group to create
            
        Returns:
            Group ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO device_groups 
                (name, description, group_type, parent_id, rules, metadata, 
                 icon, color, sort_order, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                group_data.get('name'),
                group_data.get('description', ''),
                'manual',  # Default group type
                group_data.get('parent_id'),
                json.dumps(group_data.get('rules')) if group_data.get('rules') else None,
                json.dumps(group_data.get('metadata')) if group_data.get('metadata') else None,
                group_data.get('icon'),
                group_data.get('color'),
                group_data.get('sort_order', 0),
                group_data.get('enabled', True)
            ))
            
            group_id = cursor.lastrowid
            
            # Add devices to the group if provided
            devices = group_data.get('devices', [])
            for device_ip in devices:
                cursor.execute("""
                    INSERT OR IGNORE INTO group_members (group_id, device_ip)
                    VALUES (?, ?)
                """, (group_id, device_ip))
            
            conn.commit()
            
            # Return the created group
            return self.get_group(group_id)
            
        except sqlite3.IntegrityError:
            return 0
        finally:
            conn.close()
    
    def update_group(self, group_id: int, updates: Dict) -> bool:
        """Update device group.
        
        Args:
            group_id: Group ID
            updates: Fields to update
            
        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Handle devices separately
        devices = updates.pop('devices', None)
        
        # Build update query for group fields
        if updates:
            fields = []
            values = []
            
            for key, value in updates.items():
                if key in ['name', 'description', 'parent_id']:  # Only update safe fields
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if fields:
                fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(group_id)
                
                query = f"UPDATE device_groups SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
        
        # Update group members if devices provided
        if devices is not None:
            # Remove all existing members
            cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
            
            # Add new members
            for device_ip in devices:
                cursor.execute("""
                    INSERT OR IGNORE INTO group_members (group_id, device_ip)
                    VALUES (?, ?)
                """, (group_id, device_ip))
        
        conn.commit()
        success = True
        conn.close()
        
        return success
    
    def delete_group(self, group_id: int, reassign_children_to: Optional[int] = None) -> bool:
        """Delete device group.
        
        Args:
            group_id: Group ID to delete
            reassign_children_to: Parent ID to reassign children to
            
        Returns:
            True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Reassign children if specified
            if reassign_children_to is not None:
                cursor.execute(
                    "UPDATE device_groups SET parent_id = ? WHERE parent_id = ?",
                    (reassign_children_to, group_id)
                )
            
            # Delete the group
            cursor.execute("DELETE FROM device_groups WHERE id = ?", (group_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            return success
            
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def add_device_to_group(self, group_id: int, device_ip: str, added_by: str = "system") -> bool:
        """Add device to group.
        
        Args:
            group_id: Group ID
            device_ip: Device IP address
            added_by: User adding the device
            
        Returns:
            True if added successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO group_members (group_id, device_ip, added_by)
                VALUES (?, ?, ?)
            """, (group_id, device_ip, added_by))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception:
            return False
        finally:
            conn.close()
    
    def remove_device_from_group(self, group_id: int, device_ip: str) -> bool:
        """Remove device from group.
        
        Args:
            group_id: Group ID
            device_ip: Device IP address
            
        Returns:
            True if removed successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM group_members WHERE group_id = ? AND device_ip = ?",
            (group_id, device_ip)
        )
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_group_devices(self, group_id: int) -> List[str]:
        """Get devices in a group.
        
        Args:
            group_id: Group ID
            
        Returns:
            List of device IPs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT device_ip FROM group_members WHERE group_id = ?",
            (group_id,)
        )
        
        devices = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return devices
    
    def get_device_groups(self, device_ip: str) -> List[Dict]:
        """Get groups a device belongs to.
        
        Args:
            device_ip: Device IP address
            
        Returns:
            List of groups
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.group_type, g.icon, g.color
            FROM device_groups g
            JOIN group_members m ON g.id = m.group_id
            WHERE m.device_ip = ? AND g.enabled = 1
            ORDER BY g.sort_order, g.name
        """, (device_ip,))
        
        groups = []
        for row in cursor.fetchall():
            groups.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'group_type': row[3],
                'icon': row[4],
                'color': row[5]
            })
        
        conn.close()
        return groups
    
    def get_all_groups(self) -> List[Dict]:
        """Get all device groups.
        
        Returns:
            List of all groups with their metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    g.id,
                    g.name,
                    g.description,
                    g.parent_id,
                    g.created_at,
                    COUNT(DISTINCT gm.device_ip) as device_count,
                    0 as total_power
                FROM device_groups g
                LEFT JOIN group_members gm ON g.id = gm.group_id
                WHERE g.enabled = 1
                GROUP BY g.id
                ORDER BY g.sort_order, g.name
            """)
            
            groups = []
            for row in cursor.fetchall():
                # Get devices for this group
                cursor.execute("""
                    SELECT device_ip FROM group_members
                    WHERE group_id = ?
                """, (row[0],))
                devices = [r[0] for r in cursor.fetchall()]
                
                groups.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'parent_id': row[3],
                    'created_at': row[4],
                    'device_count': row[5],
                    'total_power': row[6],
                    'devices': devices
                })
            
            return groups
            
        finally:
            conn.close()
    
    def get_group(self, group_id: int) -> Optional[Dict]:
        """Get a specific device group.
        
        Args:
            group_id: Group ID
            
        Returns:
            Group data or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    g.id,
                    g.name,
                    g.description,
                    g.parent_id,
                    g.created_at,
                    COUNT(DISTINCT gm.device_ip) as device_count,
                    0 as total_power
                FROM device_groups g
                LEFT JOIN group_members gm ON g.id = gm.group_id
                WHERE g.id = ? AND g.enabled = 1
                GROUP BY g.id
            """, (group_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get devices for this group
            cursor.execute("""
                SELECT device_ip FROM group_members
                WHERE group_id = ?
            """, (group_id,))
            devices = [r[0] for r in cursor.fetchall()]
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'parent_id': row[3],
                'created_at': row[4],
                'device_count': row[5],
                'total_power': row[6],
                'devices': devices
            }
            
        finally:
            conn.close()
    
    def control_group(self, group_id: int, action: str) -> Dict[str, Any]:
        """Control all devices in a group.
        
        Args:
            group_id: Group ID
            action: Control action ('on' or 'off')
            
        Returns:
            Result of control operation
        """
        devices = self.get_group_devices(group_id)
        results = {'success': [], 'failed': []}
        
        # This would normally control actual devices
        # For now, just return success for all devices
        for device_ip in devices:
            results['success'].append(device_ip)
        
        return {
            'group_id': group_id,
            'action': action,
            'devices_affected': len(devices),
            'results': results
        }
    
    def get_group_hierarchy(self, parent_id: Optional[int] = None) -> List[Dict]:
        """Get hierarchical group structure.
        
        Args:
            parent_id: Parent group ID (None for root groups)
            
        Returns:
            Hierarchical group structure
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get groups at this level
        if parent_id is None:
            cursor.execute("""
                SELECT id, name, description, group_type, icon, color, sort_order
                FROM device_groups
                WHERE parent_id IS NULL AND enabled = 1
                ORDER BY sort_order, name
            """)
        else:
            cursor.execute("""
                SELECT id, name, description, group_type, icon, color, sort_order
                FROM device_groups
                WHERE parent_id = ? AND enabled = 1
                ORDER BY sort_order, name
            """, (parent_id,))
        
        groups = []
        for row in cursor.fetchall():
            group = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'group_type': row[3],
                'icon': row[4],
                'color': row[5],
                'sort_order': row[6],
                'children': self.get_group_hierarchy(row[0])  # Recursive call
            }
            
            # Get device count
            cursor.execute(
                "SELECT COUNT(*) FROM group_members WHERE group_id = ?",
                (row[0],)
            )
            group['device_count'] = cursor.fetchone()[0]
            
            groups.append(group)
        
        conn.close()
        return groups
    
    def execute_group_action(self, group_id: int, action: GroupAction, 
                            executed_by: str = "system") -> Dict[str, Any]:
        """Execute action on all devices in a group.
        
        Args:
            group_id: Group ID
            action: Action to execute
            executed_by: User executing the action
            
        Returns:
            Execution results
        """
        # Get devices in group
        devices = self.get_group_devices(group_id)
        
        if action.filter_conditions:
            # Apply filters if specified
            devices = self._filter_devices(devices, action.filter_conditions)
        
        results = {
            'total_devices': len(devices),
            'success_count': 0,
            'failure_count': 0,
            'errors': []
        }
        
        # Execute action on each device
        for device_ip in devices:
            try:
                # TODO: Execute the actual action on the device
                # This would integrate with the device control system
                results['success_count'] += 1
            except Exception as e:
                results['failure_count'] += 1
                results['errors'].append({
                    'device': device_ip,
                    'error': str(e)
                })
        
        # Record action in history
        self._record_group_action(
            group_id, action, executed_by, results
        )
        
        return results
    
    def _filter_devices(self, devices: List[str], conditions: Dict) -> List[str]:
        """Filter devices based on conditions.
        
        Args:
            devices: List of device IPs
            conditions: Filter conditions
            
        Returns:
            Filtered device list
        """
        # TODO: Implement device filtering based on conditions
        # This would check device properties against the conditions
        return devices
    
    def _record_group_action(self, group_id: int, action: GroupAction, 
                            executed_by: str, results: Dict):
        """Record group action in history.
        
        Args:
            group_id: Group ID
            action: Action executed
            executed_by: User who executed
            results: Execution results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO group_actions 
            (group_id, action_name, action_type, parameters, executed_by,
             devices_affected, success_count, failure_count, error_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            group_id,
            action.name,
            action.action_type,
            json.dumps(action.parameters),
            executed_by,
            results['total_devices'],
            results['success_count'],
            results['failure_count'],
            json.dumps(results.get('errors')) if results.get('errors') else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_group_permissions(self, group_id: int, user_id: int) -> List[str]:
        """Get user's permissions for a group.
        
        Args:
            group_id: Group ID
            user_id: User ID
            
        Returns:
            List of permissions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT permission FROM group_permissions
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        
        permissions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return permissions
    
    def grant_group_permission(self, group_id: int, user_id: int, 
                              permission: GroupPermission, granted_by: str = "system") -> bool:
        """Grant permission to user for a group.
        
        Args:
            group_id: Group ID
            user_id: User ID
            permission: Permission to grant
            granted_by: User granting permission
            
        Returns:
            True if granted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO group_permissions 
                (group_id, user_id, permission, granted_by)
                VALUES (?, ?, ?, ?)
            """, (group_id, user_id, permission.value, granted_by))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception:
            return False
        finally:
            conn.close()
    
    def revoke_group_permission(self, group_id: int, user_id: int, 
                               permission: GroupPermission) -> bool:
        """Revoke permission from user for a group.
        
        Args:
            group_id: Group ID
            user_id: User ID
            permission: Permission to revoke
            
        Returns:
            True if revoked successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM group_permissions
            WHERE group_id = ? AND user_id = ? AND permission = ?
        """, (group_id, user_id, permission.value))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def evaluate_dynamic_group(self, group_id: int) -> List[str]:
        """Evaluate dynamic group rules to get current members.
        
        Args:
            group_id: Group ID
            
        Returns:
            List of device IPs that match the rules
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get group rules
        cursor.execute(
            "SELECT rules FROM device_groups WHERE id = ? AND group_type = 'dynamic'",
            (group_id,)
        )
        
        row = cursor.fetchone()
        if not row or not row[0]:
            conn.close()
            return []
        
        rules = json.loads(row[0])
        
        # TODO: Implement rule evaluation logic
        # This would query devices based on the rules
        # For example: {"power_usage": {"operator": ">", "value": 100}}
        
        devices = []
        conn.close()
        
        return devices
    
    def get_group_statistics(self, group_id: int) -> Dict[str, Any]:
        """Get statistics for a group.
        
        Args:
            group_id: Group ID
            
        Returns:
            Group statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get device count
        cursor.execute(
            "SELECT COUNT(*) FROM group_members WHERE group_id = ?",
            (group_id,)
        )
        device_count = cursor.fetchone()[0]
        
        # Get subgroup count
        cursor.execute(
            "SELECT COUNT(*) FROM device_groups WHERE parent_id = ?",
            (group_id,)
        )
        subgroup_count = cursor.fetchone()[0]
        
        # Get recent actions
        cursor.execute("""
            SELECT COUNT(*), SUM(success_count), SUM(failure_count)
            FROM group_actions
            WHERE group_id = ? AND executed_at > datetime('now', '-7 days')
        """, (group_id,))
        
        row = cursor.fetchone()
        
        stats = {
            'device_count': device_count,
            'subgroup_count': subgroup_count,
            'recent_actions': {
                'count': row[0] or 0,
                'success': row[1] or 0,
                'failure': row[2] or 0
            }
        }
        
        conn.close()
        return stats