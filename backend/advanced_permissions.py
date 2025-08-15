"""Advanced permissions system with device-specific and hierarchical permissions.

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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import fnmatch
from collections import defaultdict


class PermissionScope(Enum):
    """Permission scope levels."""

    GLOBAL = "global"
    FEATURE = "feature"
    RESOURCE = "resource"
    DEVICE = "device"
    DEVICE_GROUP = "device_group"


class PermissionAction(Enum):
    """Standard permission actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    CONTROL = "control"
    CONFIGURE = "configure"
    EXPORT = "export"
    IMPORT = "import"
    SHARE = "share"


class ResourceType(Enum):
    """Types of resources."""

    DEVICE = "device"
    DEVICE_GROUP = "device_group"
    USER = "user"
    ROLE = "role"
    RATE = "rate"
    SCHEDULE = "schedule"
    REPORT = "report"
    BACKUP = "backup"
    SYSTEM = "system"
    API = "api"


@dataclass
class Permission:
    """Permission definition."""

    name: str
    scope: PermissionScope
    resource_type: ResourceType
    actions: List[PermissionAction]
    resource_id: Optional[str] = None
    conditions: Optional[Dict] = None
    expires_at: Optional[datetime] = None

    def matches(
        self,
        action: PermissionAction,
        resource_type: ResourceType,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if permission matches request.

        Args:
            action: Requested action
            resource_type: Type of resource
            resource_id: Specific resource ID

        Returns:
            True if permission matches
        """
        # Check resource type
        if self.resource_type != resource_type:
            return False

        # Check action
        if action not in self.actions:
            return False

        # Check resource ID if specified
        if self.scope in [PermissionScope.DEVICE, PermissionScope.RESOURCE]:
            if self.resource_id:
                # Support wildcards
                if not fnmatch.fnmatch(resource_id or "", self.resource_id):
                    return False

        # Check expiration
        if self.expires_at and datetime.now() > self.expires_at:
            return False

        # Check conditions
        if self.conditions:
            # TODO: Implement condition evaluation
            pass

        return True


@dataclass
class PermissionTemplate:
    """Reusable permission template."""

    name: str
    description: str
    permissions: List[Permission]
    is_system: bool = False


class AdvancedPermissionManager:
    """Advanced permission management system."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize permission manager.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self._init_database()
        self._init_default_templates()

    def _init_database(self):
        """Initialize permission tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Permission definitions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS permission_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                scope TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                actions TEXT NOT NULL,
                description TEXT,
                is_system BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # User permissions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                permission_name TEXT NOT NULL,
                resource_id TEXT,
                conditions TEXT,
                granted_by INTEGER,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (granted_by) REFERENCES users(id),
                UNIQUE(user_id, permission_name, resource_id)
            )
        """
        )

        # Role permissions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                permission_name TEXT NOT NULL,
                resource_id TEXT,
                conditions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id),
                UNIQUE(role_id, permission_name, resource_id)
            )
        """
        )

        # Device-specific permissions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                actions TEXT NOT NULL,
                granted_by INTEGER,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (granted_by) REFERENCES users(id),
                UNIQUE(user_id, device_id)
            )
        """
        )

        # Device groups
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                parent_group_id INTEGER,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_group_id) REFERENCES device_groups(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """
        )

        # Device group memberships
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_group_members (
                group_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, device_id),
                FOREIGN KEY (group_id) REFERENCES device_groups(id)
            )
        """
        )

        # Permission templates
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS permission_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                permissions TEXT NOT NULL,
                is_system BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Permission inheritance rules
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS permission_inheritance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_role_id INTEGER,
                child_role_id INTEGER,
                inherit_all BOOLEAN DEFAULT 1,
                specific_permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_role_id) REFERENCES roles(id),
                FOREIGN KEY (child_role_id) REFERENCES roles(id),
                UNIQUE(parent_role_id, child_role_id)
            )
        """
        )

        # Temporary permissions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS temporary_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                permission_name TEXT NOT NULL,
                resource_id TEXT,
                reason TEXT,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                revoked_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (granted_by) REFERENCES users(id)
            )
        """
        )

        conn.commit()
        conn.close()

    def _init_default_templates(self):
        """Initialize default permission templates."""
        templates = [
            PermissionTemplate(
                name="device_operator",
                description="Can view and control devices",
                permissions=[
                    Permission(
                        name="device.view",
                        scope=PermissionScope.DEVICE,
                        resource_type=ResourceType.DEVICE,
                        actions=[PermissionAction.READ],
                    ),
                    Permission(
                        name="device.control",
                        scope=PermissionScope.DEVICE,
                        resource_type=ResourceType.DEVICE,
                        actions=[PermissionAction.CONTROL, PermissionAction.UPDATE],
                    ),
                ],
                is_system=True,
            ),
            PermissionTemplate(
                name="device_admin",
                description="Full device management",
                permissions=[
                    Permission(
                        name="device.manage",
                        scope=PermissionScope.DEVICE,
                        resource_type=ResourceType.DEVICE,
                        actions=[
                            PermissionAction.CREATE,
                            PermissionAction.READ,
                            PermissionAction.UPDATE,
                            PermissionAction.DELETE,
                            PermissionAction.CONTROL,
                            PermissionAction.CONFIGURE,
                        ],
                    )
                ],
                is_system=True,
            ),
            PermissionTemplate(
                name="report_viewer",
                description="Can view and export reports",
                permissions=[
                    Permission(
                        name="report.view",
                        scope=PermissionScope.FEATURE,
                        resource_type=ResourceType.REPORT,
                        actions=[PermissionAction.READ, PermissionAction.EXPORT],
                    )
                ],
                is_system=True,
            ),
        ]

        for template in templates:
            self.create_template(template)

    def grant_permission(
        self,
        user_id: int,
        permission_name: str,
        resource_id: Optional[str] = None,
        conditions: Optional[Dict] = None,
        expires_at: Optional[datetime] = None,
        granted_by: Optional[int] = None,
    ) -> bool:
        """Grant permission to user.

        Args:
            user_id: User ID
            permission_name: Permission name
            resource_id: Optional resource ID
            conditions: Optional conditions
            expires_at: Optional expiration
            granted_by: User who granted permission

        Returns:
            True if granted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO user_permissions 
                (user_id, permission_name, resource_id, conditions, 
                 granted_by, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
                (
                    user_id,
                    permission_name,
                    resource_id,
                    json.dumps(conditions) if conditions else None,
                    granted_by,
                    expires_at,
                ),
            )

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def revoke_permission(
        self, user_id: int, permission_name: str, resource_id: Optional[str] = None
    ) -> bool:
        """Revoke permission from user.

        Args:
            user_id: User ID
            permission_name: Permission name
            resource_id: Optional resource ID

        Returns:
            True if revoked successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_permissions
            SET is_active = 0
            WHERE user_id = ? AND permission_name = ?
            AND (resource_id = ? OR (? IS NULL AND resource_id IS NULL))
        """,
            (user_id, permission_name, resource_id, resource_id),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def grant_device_permission(
        self,
        user_id: int,
        device_id: str,
        actions: List[PermissionAction],
        expires_at: Optional[datetime] = None,
        granted_by: Optional[int] = None,
    ) -> bool:
        """Grant device-specific permission.

        Args:
            user_id: User ID
            device_id: Device ID
            actions: List of allowed actions
            expires_at: Optional expiration
            granted_by: User who granted permission

        Returns:
            True if granted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO device_permissions 
                (user_id, device_id, actions, granted_by, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """,
                (
                    user_id,
                    device_id,
                    json.dumps([a.value for a in actions]),
                    granted_by,
                    expires_at,
                ),
            )

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def check_permission(
        self,
        user_id: int,
        action: PermissionAction,
        resource_type: ResourceType,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if user has permission.

        Args:
            user_id: User ID
            action: Requested action
            resource_type: Type of resource
            resource_id: Specific resource ID

        Returns:
            True if permission is granted
        """
        # Get user's direct permissions
        direct_perms = self._get_user_permissions(user_id)

        # Get user's role permissions
        role_perms = self._get_user_role_permissions(user_id)

        # Get device-specific permissions if applicable
        device_perms = []
        if resource_type == ResourceType.DEVICE and resource_id:
            device_perms = self._get_device_permissions(user_id, resource_id)

        # Combine all permissions
        all_perms = direct_perms + role_perms + device_perms

        # Check each permission
        for perm in all_perms:
            if perm.matches(action, resource_type, resource_id):
                return True

        # Check inherited permissions
        if self._check_inherited_permission(
            user_id, action, resource_type, resource_id
        ):
            return True

        return False

    def get_user_permissions(self, user_id: int) -> List[Dict]:
        """Get all permissions for a user.

        Args:
            user_id: User ID

        Returns:
            List of permissions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get direct permissions
        cursor.execute(
            """
            SELECT permission_name, resource_id, conditions, expires_at
            FROM user_permissions
            WHERE user_id = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        """,
            (user_id,),
        )

        permissions = []
        for row in cursor.fetchall():
            permissions.append(
                {
                    "name": row[0],
                    "resource_id": row[1],
                    "conditions": json.loads(row[2]) if row[2] else None,
                    "expires_at": row[3],
                    "source": "direct",
                }
            )

        # Get role permissions
        cursor.execute(
            """
            SELECT rp.permission_name, rp.resource_id, rp.conditions
            FROM role_permissions rp
            JOIN user_roles ur ON ur.role_id = rp.role_id
            WHERE ur.user_id = ?
        """,
            (user_id,),
        )

        for row in cursor.fetchall():
            permissions.append(
                {
                    "name": row[0],
                    "resource_id": row[1],
                    "conditions": json.loads(row[2]) if row[2] else None,
                    "source": "role",
                }
            )

        # Get device permissions
        cursor.execute(
            """
            SELECT device_id, actions, expires_at
            FROM device_permissions
            WHERE user_id = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        """,
            (user_id,),
        )

        for row in cursor.fetchall():
            permissions.append(
                {
                    "name": "device.specific",
                    "resource_id": row[0],
                    "actions": json.loads(row[1]),
                    "expires_at": row[2],
                    "source": "device",
                }
            )

        conn.close()
        return permissions

    def create_device_group(
        self,
        name: str,
        description: Optional[str] = None,
        parent_group_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> int:
        """Create a device group.

        Args:
            name: Group name
            description: Group description
            parent_group_id: Parent group for hierarchy
            created_by: User who created the group

        Returns:
            Group ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO device_groups 
            (name, description, parent_group_id, created_by)
            VALUES (?, ?, ?, ?)
        """,
            (name, description, parent_group_id, created_by),
        )

        group_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return group_id

    def add_device_to_group(self, group_id: int, device_id: str) -> bool:
        """Add device to group.

        Args:
            group_id: Group ID
            device_id: Device ID

        Returns:
            True if added successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO device_group_members (group_id, device_id)
                VALUES (?, ?)
            """,
                (group_id, device_id),
            )

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def grant_group_permission(
        self, user_id: int, group_id: int, actions: List[PermissionAction]
    ) -> bool:
        """Grant permission for all devices in a group.

        Args:
            user_id: User ID
            group_id: Device group ID
            actions: List of allowed actions

        Returns:
            True if granted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all devices in group (including hierarchy)
        devices = self._get_group_devices(group_id, include_subgroups=True)

        # Grant permission for each device
        success = True
        for device_id in devices:
            if not self.grant_device_permission(user_id, device_id, actions):
                success = False

        conn.close()
        return success

    def create_template(self, template: PermissionTemplate) -> bool:
        """Create permission template.

        Args:
            template: Permission template

        Returns:
            True if created successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Serialize permissions
            perms_data = []
            for perm in template.permissions:
                perms_data.append(
                    {
                        "name": perm.name,
                        "scope": perm.scope.value,
                        "resource_type": perm.resource_type.value,
                        "actions": [a.value for a in perm.actions],
                        "resource_id": perm.resource_id,
                        "conditions": perm.conditions,
                    }
                )

            cursor.execute(
                """
                INSERT OR IGNORE INTO permission_templates 
                (name, description, permissions, is_system)
                VALUES (?, ?, ?, ?)
            """,
                (
                    template.name,
                    template.description,
                    json.dumps(perms_data),
                    template.is_system,
                ),
            )

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def apply_template(
        self, user_id: int, template_name: str, resource_id: Optional[str] = None
    ) -> bool:
        """Apply permission template to user.

        Args:
            user_id: User ID
            template_name: Template name
            resource_id: Optional resource ID

        Returns:
            True if applied successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get template
        cursor.execute(
            """
            SELECT permissions FROM permission_templates
            WHERE name = ?
        """,
            (template_name,),
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        perms_data = json.loads(row[0])

        # Apply each permission
        success = True
        for perm_data in perms_data:
            perm_resource_id = resource_id or perm_data.get("resource_id")

            if not self.grant_permission(
                user_id=user_id,
                permission_name=perm_data["name"],
                resource_id=perm_resource_id,
                conditions=perm_data.get("conditions"),
            ):
                success = False

        conn.close()
        return success

    def setup_inheritance(
        self,
        parent_role_id: int,
        child_role_id: int,
        inherit_all: bool = True,
        specific_permissions: Optional[List[str]] = None,
    ) -> bool:
        """Setup permission inheritance between roles.

        Args:
            parent_role_id: Parent role ID
            child_role_id: Child role ID
            inherit_all: Inherit all permissions
            specific_permissions: Specific permissions to inherit

        Returns:
            True if setup successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO permission_inheritance 
                (parent_role_id, child_role_id, inherit_all, specific_permissions)
                VALUES (?, ?, ?, ?)
            """,
                (
                    parent_role_id,
                    child_role_id,
                    inherit_all,
                    json.dumps(specific_permissions) if specific_permissions else None,
                ),
            )

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def grant_temporary_permission(
        self,
        user_id: int,
        permission_name: str,
        duration_hours: int,
        reason: str,
        granted_by: int,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Grant temporary permission.

        Args:
            user_id: User ID
            permission_name: Permission name
            duration_hours: Duration in hours
            reason: Reason for temporary grant
            granted_by: User granting permission
            resource_id: Optional resource ID

        Returns:
            True if granted successfully
        """
        expires_at = datetime.now() + timedelta(hours=duration_hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO temporary_permissions 
            (user_id, permission_name, resource_id, reason, granted_by, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (user_id, permission_name, resource_id, reason, granted_by, expires_at),
        )

        success = cursor.rowcount > 0

        if success:
            # Also grant the actual permission
            self.grant_permission(
                user_id=user_id,
                permission_name=permission_name,
                resource_id=resource_id,
                expires_at=expires_at,
                granted_by=granted_by,
            )

        conn.commit()
        conn.close()

        return success

    def _get_user_permissions(self, user_id: int) -> List[Permission]:
        """Get user's direct permissions.

        Args:
            user_id: User ID

        Returns:
            List of permissions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pd.name, pd.scope, pd.resource_type, pd.actions,
                   up.resource_id, up.conditions, up.expires_at
            FROM user_permissions up
            JOIN permission_definitions pd ON pd.name = up.permission_name
            WHERE up.user_id = ? AND up.is_active = 1
            AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
        """,
            (user_id,),
        )

        permissions = []
        for row in cursor.fetchall():
            permissions.append(
                Permission(
                    name=row[0],
                    scope=PermissionScope(row[1]),
                    resource_type=ResourceType(row[2]),
                    actions=[PermissionAction(a) for a in json.loads(row[3])],
                    resource_id=row[4],
                    conditions=json.loads(row[5]) if row[5] else None,
                    expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
                )
            )

        conn.close()
        return permissions

    def _get_user_role_permissions(self, user_id: int) -> List[Permission]:
        """Get user's role-based permissions.

        Args:
            user_id: User ID

        Returns:
            List of permissions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pd.name, pd.scope, pd.resource_type, pd.actions,
                   rp.resource_id, rp.conditions
            FROM role_permissions rp
            JOIN permission_definitions pd ON pd.name = rp.permission_name
            JOIN user_roles ur ON ur.role_id = rp.role_id
            WHERE ur.user_id = ?
        """,
            (user_id,),
        )

        permissions = []
        for row in cursor.fetchall():
            permissions.append(
                Permission(
                    name=row[0],
                    scope=PermissionScope(row[1]),
                    resource_type=ResourceType(row[2]),
                    actions=[PermissionAction(a) for a in json.loads(row[3])],
                    resource_id=row[4],
                    conditions=json.loads(row[5]) if row[5] else None,
                )
            )

        conn.close()
        return permissions

    def _get_device_permissions(self, user_id: int, device_id: str) -> List[Permission]:
        """Get device-specific permissions.

        Args:
            user_id: User ID
            device_id: Device ID

        Returns:
            List of permissions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT actions, expires_at
            FROM device_permissions
            WHERE user_id = ? AND device_id = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        """,
            (user_id, device_id),
        )

        permissions = []
        row = cursor.fetchone()

        if row:
            permissions.append(
                Permission(
                    name=f"device.{device_id}",
                    scope=PermissionScope.DEVICE,
                    resource_type=ResourceType.DEVICE,
                    actions=[PermissionAction(a) for a in json.loads(row[0])],
                    resource_id=device_id,
                    expires_at=datetime.fromisoformat(row[1]) if row[1] else None,
                )
            )

        conn.close()
        return permissions

    def _check_inherited_permission(
        self,
        user_id: int,
        action: PermissionAction,
        resource_type: ResourceType,
        resource_id: Optional[str],
    ) -> bool:
        """Check inherited permissions.

        Args:
            user_id: User ID
            action: Requested action
            resource_type: Type of resource
            resource_id: Specific resource ID

        Returns:
            True if permission is inherited
        """
        # Get user's roles
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role_id FROM user_roles WHERE user_id = ?
        """,
            (user_id,),
        )

        role_ids = [row[0] for row in cursor.fetchall()]

        # Check inheritance for each role
        for role_id in role_ids:
            cursor.execute(
                """
                SELECT parent_role_id, inherit_all, specific_permissions
                FROM permission_inheritance
                WHERE child_role_id = ?
            """,
                (role_id,),
            )

            for parent_id, inherit_all, specific_perms in cursor.fetchall():
                if inherit_all:
                    # Check parent role permissions
                    parent_perms = self._get_role_permissions(parent_id)
                    for perm in parent_perms:
                        if perm.matches(action, resource_type, resource_id):
                            conn.close()
                            return True
                elif specific_perms:
                    # Check specific inherited permissions
                    perm_list = json.loads(specific_perms)
                    # TODO: Check if requested permission is in list

        conn.close()
        return False

    def _get_role_permissions(self, role_id: int) -> List[Permission]:
        """Get permissions for a role.

        Args:
            role_id: Role ID

        Returns:
            List of permissions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pd.name, pd.scope, pd.resource_type, pd.actions,
                   rp.resource_id, rp.conditions
            FROM role_permissions rp
            JOIN permission_definitions pd ON pd.name = rp.permission_name
            WHERE rp.role_id = ?
        """,
            (role_id,),
        )

        permissions = []
        for row in cursor.fetchall():
            permissions.append(
                Permission(
                    name=row[0],
                    scope=PermissionScope(row[1]),
                    resource_type=ResourceType(row[2]),
                    actions=[PermissionAction(a) for a in json.loads(row[3])],
                    resource_id=row[4],
                    conditions=json.loads(row[5]) if row[5] else None,
                )
            )

        conn.close()
        return permissions

    def _get_group_devices(
        self, group_id: int, include_subgroups: bool = False
    ) -> List[str]:
        """Get all devices in a group.

        Args:
            group_id: Group ID
            include_subgroups: Include devices from subgroups

        Returns:
            List of device IDs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        devices = []

        # Get direct members
        cursor.execute(
            """
            SELECT device_id FROM device_group_members
            WHERE group_id = ?
        """,
            (group_id,),
        )

        devices.extend([row[0] for row in cursor.fetchall()])

        if include_subgroups:
            # Get subgroups
            cursor.execute(
                """
                SELECT id FROM device_groups
                WHERE parent_group_id = ?
            """,
                (group_id,),
            )

            for (subgroup_id,) in cursor.fetchall():
                devices.extend(self._get_group_devices(subgroup_id, True))

        conn.close()
        return devices
