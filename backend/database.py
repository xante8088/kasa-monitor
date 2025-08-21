"""Database management for Kasa device monitoring.

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
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiosqlite
from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write_api import SYNCHRONOUS
from rate_calculator import RateCalculator

from auth import AuthManager
from models import (
    DeviceData,
    DeviceReading,
    ElectricityRate,
    RateType,
    User,
    UserCreate,
    UserRole,
)


class DatabaseManager:
    """Manages both SQLite and InfluxDB connections for device data storage."""

    def __init__(self):
        self.sqlite_path = os.getenv("SQLITE_PATH", "kasa_monitor.db")
        self.influx_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.influx_token = os.getenv("INFLUXDB_TOKEN", "")
        self.influx_org = os.getenv("INFLUXDB_ORG", "kasa-monitor")
        self.influx_bucket = os.getenv("INFLUXDB_BUCKET", "device-data")
        self.use_influx = bool(self.influx_token)

        self.sqlite_conn: Optional[aiosqlite.Connection] = None
        self.influx_client: Optional[InfluxDBClientAsync] = None

    async def initialize(self):
        """Initialize database connections and create tables."""
        # Initialize SQLite
        self.sqlite_conn = await aiosqlite.connect(self.sqlite_path)
        await self._create_sqlite_tables()

        # Initialize InfluxDB if configured
        if self.use_influx:
            self.influx_client = InfluxDBClientAsync(
                url=self.influx_url, token=self.influx_token, org=self.influx_org
            )

    async def close(self):
        """Close database connections."""
        if self.sqlite_conn:
            await self.sqlite_conn.close()
        if self.influx_client:
            await self.influx_client.close()

    async def _create_sqlite_tables(self):
        """Create SQLite tables for device data and configuration."""
        await self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_info (
                device_ip TEXT PRIMARY KEY,
                alias TEXT,
                model TEXT,
                device_type TEXT,
                mac TEXT,
                last_seen TIMESTAMP,
                metadata TEXT,
                is_monitored BOOLEAN DEFAULT 1,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_notes TEXT
            )
        """
        )

        await self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_ip TEXT,
                timestamp TIMESTAMP,
                is_on BOOLEAN,
                current_power_w REAL,
                voltage REAL,
                current REAL,
                today_energy_kwh REAL,
                month_energy_kwh REAL,
                total_energy_kwh REAL,
                rssi INTEGER,
                FOREIGN KEY (device_ip) REFERENCES device_info(device_ip)
            )
        """
        )

        await self.sqlite_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_device_readings_timestamp
            ON device_readings(device_ip, timestamp DESC)
        """
        )

        await self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS electricity_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                rate_type TEXT,
                rate_config TEXT,  -- JSON string containing full rate configuration
                currency TEXT DEFAULT 'USD',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        await self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_ip TEXT,
                date DATE,
                energy_kwh REAL,
                cost REAL,
                rate_id INTEGER,
                FOREIGN KEY (device_ip) REFERENCES device_info(device_ip),
                FOREIGN KEY (rate_id) REFERENCES electricity_rates(id)
            )
        """
        )

        await self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                permissions TEXT,  -- JSON string of custom permissions
                totp_secret TEXT,  -- TOTP secret for 2FA (when enabled)
                temp_totp_secret TEXT  -- Temporary TOTP secret (during setup)
            )
        """
        )

        await self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        await self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        await self.sqlite_conn.commit()

    async def store_device_reading(self, device_data: DeviceData):
        """Store device reading in both SQLite and InfluxDB."""
        # Update device info in SQLite
        await self.sqlite_conn.execute(
            """
            INSERT OR REPLACE INTO device_info
            (device_ip, alias, model, device_type, mac, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                device_data.ip,
                device_data.alias,
                device_data.model,
                device_data.device_type,
                device_data.mac,
                device_data.timestamp,
            ),
        )

        # Store reading in SQLite
        await self.sqlite_conn.execute(
            """
            INSERT INTO device_readings
            (device_ip, timestamp, is_on, current_power_w, voltage, current,
             today_energy_kwh, month_energy_kwh, total_energy_kwh, rssi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                device_data.ip,
                device_data.timestamp,
                device_data.is_on,
                device_data.current_power_w,
                device_data.voltage,
                device_data.current,
                device_data.today_energy_kwh,
                device_data.month_energy_kwh,
                device_data.total_energy_kwh,
                device_data.rssi,
            ),
        )

        await self.sqlite_conn.commit()

        # Store in InfluxDB if available
        if self.use_influx and self.influx_client:
            point = (
                Point("device_reading")
                .tag("device_ip", device_data.ip)
                .tag("alias", device_data.alias)
                .tag("model", device_data.model)
                .tag("device_type", device_data.device_type)
                .field("is_on", device_data.is_on)
                .field("current_power_w", device_data.current_power_w or 0)
                .field("voltage", device_data.voltage or 0)
                .field("current", device_data.current or 0)
                .field("today_energy_kwh", device_data.today_energy_kwh or 0)
                .field("month_energy_kwh", device_data.month_energy_kwh or 0)
                .field("total_energy_kwh", device_data.total_energy_kwh or 0)
                .field("rssi", device_data.rssi or 0)
                .time(device_data.timestamp)
            )

            write_api = self.influx_client.write_api()
            await write_api.write(bucket=self.influx_bucket, record=point)

    async def get_device_history(
        self,
        device_ip: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        interval: str = "1h",
    ) -> List[Dict[str, Any]]:
        """Get historical data for a device."""
        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(days=7)
        if not end_time:
            end_time = datetime.now(timezone.utc)

        # Use InfluxDB if available for better time-series queries
        if self.use_influx and self.influx_client:
            query_api = self.influx_client.query_api()
            query = f"""
                from(bucket: "{self.influx_bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => r["device_ip"] == "{device_ip}")
                |> filter(fn: (r) => r["_field"] == "current_power_w" or
                                     r["_field"] == "voltage" or
                                     r["_field"] == "today_energy_kwh")
                |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
                |> yield(name: "mean")
            """

            result = await query_api.query(query)
            return self._process_influx_results(result)
        else:
            # Fallback to SQLite
            cursor = await self.sqlite_conn.execute(
                """
                SELECT timestamp, current_power_w, voltage, current,
                       today_energy_kwh, month_energy_kwh, total_energy_kwh
                FROM device_readings
                WHERE device_ip = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
                LIMIT 1000
            """,
                (device_ip, start_time, end_time),
            )

            rows = await cursor.fetchall()
            return [
                {
                    "timestamp": row[0],
                    "current_power_w": row[1],
                    "voltage": row[2],
                    "current": row[3],
                    "today_energy_kwh": row[4],
                    "month_energy_kwh": row[5],
                    "total_energy_kwh": row[6],
                }
                for row in rows
            ]

    async def get_device_stats(self, device_ip: str) -> Dict[str, Any]:
        """Get statistics for a device."""
        cursor = await self.sqlite_conn.execute(
            """
            SELECT
                AVG(current_power_w) as avg_power,
                MAX(current_power_w) as max_power,
                MIN(current_power_w) as min_power,
                SUM(today_energy_kwh) as total_energy,
                COUNT(*) as reading_count
            FROM device_readings
            WHERE device_ip = ? AND timestamp > datetime('now', '-30 days')
        """,
            (device_ip,),
        )

        row = await cursor.fetchone()
        return {
            "avg_power": row[0],
            "max_power": row[1],
            "min_power": row[2],
            "total_energy": row[3],
            "reading_count": row[4],
        }

    async def get_electricity_rates(self) -> List[Dict[str, Any]]:
        """Get all electricity rate configurations."""
        cursor = await self.sqlite_conn.execute(
            """
            SELECT id, name, rate_type, rate_config, currency, is_active, created_at
            FROM electricity_rates
            WHERE is_active = 1
            ORDER BY created_at DESC
        """
        )

        rows = await cursor.fetchall()
        rates = []
        for row in rows:
            rate_dict = {
                "id": row[0],
                "name": row[1],
                "rate_type": row[2],
                "currency": row[4],
                "is_active": row[5],
                "created_at": row[6],
            }
            # Parse JSON config
            if row[3]:
                import json

                config = json.loads(row[3])
                rate_dict.update(config)
            rates.append(rate_dict)
        return rates

    async def set_electricity_rate(self, rate: ElectricityRate):
        """Set or update electricity rate configuration."""
        import json

        # Deactivate existing rates
        await self.sqlite_conn.execute(
            """
            UPDATE electricity_rates SET is_active = 0 WHERE is_active = 1
        """
        )

        # Serialize the rate configuration
        rate_config = json.dumps(rate.dict(exclude={"name", "rate_type", "currency"}))

        await self.sqlite_conn.execute(
            """
            INSERT INTO electricity_rates
            (name, rate_type, rate_config, currency)
            VALUES (?, ?, ?, ?)
        """,
            (
                rate.name,
                (
                    rate.rate_type.value
                    if hasattr(rate.rate_type, "value")
                    else rate.rate_type
                ),
                rate_config,
                rate.currency,
            ),
        )

        await self.sqlite_conn.commit()

    async def mark_device_inactive(self, device_ip: str):
        """Mark a device as inactive in the database."""
        async with self.sqlite_conn.execute(
            """UPDATE devices SET is_active = 0, last_seen = CURRENT_TIMESTAMP
               WHERE device_ip = ?""",
            (device_ip,),
        ) as cursor:
            await self.sqlite_conn.commit()

    async def get_saved_devices(self) -> List[Dict[str, Any]]:
        """Get list of all saved devices from database."""
        async with self.sqlite_conn.execute(
            """SELECT device_ip, device_name, device_type, is_active, last_seen
               FROM devices ORDER BY last_seen DESC"""
        ) as cursor:
            rows = await cursor.fetchall()

        devices = []
        for row in rows:
            devices.append(
                {
                    "ip": row[0],
                    "name": row[1],
                    "type": row[2],
                    "is_active": bool(row[3]),
                    "last_seen": row[4],
                }
            )
        return devices

    async def calculate_costs(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate electricity costs for all devices using enhanced rate calculator."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Get active rate
        rates = await self.get_electricity_rates()
        if not rates:
            return {"error": "No electricity rates configured"}

        rate_dict = rates[0]  # Use first active rate

        # Convert dict back to ElectricityRate model
        rate = ElectricityRate(**rate_dict)

        # Get detailed consumption data for cost calculation
        cursor = await self.sqlite_conn.execute(
            """
            SELECT
                device_ip,
                timestamp,
                current_power_w,
                today_energy_kwh,
                month_energy_kwh
            FROM device_readings
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY device_ip, timestamp
        """,
            (start_date, end_date),
        )

        rows = await cursor.fetchall()

        # Group by device and calculate costs
        device_data = {}
        for row in rows:
            device_ip, timestamp, power_w, daily_kwh, monthly_kwh = row

            if device_ip not in device_data:
                device_data[device_ip] = {
                    "readings": [],
                    "total_kwh": 0,
                    "peak_demand_kw": 0,
                    "costs": [],
                }

            if daily_kwh:
                device_data[device_ip]["readings"].append(
                    {
                        "timestamp": timestamp,
                        "kwh": daily_kwh,
                        "monthly_kwh": monthly_kwh,
                    }
                )
                device_data[device_ip]["total_kwh"] += daily_kwh

            if power_w:
                device_data[device_ip]["peak_demand_kw"] = max(
                    device_data[device_ip]["peak_demand_kw"], power_w / 1000
                )

        # Calculate costs for each device
        total_cost = 0
        device_costs = []

        for device_ip, data in device_data.items():
            device_cost = 0

            # Calculate cost for each reading based on time of use
            for reading in data["readings"]:
                timestamp = datetime.fromisoformat(reading["timestamp"])
                cost_breakdown = RateCalculator.calculate_cost(
                    reading["kwh"],
                    rate,
                    timestamp,
                    reading.get("monthly_kwh"),
                    data["peak_demand_kw"],
                )
                device_cost += cost_breakdown["total"]

            total_cost += device_cost

            device_costs.append(
                {
                    "device_ip": device_ip,
                    "total_kwh": data["total_kwh"],
                    "peak_demand_kw": data["peak_demand_kw"],
                    "cost": device_cost,
                    "currency": rate.currency,
                }
            )

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_cost": total_cost,
            "currency": rate.currency,
            "rate_type": rate.rate_type,
            "rate_name": rate.name,
            "device_costs": sorted(device_costs, key=lambda x: x["cost"], reverse=True),
        }

    def _process_influx_results(self, result) -> List[Dict[str, Any]]:
        """Process InfluxDB query results into a standard format."""
        processed = []
        for table in result:
            for record in table.records:
                processed.append(
                    {
                        "timestamp": record.get_time(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                    }
                )
        return processed

    async def get_saved_devices(self) -> List[Dict[str, Any]]:
        """Get all saved devices from the database."""
        cursor = await self.sqlite_conn.execute(
            """
            SELECT device_ip, alias, model, device_type, mac, last_seen,
                   is_monitored, discovered_at, user_notes
            FROM device_info
            ORDER BY alias
        """
        )

        rows = await cursor.fetchall()
        devices = []
        for row in rows:
            devices.append(
                {
                    "device_ip": row[0],
                    "alias": row[1],
                    "model": row[2],
                    "device_type": row[3],
                    "mac": row[4],
                    "last_seen": row[5],
                    "is_monitored": row[6],
                    "discovered_at": row[7],
                    "user_notes": row[8],
                }
            )
        return devices

    async def get_monitored_devices(self) -> List[Dict[str, Any]]:
        """Get only devices that are being monitored."""
        cursor = await self.sqlite_conn.execute(
            """
            SELECT device_ip, alias, model, device_type, mac, last_seen
            FROM device_info
            WHERE is_monitored = 1
            ORDER BY alias
        """
        )

        rows = await cursor.fetchall()
        devices = []
        for row in rows:
            devices.append(
                {
                    "device_ip": row[0],
                    "alias": row[1],
                    "model": row[2],
                    "device_type": row[3],
                    "mac": row[4],
                    "last_seen": row[5],
                }
            )
        return devices

    async def update_device_monitoring(
        self, device_ip: str, is_monitored: bool
    ) -> bool:
        """Enable or disable monitoring for a device."""
        try:
            await self.sqlite_conn.execute(
                """
                UPDATE device_info
                SET is_monitored = ?
                WHERE device_ip = ?
            """,
                (is_monitored, device_ip),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error updating device monitoring status: {e}")
            return False

    async def update_device_ip(self, old_ip: str, new_ip: str) -> bool:
        """Update a device's IP address."""
        try:
            # Check if new IP already exists
            cursor = await self.sqlite_conn.execute(
                "SELECT COUNT(*) FROM device_info WHERE device_ip = ?", (new_ip,)
            )
            count = await cursor.fetchone()
            if count[0] > 0:
                return False  # New IP already exists

            # Update device IP in device_info
            await self.sqlite_conn.execute(
                """
                UPDATE device_info
                SET device_ip = ?
                WHERE device_ip = ?
            """,
                (new_ip, old_ip),
            )

            # Update device IP in device_readings
            await self.sqlite_conn.execute(
                """
                UPDATE device_readings
                SET device_ip = ?
                WHERE device_ip = ?
            """,
                (new_ip, old_ip),
            )

            # Update device IP in device_costs
            await self.sqlite_conn.execute(
                """
                UPDATE device_costs
                SET device_ip = ?
                WHERE device_ip = ?
            """,
                (new_ip, old_ip),
            )

            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error updating device IP: {e}")
            await self.sqlite_conn.rollback()
            return False

    async def remove_device(self, device_ip: str) -> bool:
        """Remove a device and all its data from the database."""
        try:
            # Delete device readings
            await self.sqlite_conn.execute(
                "DELETE FROM device_readings WHERE device_ip = ?", (device_ip,)
            )

            # Delete device costs
            await self.sqlite_conn.execute(
                "DELETE FROM device_costs WHERE device_ip = ?", (device_ip,)
            )

            # Delete device info
            await self.sqlite_conn.execute(
                "DELETE FROM device_info WHERE device_ip = ?", (device_ip,)
            )

            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error removing device: {e}")
            await self.sqlite_conn.rollback()
            return False

    async def update_device_notes(self, device_ip: str, notes: str) -> bool:
        """Update user notes for a device."""
        try:
            await self.sqlite_conn.execute(
                """
                UPDATE device_info
                SET user_notes = ?
                WHERE device_ip = ?
            """,
                (notes, device_ip),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error updating device notes: {e}")
            return False

    async def create_admin_user(
        self, username: str, email: str, full_name: str, password: str
    ) -> bool:
        """Create the initial admin user."""
        try:
            # Check if any users exist
            cursor = await self.sqlite_conn.execute("SELECT COUNT(*) FROM users")
            count = await cursor.fetchone()

            if count[0] > 0:
                return False  # Admin already exists

            password_hash = AuthManager.hash_password(password)

            await self.sqlite_conn.execute(
                """
                INSERT INTO users (username, email, full_name, password_hash, role, is_admin)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (username, email, full_name, password_hash, UserRole.ADMIN.value, True),
            )

            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error creating admin user: {e}")
            return False

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            cursor = await self.sqlite_conn.execute(
                """
                SELECT id, username, email, full_name, role, is_active, is_admin,
                       created_at, last_login, permissions
                FROM users WHERE username = ? AND is_active = 1
            """,
                (username,),
            )

            row = await cursor.fetchone()
            if row:
                return User(
                    id=row[0],
                    username=row[1],
                    email=row[2],
                    full_name=row[3],
                    role=UserRole(row[4]),
                    is_active=row[5],
                    is_admin=row[6],
                    created_at=row[7],
                    last_login=row[8],
                    permissions=json.loads(row[9]) if row[9] else [],
                )
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    async def get_user_password_hash(self, username: str) -> Optional[str]:
        """Get user's password hash for authentication."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT password_hash FROM users WHERE username = ? AND is_active = 1",
                (username,),
            )
            row = await cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            # Log error without exposing sensitive details
            print("Error getting password hash: Database operation failed")
            return None

    async def update_user_login(self, username: str) -> bool:
        """Update user's last login timestamp."""
        try:
            await self.sqlite_conn.execute(
                """
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE username = ?
            """,
                (username,),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error updating login time: {e}")
            return False

    async def create_user(self, user_create: UserCreate) -> Optional[User]:
        """Create a new user."""
        try:
            password_hash = AuthManager.hash_password(user_create.password)

            await self.sqlite_conn.execute(
                """
                INSERT INTO users (username, email, full_name, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    user_create.username,
                    user_create.email,
                    user_create.full_name,
                    password_hash,
                    user_create.role.value,
                ),
            )

            await self.sqlite_conn.commit()

            # Return the created user
            return await self.get_user_by_username(user_create.username)
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    async def get_all_users(self) -> List[User]:
        """Get all users."""
        try:
            cursor = await self.sqlite_conn.execute(
                """
                SELECT id, username, email, full_name, role, is_active, is_admin,
                       created_at, last_login, permissions
                FROM users
                ORDER BY created_at DESC
            """
            )

            rows = await cursor.fetchall()
            users = []
            for row in rows:
                users.append(
                    User(
                        id=row[0],
                        username=row[1],
                        email=row[2],
                        full_name=row[3],
                        role=UserRole(row[4]),
                        is_active=row[5],
                        is_admin=row[6],
                        created_at=row[7],
                        last_login=row[8],
                        permissions=json.loads(row[9]) if row[9] else [],
                    )
                )
            return users
        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    async def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user information."""
        try:
            set_clauses = []
            values = []

            allowed_updates = ["email", "full_name", "role", "is_active", "permissions"]

            for key, value in updates.items():
                if key in allowed_updates:
                    set_clauses.append(f"{key} = ?")
                    if key == "permissions":
                        values.append(json.dumps(value))
                    elif key == "role":
                        values.append(
                            value.value if isinstance(value, UserRole) else value
                        )
                    else:
                        values.append(value)

            if not set_clauses:
                return False

            values.append(user_id)

            await self.sqlite_conn.execute(
                f"""
                UPDATE users SET {', '.join(set_clauses)}
                WHERE id = ?
            """,
                values,
            )

            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user (soft delete - set inactive)."""
        try:
            await self.sqlite_conn.execute(
                "UPDATE users SET is_active = 0 WHERE id = ?", (user_id,)
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    async def is_setup_required(self) -> bool:
        """Check if initial setup is required (no admin users exist)."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_admin = 1 AND is_active = 1"
            )
            count = await cursor.fetchone()
            return count[0] == 0
        except Exception:
            return True

    async def set_system_config(self, key: str, value: str) -> bool:
        """Set a system configuration value."""
        try:
            await self.sqlite_conn.execute(
                """
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (key, value),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error setting config: {e}")
            return False

    async def get_system_config(self, key: str, default: str = None) -> Optional[str]:
        """Get a system configuration value."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT value FROM system_config WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else default
        except Exception as e:
            print(f"Error getting config: {e}")
            return default

    async def get_all_system_config(self) -> Dict[str, str]:
        """Get all system configuration values."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT key, value FROM system_config"
            )
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}
        except Exception as e:
            print(f"Error getting all config: {e}")
            return {}

    # Profile management methods
    async def update_user_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user profile fields."""
        try:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [user_id]

            await self.sqlite_conn.execute(
                f"""
                UPDATE users
                SET {set_clause}
                WHERE id = ?
            """,
                values,
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False

    async def update_user_password(self, user_id: int, hashed_password: str) -> bool:
        """Update user password."""
        try:
            await self.sqlite_conn.execute(
                """
                UPDATE users
                SET password_hash = ?, last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (hashed_password, user_id),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            # Log error without exposing sensitive details
            print("Error updating password: Database operation failed")
            return False

    async def count_admin_users(self) -> int:
        """Count the number of admin users."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            )
            count = await cursor.fetchone()
            return count[0] if count else 0
        except Exception as e:
            print(f"Error counting admin users: {e}")
            return 0

    # 2FA methods
    async def get_user_totp_secret(self, user_id: int) -> Optional[str]:
        """Get user's TOTP secret if 2FA is enabled."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT totp_secret FROM users WHERE id = ? AND totp_secret IS NOT NULL",
                (user_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            # Log error without exposing sensitive details
            print("Error getting TOTP secret: Database operation failed")
            return None

    async def store_temp_totp_secret(self, user_id: int, secret: str) -> bool:
        """Store temporary TOTP secret (not confirmed yet)."""
        try:
            await self.sqlite_conn.execute(
                """
                UPDATE users
                SET temp_totp_secret = ?
                WHERE id = ?
            """,
                (secret, user_id),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            # Log error without exposing sensitive details
            print("Error storing temp TOTP secret: Database operation failed")
            return False

    async def get_temp_totp_secret(self, user_id: int) -> Optional[str]:
        """Get temporary TOTP secret."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT temp_totp_secret FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None
        except Exception as e:
            # Log error without exposing sensitive details
            print("Error getting temp TOTP secret: Database operation failed")
            return None

    async def confirm_totp_secret(self, user_id: int, secret: str) -> bool:
        """Confirm TOTP secret and enable 2FA."""
        try:
            await self.sqlite_conn.execute(
                """
                UPDATE users
                SET totp_secret = ?, temp_totp_secret = NULL
                WHERE id = ?
            """,
                (secret, user_id),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            # Log error without exposing sensitive details
            print("Error confirming TOTP secret: Database operation failed")
            return False

    async def disable_totp(self, user_id: int) -> bool:
        """Disable 2FA for user."""
        try:
            cursor = await self.sqlite_conn.execute(
                "SELECT totp_secret FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if not row or not row[0]:
                return False  # 2FA not enabled

            await self.sqlite_conn.execute(
                """
                UPDATE users
                SET totp_secret = NULL, temp_totp_secret = NULL
                WHERE id = ?
            """,
                (user_id,),
            )
            await self.sqlite_conn.commit()
            return True
        except Exception as e:
            print(f"Error disabling TOTP: {e}")
            return False
