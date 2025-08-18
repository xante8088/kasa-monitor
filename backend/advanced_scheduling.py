"""Advanced scheduling system with complex rules and triggers.

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

import asyncio
import json
import random
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import croniter
import pytz


# Patch timezone handling for CST6CDT and similar issues
def patch_timezone_handling():
    """Patch timezone handling to work around CST6CDT and similar issues."""
    timezone_mapping = {
        "CST6CDT": "America/Chicago",
        "EST5EDT": "America/New_York",
        "MST7MDT": "America/Denver",
        "PST8PDT": "America/Los_Angeles",
        "HST10": "Pacific/Honolulu",
        "AKST9AKDT": "America/Anchorage",
    }

    original_timezone = pytz.timezone

    def patched_timezone(zone):
        try:
            return original_timezone(zone)
        except pytz.exceptions.UnknownTimeZoneError:
            if zone in timezone_mapping:
                return original_timezone(timezone_mapping[zone])
            return original_timezone("UTC")

    pytz.timezone = patched_timezone


patch_timezone_handling()

from astral import LocationInfo
from astral.sun import sun


class ScheduleType(Enum):
    """Schedule types."""

    SIMPLE = "simple"
    CRON = "cron"
    SOLAR = "solar"
    TEMPLATE = "template"
    HOLIDAY = "holiday"
    ADAPTIVE = "adaptive"


class TriggerType(Enum):
    """Trigger types for schedules."""

    TIME = "time"
    SUNRISE = "sunrise"
    SUNSET = "sunset"
    CIVIL_DAWN = "civil_dawn"
    CIVIL_DUSK = "civil_dusk"
    SENSOR = "sensor"
    EVENT = "event"
    CONDITION = "condition"


class ActionType(Enum):
    """Schedule action types."""

    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    TOGGLE = "toggle"
    SET_BRIGHTNESS = "set_brightness"
    SET_COLOR = "set_color"
    SET_TEMPERATURE = "set_temperature"
    EXECUTE_SCENE = "execute_scene"
    CUSTOM = "custom"


@dataclass
class ScheduleRule:
    """Advanced schedule rule."""

    name: str
    description: str
    schedule_type: ScheduleType
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]
    action_type: ActionType
    action_config: Dict[str, Any]
    devices: List[str]
    groups: Optional[List[int]] = None
    conditions: Optional[List[Dict]] = None
    random_delay: Optional[int] = None  # Random delay in seconds
    retry_on_failure: bool = True
    retry_count: int = 3
    enabled: bool = True
    priority: int = 0
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    timezone: str = "UTC"
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["schedule_type"] = self.schedule_type.value
        data["trigger_type"] = self.trigger_type.value
        data["action_type"] = self.action_type.value
        if self.valid_from:
            data["valid_from"] = self.valid_from.isoformat()
        if self.valid_until:
            data["valid_until"] = self.valid_until.isoformat()
        return data


@dataclass
class ScheduleTemplate:
    """Reusable schedule template."""

    name: str
    description: str
    category: str
    rules: List[Dict[str, Any]]
    variables: Optional[Dict[str, Any]] = None
    icon: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class AdvancedScheduler:
    """Advanced scheduling system."""

    def __init__(
        self, db_path: str = "kasa_monitor.db", location: Optional[LocationInfo] = None
    ):
        """Initialize scheduler.

        Args:
            db_path: Path to database
            location: Location info for solar calculations
        """
        self.db_path = db_path
        self.location = location or LocationInfo("Default", "Default", "UTC", 0, 0)
        self.schedules = {}
        self.running = False
        self.scheduler_task = None

        self._init_database()
        self._load_schedules()

    def _init_database(self):
        """Initialize schedule tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Schedule rules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schedule_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                schedule_type TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_config TEXT NOT NULL,
                devices TEXT NOT NULL,
                groups TEXT,
                conditions TEXT,
                random_delay INTEGER,
                retry_on_failure BOOLEAN DEFAULT 1,
                retry_count INTEGER DEFAULT 3,
                enabled BOOLEAN DEFAULT 1,
                priority INTEGER DEFAULT 0,
                valid_from TIMESTAMP,
                valid_until TIMESTAMP,
                timezone TEXT DEFAULT 'UTC',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Schedule templates table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schedule_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                rules TEXT NOT NULL,
                variables TEXT,
                icon TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Schedule execution history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schedule_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER NOT NULL,
                triggered_at TIMESTAMP NOT NULL,
                executed_at TIMESTAMP,
                action_type TEXT NOT NULL,
                devices_affected TEXT,
                success BOOLEAN,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (schedule_id) REFERENCES schedule_rules(id)
            )
        """
        )

        # Holiday schedules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS holiday_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holiday_name TEXT NOT NULL,
                country_code TEXT DEFAULT 'US',
                schedule_id INTEGER NOT NULL,
                year INTEGER,
                enabled BOOLEAN DEFAULT 1,
                FOREIGN KEY (schedule_id) REFERENCES schedule_rules(id),
                UNIQUE(holiday_name, year, schedule_id)
            )
        """
        )

        # Schedule conflicts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schedule_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule1_id INTEGER NOT NULL,
                schedule2_id INTEGER NOT NULL,
                conflict_type TEXT NOT NULL,
                conflict_time TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolution TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (schedule1_id) REFERENCES schedule_rules(id),
                FOREIGN KEY (schedule2_id) REFERENCES schedule_rules(id)
            )
        """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedule_enabled ON schedule_rules(enabled)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedule_type ON "
            "schedule_rules(schedule_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_schedule ON "
            "schedule_executions(schedule_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_execution_time ON "
            "schedule_executions(triggered_at)"
        )

        # Insert default templates
        self._create_default_templates(cursor)

        conn.commit()
        conn.close()

    def _create_default_templates(self, cursor):
        """Create default schedule templates."""
        templates = [
            {
                "name": "Sunrise/Sunset Lights",
                "description": "Turn lights on at sunset and off at sunrise",
                "category": "lighting",
                "rules": json.dumps(
                    [
                        {
                            "trigger_type": "sunset",
                            "action_type": "turn_on",
                            "offset_minutes": -30,
                        },
                        {
                            "trigger_type": "sunrise",
                            "action_type": "turn_off",
                            "offset_minutes": 30,
                        },
                    ]
                ),
                "icon": "sun",
            },
            {
                "name": "Vacation Mode",
                "description": "Random on/off pattern to simulate presence",
                "category": "security",
                "rules": json.dumps(
                    [
                        {
                            "trigger_type": "time",
                            "time": "19:00",
                            "action_type": "turn_on",
                            "random_delay": 1800,
                        },
                        {
                            "trigger_type": "time",
                            "time": "23:00",
                            "action_type": "turn_off",
                            "random_delay": 3600,
                        },
                    ]
                ),
                "icon": "beach",
            },
            {
                "name": "Holiday Lights",
                "description": "Special schedule for holiday decorations",
                "category": "seasonal",
                "rules": json.dumps(
                    [
                        {"trigger_type": "sunset", "action_type": "turn_on"},
                        {
                            "trigger_type": "time",
                            "time": "00:00",
                            "action_type": "turn_off",
                        },
                    ]
                ),
                "icon": "star",
            },
        ]

        for template in templates:
            cursor.execute(
                """
                INSERT OR IGNORE INTO schedule_templates
                (name, description, category, rules, icon)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    template["name"],
                    template["description"],
                    template["category"],
                    template["rules"],
                    template["icon"],
                ),
            )

    def create_schedule(self, schedule: ScheduleRule) -> int:
        """Create a new schedule.

        Args:
            schedule: Schedule rule to create

        Returns:
            Schedule ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO schedule_rules
                (name, description, schedule_type, trigger_type, trigger_config,
                 action_type, action_config, devices, groups, conditions,
                 random_delay, retry_on_failure, retry_count, enabled, priority,
                 valid_from, valid_until, timezone, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    schedule.name,
                    schedule.description,
                    schedule.schedule_type.value,
                    schedule.trigger_type.value,
                    json.dumps(schedule.trigger_config),
                    schedule.action_type.value,
                    json.dumps(schedule.action_config),
                    json.dumps(schedule.devices),
                    json.dumps(schedule.groups) if schedule.groups else None,
                    json.dumps(schedule.conditions) if schedule.conditions else None,
                    schedule.random_delay,
                    schedule.retry_on_failure,
                    schedule.retry_count,
                    schedule.enabled,
                    schedule.priority,
                    schedule.valid_from,
                    schedule.valid_until,
                    schedule.timezone,
                    json.dumps(schedule.metadata) if schedule.metadata else None,
                ),
            )

            schedule_id = cursor.lastrowid
            conn.commit()

            # Add to in-memory schedules
            self.schedules[schedule_id] = schedule

            # Check for conflicts
            self._check_schedule_conflicts(schedule_id)

            return schedule_id

        except sqlite3.IntegrityError:
            return 0
        finally:
            conn.close()

    def update_schedule(self, schedule_id: int, updates: Dict) -> bool:
        """Update schedule.

        Args:
            schedule_id: Schedule ID
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build update query
        fields = []
        values = []

        for key, value in updates.items():
            fields.append(f"{key} = ?")
            if key in [
                "trigger_config",
                "action_config",
                "devices",
                "groups",
                "conditions",
                "metadata",
            ]:
                values.append(json.dumps(value) if value else None)
            elif key in ["schedule_type", "trigger_type", "action_type"]:
                values.append(value.value if isinstance(value, Enum) else value)
            else:
                values.append(value)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(schedule_id)

        query = f"UPDATE schedule_rules SET {', '.join(fields)} WHERE id = ?"

        cursor.execute(query, values)
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        # Reload schedules
        if success:
            self._load_schedules()
            self._check_schedule_conflicts(schedule_id)

        return success

    def delete_schedule(self, schedule_id: int) -> bool:
        """Delete schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM schedule_rules WHERE id = ?", (schedule_id,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()

        # Remove from in-memory schedules
        if success and schedule_id in self.schedules:
            del self.schedules[schedule_id]

        return success

    async def start(self):
        """Start the scheduler."""
        if self.running:
            return

        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.scheduler_task:
            await self.scheduler_task

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                # Check and execute schedules
                await self._check_schedules()

                # Sleep for a short interval
                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _check_schedules(self):
        """Check and execute due schedules."""
        now = datetime.now()

        for schedule_id, schedule in self.schedules.items():
            if not schedule.enabled:
                continue

            # Check validity period
            if schedule.valid_from and now < schedule.valid_from:
                continue
            if schedule.valid_until and now > schedule.valid_until:
                continue

            # Check if schedule should trigger
            if await self._should_trigger(schedule, now):
                # Check conditions
                if schedule.conditions and not self._evaluate_conditions(
                    schedule.conditions
                ):
                    continue

                # Execute schedule
                await self._execute_schedule(schedule_id, schedule)

    async def _should_trigger(self, schedule: ScheduleRule, now: datetime) -> bool:
        """Check if schedule should trigger.

        Args:
            schedule: Schedule rule
            now: Current time

        Returns:
            True if should trigger
        """
        tz = pytz.timezone(schedule.timezone)
        local_now = now.astimezone(tz)

        if schedule.trigger_type == TriggerType.TIME:
            # Simple time trigger
            trigger_time = schedule.trigger_config.get("time")
            if trigger_time:
                hour, minute = map(int, trigger_time.split(":"))
                if local_now.hour == hour and local_now.minute == minute:
                    return self._check_last_execution(schedule, now)

        elif schedule.trigger_type in [
            TriggerType.SUNRISE,
            TriggerType.SUNSET,
            TriggerType.CIVIL_DAWN,
            TriggerType.CIVIL_DUSK,
        ]:
            # Solar trigger
            return await self._check_solar_trigger(schedule, local_now)

        elif schedule.schedule_type == ScheduleType.CRON:
            # Cron expression
            cron_expr = schedule.trigger_config.get("cron")
            if cron_expr:
                cron = croniter.croniter(cron_expr, local_now)
                prev_run = cron.get_prev(datetime)
                if (now - prev_run).total_seconds() < 60:
                    return self._check_last_execution(schedule, now)

        return False

    async def _check_solar_trigger(
        self, schedule: ScheduleRule, local_now: datetime
    ) -> bool:
        """Check solar-based trigger.

        Args:
            schedule: Schedule rule
            local_now: Current local time

        Returns:
            True if should trigger
        """
        s = sun(self.location.observer, date=local_now.date())

        trigger_times = {
            TriggerType.SUNRISE: s["sunrise"],
            TriggerType.SUNSET: s["sunset"],
            TriggerType.CIVIL_DAWN: s["dawn"],
            TriggerType.CIVIL_DUSK: s["dusk"],
        }

        trigger_time = trigger_times.get(schedule.trigger_type)
        if not trigger_time:
            return False

        # Apply offset if specified
        offset_minutes = schedule.trigger_config.get("offset_minutes", 0)
        trigger_time += timedelta(minutes=offset_minutes)

        # Check if within trigger window (1 minute)
        time_diff = abs((local_now - trigger_time).total_seconds())
        if time_diff < 60:
            return self._check_last_execution(schedule, local_now)

        return False

    def _check_last_execution(self, schedule: ScheduleRule, now: datetime) -> bool:
        """Check if schedule was recently executed.

        Args:
            schedule: Schedule rule
            now: Current time

        Returns:
            True if not recently executed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check last execution
        cursor.execute(
            """
            SELECT triggered_at FROM schedule_executions
            WHERE schedule_id = ?
            ORDER BY triggered_at DESC LIMIT 1
        """,
            (schedule.name,),
        )  # Note: Using name as we need the ID

        row = cursor.fetchone()
        conn.close()

        if row:
            last_trigger = datetime.fromisoformat(row[0])
            # Don't trigger if executed in last 55 seconds
            if (now - last_trigger).total_seconds() < 55:
                return False

        return True

    def _evaluate_conditions(self, conditions: List[Dict]) -> bool:
        """Evaluate schedule conditions.

        Args:
            conditions: List of conditions

        Returns:
            True if all conditions are met
        """
        # TODO: Implement condition evaluation
        # This would check sensor values, states, etc.
        return True

    async def _execute_schedule(self, schedule_id: int, schedule: ScheduleRule):
        """Execute scheduled action.

        Args:
            schedule_id: Schedule ID
            schedule: Schedule rule
        """
        # Apply random delay if specified
        if schedule.random_delay:
            delay = random.randint(0, schedule.random_delay)
            await asyncio.sleep(delay)

        # Record execution start
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO schedule_executions
            (schedule_id, triggered_at, action_type, devices_affected)
            VALUES (?, ?, ?, ?)
        """,
            (
                schedule_id,
                datetime.now(),
                schedule.action_type.value,
                json.dumps(schedule.devices),
            ),
        )

        execution_id = cursor.lastrowid
        conn.commit()

        # Execute action on devices
        success = True
        error_message = None
        retry_count = 0

        while retry_count <= schedule.retry_count:
            try:
                # TODO: Execute actual device action
                # This would integrate with the device control system
                for device_ip in schedule.devices:
                    await self._execute_device_action(
                        device_ip, schedule.action_type, schedule.action_config
                    )
                break

            except Exception as e:
                error_message = str(e)
                retry_count += 1
                if retry_count <= schedule.retry_count:
                    await asyncio.sleep(5 * retry_count)  # Exponential backoff
                else:
                    success = False

        # Update execution record
        cursor.execute(
            """
            UPDATE schedule_executions
            SET executed_at = ?, success = ?, error_message = ?, retry_count = ?
            WHERE id = ?
        """,
            (datetime.now(), success, error_message, retry_count, execution_id),
        )

        conn.commit()
        conn.close()

    async def _execute_device_action(
        self, device_ip: str, action_type: ActionType, config: Dict[str, Any]
    ):
        """Execute action on a device.

        Args:
            device_ip: Device IP address
            action_type: Type of action
            config: Action configuration
        """
        # TODO: Implement actual device control
        # This is a placeholder that would integrate with the device control system
        pass

    def _check_schedule_conflicts(self, schedule_id: int):
        """Check for conflicts with other schedules.

        Args:
            schedule_id: Schedule ID to check
        """
        if schedule_id not in self.schedules:
            return

        schedule = self.schedules[schedule_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for other_id, other_schedule in self.schedules.items():
            if other_id == schedule_id:
                continue

            # Check for device overlap
            device_overlap = set(schedule.devices) & set(other_schedule.devices)
            if not device_overlap:
                continue

            # Check for time conflicts
            conflict_type = None

            if (
                schedule.trigger_type == TriggerType.TIME
                and other_schedule.trigger_type == TriggerType.TIME
            ):
                if schedule.trigger_config.get(
                    "time"
                ) == other_schedule.trigger_config.get("time"):
                    conflict_type = "same_time"

            if conflict_type:
                # Record conflict
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO schedule_conflicts
                    (schedule1_id, schedule2_id, conflict_type)
                    VALUES (?, ?, ?)
                """,
                    (schedule_id, other_id, conflict_type),
                )

        conn.commit()
        conn.close()

    def create_holiday_schedule(
        self,
        holiday_name: str,
        schedule_id: int,
        country_code: str = "US",
        year: Optional[int] = None,
    ) -> bool:
        """Create holiday-specific schedule.

        Args:
            holiday_name: Name of holiday
            schedule_id: Schedule to activate
            country_code: Country code for holidays
            year: Specific year (None for recurring)

        Returns:
            True if created successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO holiday_schedules
                (holiday_name, country_code, schedule_id, year, enabled)
                VALUES (?, ?, ?, ?, 1)
            """,
                (holiday_name, country_code, schedule_id, year),
            )

            conn.commit()
            return True

        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_schedule_statistics(self, schedule_id: int, days: int = 30) -> Dict:
        """Get schedule execution statistics.

        Args:
            schedule_id: Schedule ID
            days: Number of days to analyze

        Returns:
            Execution statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        start_date = datetime.now() - timedelta(days=days)

        # Get execution counts
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                AVG(retry_count) as avg_retries
            FROM schedule_executions
            WHERE schedule_id = ? AND triggered_at >= ?
        """,
            (schedule_id, start_date),
        )

        row = cursor.fetchone()

        stats = {
            "total_executions": row[0] or 0,
            "successful": row[1] or 0,
            "failed": row[2] or 0,
            "average_retries": row[3] or 0,
            "success_rate": ((row[1] or 0) / (row[0] or 1)) * 100,
        }

        conn.close()
        return stats

    def _load_schedules(self):
        """Load schedules from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, description, schedule_type, trigger_type, trigger_config,
                   action_type, action_config, devices, groups, conditions,
                   random_delay, retry_on_failure, retry_count, enabled, priority,
                   valid_from, valid_until, timezone, metadata
            FROM schedule_rules
            WHERE enabled = 1
        """
        )

        self.schedules = {}
        for row in cursor.fetchall():
            schedule = ScheduleRule(
                name=row[1],
                description=row[2],
                schedule_type=ScheduleType(row[3]),
                trigger_type=TriggerType(row[4]),
                trigger_config=json.loads(row[5]),
                action_type=ActionType(row[6]),
                action_config=json.loads(row[7]),
                devices=json.loads(row[8]),
                groups=json.loads(row[9]) if row[9] else None,
                conditions=json.loads(row[10]) if row[10] else None,
                random_delay=row[11],
                retry_on_failure=bool(row[12]),
                retry_count=row[13],
                enabled=bool(row[14]),
                priority=row[15],
                valid_from=datetime.fromisoformat(row[16]) if row[16] else None,
                valid_until=datetime.fromisoformat(row[17]) if row[17] else None,
                timezone=row[18],
                metadata=json.loads(row[19]) if row[19] else None,
            )
            self.schedules[row[0]] = schedule

        conn.close()
