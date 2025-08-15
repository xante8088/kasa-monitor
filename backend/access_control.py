"""IP-based and Time-based Access Control.

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

import ipaddress
import json
import sqlite3
from datetime import datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import geoip2.database
import geoip2.errors
import pytz
from fastapi import HTTPException, Request, status


class AccessRule(Enum):
    """Access control rule types."""

    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"  # Require additional auth


class IPAccessControl:
    """IP-based access control with whitelist/blacklist and geo-blocking."""

    def __init__(
        self, db_path: str = "kasa_monitor.db", geoip_db_path: Optional[str] = None
    ):
        """Initialize IP access control.

        Args:
            db_path: Path to database
            geoip_db_path: Optional path to MaxMind GeoIP2 database
        """
        self.db_path = db_path
        self.geoip_reader = None

        if geoip_db_path and Path(geoip_db_path).exists():
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
            except Exception:
                pass

        self._init_database()

    def _init_database(self):
        """Initialize IP access control tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # IP rules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ip_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT,
                cidr_range TEXT,
                rule_type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                created_by INTEGER,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """
        )

        # Geo-blocking rules
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS geo_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_code TEXT,
                region_code TEXT,
                city TEXT,
                rule_type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """
        )

        # Per-user IP restrictions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_ip_restrictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ip_address TEXT,
                cidr_range TEXT,
                rule_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Dynamic IP updates (for services with changing IPs)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dynamic_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT UNIQUE NOT NULL,
                current_ip TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                update_token TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """
        )

        conn.commit()
        conn.close()

    def add_ip_rule(
        self,
        ip_or_cidr: str,
        rule_type: AccessRule,
        description: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> bool:
        """Add IP access rule.

        Args:
            ip_or_cidr: IP address or CIDR range
            rule_type: Allow or deny
            description: Optional description
            expires_in_hours: Optional expiration time
            created_by: User ID who created the rule

        Returns:
            True if added successfully
        """
        try:
            # Validate IP/CIDR
            if "/" in ip_or_cidr:
                ipaddress.ip_network(ip_or_cidr, strict=False)
                ip_address = None
                cidr_range = ip_or_cidr
            else:
                ipaddress.ip_address(ip_or_cidr)
                ip_address = ip_or_cidr
                cidr_range = None

            expires_at = None
            if expires_in_hours:
                expires_at = datetime.now() + timedelta(hours=expires_in_hours)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO ip_rules 
                (ip_address, cidr_range, rule_type, description, expires_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    ip_address,
                    cidr_range,
                    rule_type.value,
                    description,
                    expires_at,
                    created_by,
                ),
            )

            conn.commit()
            conn.close()
            return True
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            return False

    def check_ip_access(self, ip: str, user_id: Optional[int] = None) -> AccessRule:
        """Check if IP is allowed access.

        Args:
            ip: IP address to check
            user_id: Optional user ID for user-specific rules

        Returns:
            Access rule (allow/deny/challenge)
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ipaddress.AddressValueError:
            return AccessRule.DENY

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check global IP rules
            cursor.execute(
                """
                SELECT rule_type FROM ip_rules
                WHERE is_active = 1
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                AND (ip_address = ? OR cidr_range IS NOT NULL)
                ORDER BY created_at DESC
            """,
                (ip,),
            )

            for row in cursor.fetchall():
                rule_type = row[0]
                # Direct IP match
                if rule_type:
                    return AccessRule(rule_type)

            # Check CIDR ranges
            cursor.execute(
                """
                SELECT cidr_range, rule_type FROM ip_rules
                WHERE is_active = 1
                AND cidr_range IS NOT NULL
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """
            )

            for cidr_range, rule_type in cursor.fetchall():
                try:
                    network = ipaddress.ip_network(cidr_range, strict=False)
                    if ip_obj in network:
                        return AccessRule(rule_type)
                except Exception:
                    continue

            # Check user-specific rules if user_id provided
            if user_id:
                cursor.execute(
                    """
                    SELECT ip_address, cidr_range, rule_type FROM user_ip_restrictions
                    WHERE user_id = ? AND is_active = 1
                """,
                    (user_id,),
                )

                for ip_addr, cidr_range, rule_type in cursor.fetchall():
                    if ip_addr == ip:
                        return AccessRule(rule_type)
                    elif cidr_range:
                        try:
                            network = ipaddress.ip_network(cidr_range, strict=False)
                            if ip_obj in network:
                                return AccessRule(rule_type)
                        except Exception:
                            continue

            # Check geo-blocking rules if GeoIP is available
            if self.geoip_reader:
                geo_rule = self._check_geo_rules(ip)
                if geo_rule:
                    return geo_rule

            # Default to allow if no rules match
            return AccessRule.ALLOW
        finally:
            conn.close()

    def _check_geo_rules(self, ip: str) -> Optional[AccessRule]:
        """Check geo-blocking rules for an IP.

        Args:
            ip: IP address to check

        Returns:
            Access rule if geo-rule matches, None otherwise
        """
        if not self.geoip_reader:
            return None

        try:
            response = self.geoip_reader.city(ip)
            country_code = response.country.iso_code
            region_code = (
                response.subdivisions.most_specific.iso_code
                if response.subdivisions
                else None
            )
            city = response.city.name

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check country rules
            cursor.execute(
                """
                SELECT rule_type FROM geo_rules
                WHERE is_active = 1
                AND country_code = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (country_code,),
            )

            row = cursor.fetchone()
            if row:
                return AccessRule(row[0])

            # Check region rules
            if region_code:
                cursor.execute(
                    """
                    SELECT rule_type FROM geo_rules
                    WHERE is_active = 1
                    AND country_code = ? AND region_code = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (country_code, region_code),
                )

                row = cursor.fetchone()
                if row:
                    return AccessRule(row[0])

            conn.close()
        except geoip2.errors.AddressNotFoundError:
            pass
        except Exception:
            pass

        return None

    def add_geo_rule(
        self,
        country_code: Optional[str] = None,
        region_code: Optional[str] = None,
        city: Optional[str] = None,
        rule_type: AccessRule = AccessRule.DENY,
        description: Optional[str] = None,
    ) -> bool:
        """Add geo-blocking rule.

        Args:
            country_code: ISO country code (e.g., 'US')
            region_code: ISO region code
            city: City name
            rule_type: Allow or deny
            description: Optional description

        Returns:
            True if added successfully
        """
        if not any([country_code, region_code, city]):
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO geo_rules 
            (country_code, region_code, city, rule_type, description)
            VALUES (?, ?, ?, ?, ?)
        """,
            (country_code, region_code, city, rule_type.value, description),
        )

        conn.commit()
        conn.close()
        return True

    def update_dynamic_ip(self, service_name: str, new_ip: str, token: str) -> bool:
        """Update dynamic IP for a service.

        Args:
            service_name: Name of the service
            new_ip: New IP address
            token: Update token for authentication

        Returns:
            True if updated successfully
        """
        try:
            ipaddress.ip_address(new_ip)
        except ipaddress.AddressValueError:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE dynamic_ips
            SET current_ip = ?, last_updated = CURRENT_TIMESTAMP
            WHERE service_name = ? AND update_token = ? AND is_active = 1
        """,
            (new_ip, service_name, token),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success


class TimeBasedAccessControl:
    """Time-based access control with schedules and timezones."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize time-based access control.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize time-based access control tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Access schedules
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS access_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_id INTEGER,
                role TEXT,
                timezone TEXT DEFAULT 'UTC',
                schedule_data TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Temporary access grants
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS temporary_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                granted_by INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                permissions TEXT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (granted_by) REFERENCES users(id)
            )
        """
        )

        # Holiday/exception dates
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS access_exceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                exception_type TEXT NOT NULL,
                description TEXT,
                applies_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def add_schedule(
        self,
        name: str,
        schedule_data: Dict[str, Any],
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        timezone: str = "UTC",
    ) -> int:
        """Add access schedule.

        Args:
            name: Schedule name
            schedule_data: Schedule configuration
            user_id: Optional user ID
            role: Optional role name
            timezone: Timezone for schedule

        Returns:
            Schedule ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO access_schedules 
            (name, user_id, role, timezone, schedule_data)
            VALUES (?, ?, ?, ?, ?)
        """,
            (name, user_id, role, timezone, json.dumps(schedule_data)),
        )

        schedule_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return schedule_id

    def check_time_access(
        self,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        check_time: Optional[datetime] = None,
    ) -> bool:
        """Check if access is allowed at current/specified time.

        Args:
            user_id: Optional user ID
            role: Optional role
            check_time: Time to check (defaults to now)

        Returns:
            True if access is allowed
        """
        if not check_time:
            check_time = datetime.now(pytz.UTC)

        # Check temporary access first
        if user_id and self._check_temporary_access(user_id, check_time):
            return True

        # Check exceptions (holidays, etc.)
        if self._check_exceptions(check_time.date()):
            return False

        # Check schedules
        return self._check_schedules(user_id, role, check_time)

    def _check_temporary_access(self, user_id: int, check_time: datetime) -> bool:
        """Check if user has temporary access grant.

        Args:
            user_id: User ID
            check_time: Time to check

        Returns:
            True if temporary access is active
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM temporary_access
            WHERE user_id = ?
            AND is_active = 1
            AND start_time <= ?
            AND end_time >= ?
        """,
            (user_id, check_time, check_time),
        )

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    def _check_exceptions(self, check_date: Any) -> bool:
        """Check if date is an exception (holiday, etc.).

        Args:
            check_date: Date to check

        Returns:
            True if date is an exception
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT exception_type FROM access_exceptions
            WHERE date = ?
        """,
            (check_date,),
        )

        result = cursor.fetchone()
        conn.close()

        return result is not None

    def _check_schedules(
        self, user_id: Optional[int], role: Optional[str], check_time: datetime
    ) -> bool:
        """Check access schedules.

        Args:
            user_id: Optional user ID
            role: Optional role
            check_time: Time to check

        Returns:
            True if access is allowed by schedule
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get applicable schedules
        query = """
            SELECT timezone, schedule_data FROM access_schedules
            WHERE is_active = 1
        """
        params = []

        if user_id:
            query += " AND (user_id = ? OR user_id IS NULL)"
            params.append(user_id)

        if role:
            query += " AND (role = ? OR role IS NULL)"
            params.append(role)

        query += " ORDER BY priority DESC"

        cursor.execute(query, params)

        for timezone_str, schedule_data_json in cursor.fetchall():
            schedule_data = json.loads(schedule_data_json)

            # Convert check_time to schedule's timezone
            tz = pytz.timezone(timezone_str)
            local_time = check_time.astimezone(tz)

            # Check if current time matches schedule
            if self._matches_schedule(local_time, schedule_data):
                conn.close()
                return True

        conn.close()
        return False

    def _matches_schedule(self, check_time: datetime, schedule: Dict) -> bool:
        """Check if time matches schedule rules.

        Args:
            check_time: Time to check
            schedule: Schedule configuration

        Returns:
            True if time matches schedule
        """
        # Check day of week
        day_name = check_time.strftime("%A").lower()
        if day_name not in schedule.get("days", []):
            return False

        # Check time range
        current_time = check_time.time()

        for time_range in schedule.get("time_ranges", []):
            start_time = time.fromisoformat(time_range["start"])
            end_time = time.fromisoformat(time_range["end"])

            if start_time <= current_time <= end_time:
                return True

        return False

    def grant_temporary_access(
        self,
        user_id: int,
        granted_by: int,
        duration_hours: int,
        permissions: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Grant temporary access to a user.

        Args:
            user_id: User to grant access to
            granted_by: User granting access
            duration_hours: Duration in hours
            permissions: Optional specific permissions
            reason: Optional reason for grant

        Returns:
            Grant ID
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO temporary_access 
            (user_id, granted_by, start_time, end_time, permissions, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                granted_by,
                start_time,
                end_time,
                json.dumps(permissions) if permissions else None,
                reason,
            ),
        )

        grant_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return grant_id
