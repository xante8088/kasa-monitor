"""Firmware management system for device updates and tracking.

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
import hashlib
import asyncio
import aiohttp
import semver
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import tempfile
import shutil


class FirmwareStatus(Enum):
    """Firmware update status."""

    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    INSTALLING = "installing"
    INSTALLED = "installed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class UpdateChannel(Enum):
    """Firmware update channels."""

    STABLE = "stable"
    BETA = "beta"
    DEVELOPER = "developer"
    CUSTOM = "custom"


class UpdatePolicy(Enum):
    """Firmware update policies."""

    MANUAL = "manual"
    NOTIFY = "notify"
    AUTO_DOWNLOAD = "auto_download"
    AUTO_INSTALL = "auto_install"


@dataclass
class FirmwareVersion:
    """Firmware version information."""

    version: str
    model: str
    release_date: datetime
    channel: UpdateChannel
    size_bytes: int
    checksum: str
    download_url: Optional[str] = None
    release_notes: Optional[str] = None
    min_hardware_version: Optional[str] = None
    max_hardware_version: Optional[str] = None
    dependencies: Optional[List[str]] = None
    critical: bool = False
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["release_date"] = self.release_date.isoformat()
        data["channel"] = self.channel.value
        return data

    def is_newer_than(self, other_version: str) -> bool:
        """Check if this version is newer than another.

        Args:
            other_version: Version string to compare

        Returns:
            True if this version is newer
        """
        try:
            return semver.compare(self.version, other_version) > 0
        except ValueError:
            # Fallback to string comparison if not semver
            return self.version > other_version

    def is_compatible_with(self, hardware_version: str) -> bool:
        """Check if firmware is compatible with hardware.

        Args:
            hardware_version: Hardware version string

        Returns:
            True if compatible
        """
        if self.min_hardware_version:
            try:
                if semver.compare(hardware_version, self.min_hardware_version) < 0:
                    return False
            except ValueError:
                if hardware_version < self.min_hardware_version:
                    return False

        if self.max_hardware_version:
            try:
                if semver.compare(hardware_version, self.max_hardware_version) > 0:
                    return False
            except ValueError:
                if hardware_version > self.max_hardware_version:
                    return False

        return True


@dataclass
class DeviceFirmware:
    """Device firmware information."""

    device_ip: str
    model: str
    current_version: str
    hardware_version: str
    last_updated: Optional[datetime] = None
    auto_update: bool = False
    update_channel: UpdateChannel = UpdateChannel.STABLE
    update_policy: UpdatePolicy = UpdatePolicy.NOTIFY

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        if self.last_updated:
            data["last_updated"] = self.last_updated.isoformat()
        data["update_channel"] = self.update_channel.value
        data["update_policy"] = self.update_policy.value
        return data


@dataclass
class FirmwareUpdate:
    """Firmware update task."""

    device_ip: str
    from_version: str
    to_version: str
    status: FirmwareStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_version: Optional[str] = None
    progress_percent: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data


class FirmwareManager:
    """Manages firmware updates and version tracking."""

    def __init__(
        self, db_path: str = "kasa_monitor.db", firmware_dir: str = "./firmware"
    ):
        """Initialize firmware manager.

        Args:
            db_path: Path to database
            firmware_dir: Directory for firmware storage
        """
        self.db_path = db_path
        self.firmware_dir = Path(firmware_dir)
        self.firmware_dir.mkdir(parents=True, exist_ok=True)

        self.device_firmware = {}
        self.available_firmware = {}
        self.update_tasks = {}

        self._init_database()
        self._load_device_firmware()
        self._load_available_firmware()

    def _init_database(self):
        """Initialize firmware tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Device firmware table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_firmware (
                device_ip TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                current_version TEXT NOT NULL,
                hardware_version TEXT,
                last_updated TIMESTAMP,
                auto_update BOOLEAN DEFAULT 0,
                update_channel TEXT DEFAULT 'stable',
                update_policy TEXT DEFAULT 'notify',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Available firmware versions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS firmware_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                model TEXT NOT NULL,
                release_date TIMESTAMP NOT NULL,
                channel TEXT NOT NULL,
                size_bytes INTEGER,
                checksum TEXT NOT NULL,
                download_url TEXT,
                release_notes TEXT,
                min_hardware_version TEXT,
                max_hardware_version TEXT,
                dependencies TEXT,
                critical BOOLEAN DEFAULT 0,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(version, model, channel)
            )
        """
        )

        # Firmware update history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS firmware_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_ip TEXT NOT NULL,
                from_version TEXT NOT NULL,
                to_version TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                error_message TEXT,
                rollback_version TEXT,
                update_method TEXT,
                initiated_by TEXT,
                FOREIGN KEY (device_ip) REFERENCES device_firmware(device_ip)
            )
        """
        )

        # Firmware download cache table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS firmware_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                model TEXT NOT NULL,
                file_path TEXT NOT NULL,
                checksum TEXT NOT NULL,
                size_bytes INTEGER,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                UNIQUE(version, model)
            )
        """
        )

        # Update schedules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS update_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_ip TEXT,
                device_group TEXT,
                target_version TEXT NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                max_parallel INTEGER DEFAULT 1,
                rollback_on_failure BOOLEAN DEFAULT 1,
                test_devices TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Compatibility matrix table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS firmware_compatibility (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                firmware_version TEXT NOT NULL,
                hardware_versions TEXT NOT NULL,
                compatible_with TEXT,
                incompatible_with TEXT,
                notes TEXT,
                verified BOOLEAN DEFAULT 0,
                UNIQUE(model, firmware_version)
            )
        """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fw_model ON firmware_versions(model)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fw_channel ON firmware_versions(channel)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fw_update_device ON firmware_updates(device_ip)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_fw_update_status ON firmware_updates(status)"
        )

        conn.commit()
        conn.close()

    def track_device(self, device: DeviceFirmware) -> bool:
        """Track device firmware information.

        Args:
            device: Device firmware information

        Returns:
            True if tracked successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO device_firmware 
                (device_ip, model, current_version, hardware_version,
                 last_updated, auto_update, update_channel, update_policy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    device.device_ip,
                    device.model,
                    device.current_version,
                    device.hardware_version,
                    device.last_updated,
                    device.auto_update,
                    device.update_channel.value,
                    device.update_policy.value,
                ),
            )

            conn.commit()
            self.device_firmware[device.device_ip] = device
            return True

        except Exception:
            return False
        finally:
            conn.close()

    def register_firmware(self, firmware: FirmwareVersion) -> bool:
        """Register available firmware version.

        Args:
            firmware: Firmware version information

        Returns:
            True if registered successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO firmware_versions 
                (version, model, release_date, channel, size_bytes, checksum,
                 download_url, release_notes, min_hardware_version,
                 max_hardware_version, dependencies, critical, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    firmware.version,
                    firmware.model,
                    firmware.release_date,
                    firmware.channel.value,
                    firmware.size_bytes,
                    firmware.checksum,
                    firmware.download_url,
                    firmware.release_notes,
                    firmware.min_hardware_version,
                    firmware.max_hardware_version,
                    (
                        json.dumps(firmware.dependencies)
                        if firmware.dependencies
                        else None
                    ),
                    firmware.critical,
                    json.dumps(firmware.metadata) if firmware.metadata else None,
                ),
            )

            conn.commit()

            # Add to cache
            key = f"{firmware.model}:{firmware.channel.value}"
            if key not in self.available_firmware:
                self.available_firmware[key] = []
            self.available_firmware[key].append(firmware)

            return True

        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def check_for_updates(self, device_ip: str) -> Optional[FirmwareVersion]:
        """Check if updates are available for device.

        Args:
            device_ip: Device IP address

        Returns:
            Latest compatible firmware or None
        """
        device = self.device_firmware.get(device_ip)
        if not device:
            return None

        # Get available firmware for model and channel
        key = f"{device.model}:{device.update_channel.value}"
        available = self.available_firmware.get(key, [])

        # Filter compatible and newer versions
        compatible = []
        for fw in available:
            if fw.is_newer_than(device.current_version) and fw.is_compatible_with(
                device.hardware_version
            ):
                compatible.append(fw)

        if not compatible:
            return None

        # Return latest version
        return max(compatible, key=lambda x: x.version)

    async def download_firmware(
        self, firmware: FirmwareVersion, progress_callback: Optional[callable] = None
    ) -> str:
        """Download firmware file.

        Args:
            firmware: Firmware version to download
            progress_callback: Progress callback function

        Returns:
            Path to downloaded file
        """
        # Check cache first
        cached_path = self._get_cached_firmware(firmware)
        if cached_path:
            return cached_path

        if not firmware.download_url:
            raise ValueError("No download URL available")

        # Download to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(firmware.download_url) as response:
                    response.raise_for_status()

                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(temp_file.name, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            if progress_callback and total_size:
                                progress = (downloaded / total_size) * 100
                                progress_callback(progress)

            # Verify checksum
            if not self._verify_checksum(temp_file.name, firmware.checksum):
                raise ValueError("Checksum verification failed")

            # Move to firmware directory
            final_path = self.firmware_dir / f"{firmware.model}_{firmware.version}.bin"
            shutil.move(temp_file.name, final_path)

            # Cache the download
            self._cache_firmware(firmware, str(final_path))

            return str(final_path)

        except Exception as e:
            # Clean up temp file on error
            Path(temp_file.name).unlink(missing_ok=True)
            raise e

    async def install_update(
        self, device_ip: str, firmware: FirmwareVersion, backup_current: bool = True
    ) -> bool:
        """Install firmware update on device.

        Args:
            device_ip: Device IP address
            firmware: Firmware to install
            backup_current: Whether to backup current firmware

        Returns:
            True if installation successful
        """
        device = self.device_firmware.get(device_ip)
        if not device:
            return False

        # Create update task
        update = FirmwareUpdate(
            device_ip=device_ip,
            from_version=device.current_version,
            to_version=firmware.version,
            status=FirmwareStatus.DOWNLOADING,
            started_at=datetime.now(),
        )

        self.update_tasks[device_ip] = update
        self._record_update_start(update)

        try:
            # Download firmware
            firmware_path = await self.download_firmware(
                firmware,
                lambda p: self._update_progress(device_ip, p * 0.5),  # 50% for download
            )

            update.status = FirmwareStatus.DOWNLOADED

            # Backup current firmware if requested
            if backup_current:
                update.rollback_version = device.current_version

            # Install firmware
            update.status = FirmwareStatus.INSTALLING
            success = await self._install_firmware_on_device(
                device_ip, firmware_path, firmware
            )

            if success:
                update.status = FirmwareStatus.INSTALLED
                update.completed_at = datetime.now()
                update.progress_percent = 100

                # Update device record
                device.current_version = firmware.version
                device.last_updated = datetime.now()
                self.track_device(device)
            else:
                raise Exception("Installation failed")

            self._record_update_complete(update)
            return True

        except Exception as e:
            update.status = FirmwareStatus.FAILED
            update.error_message = str(e)
            update.completed_at = datetime.now()

            # Attempt rollback if available
            if update.rollback_version and backup_current:
                await self.rollback_firmware(device_ip)

            self._record_update_complete(update)
            return False
        finally:
            # Clean up task
            if device_ip in self.update_tasks:
                del self.update_tasks[device_ip]

    async def rollback_firmware(self, device_ip: str) -> bool:
        """Rollback to previous firmware version.

        Args:
            device_ip: Device IP address

        Returns:
            True if rollback successful
        """
        # Get last successful update
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT from_version FROM firmware_updates
            WHERE device_ip = ? AND status = 'installed'
            ORDER BY completed_at DESC LIMIT 1
        """,
            (device_ip,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return False

        previous_version = row[0]

        # TODO: Implement actual rollback mechanism
        # This would involve installing the previous version

        # Update device record
        device = self.device_firmware.get(device_ip)
        if device:
            device.current_version = previous_version
            self.track_device(device)

        # Record rollback
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO firmware_updates 
            (device_ip, from_version, to_version, status, started_at, completed_at)
            VALUES (?, ?, ?, 'rolled_back', ?, ?)
        """,
            (
                device_ip,
                device.current_version if device else "unknown",
                previous_version,
                datetime.now(),
                datetime.now(),
            ),
        )

        conn.commit()
        conn.close()

        return True

    async def _install_firmware_on_device(
        self, device_ip: str, firmware_path: str, firmware: FirmwareVersion
    ) -> bool:
        """Install firmware on physical device.

        Args:
            device_ip: Device IP address
            firmware_path: Path to firmware file
            firmware: Firmware version info

        Returns:
            True if installation successful
        """
        # TODO: Implement actual firmware installation
        # This would involve:
        # 1. Connecting to the device
        # 2. Uploading the firmware
        # 3. Triggering the update process
        # 4. Monitoring the update progress
        # 5. Verifying successful installation

        # Simulate installation delay
        await asyncio.sleep(5)

        # Update progress
        self._update_progress(device_ip, 100)

        return True

    def schedule_update(
        self,
        device_ip: Optional[str],
        target_version: str,
        scheduled_time: datetime,
        device_group: Optional[str] = None,
        max_parallel: int = 1,
        test_devices: Optional[List[str]] = None,
    ) -> int:
        """Schedule firmware update.

        Args:
            device_ip: Device IP (None for group update)
            target_version: Target firmware version
            scheduled_time: When to perform update
            device_group: Device group name
            max_parallel: Maximum parallel updates
            test_devices: Test devices to update first

        Returns:
            Schedule ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO update_schedules 
            (device_ip, device_group, target_version, scheduled_time,
             max_parallel, test_devices, enabled)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
            (
                device_ip,
                device_group,
                target_version,
                scheduled_time,
                max_parallel,
                json.dumps(test_devices) if test_devices else None,
            ),
        )

        schedule_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return schedule_id

    def get_update_history(self, device_ip: str, limit: int = 10) -> List[Dict]:
        """Get firmware update history for device.

        Args:
            device_ip: Device IP address
            limit: Maximum results

        Returns:
            Update history
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT from_version, to_version, status, started_at, completed_at,
                   error_message, rollback_version, initiated_by
            FROM firmware_updates
            WHERE device_ip = ?
            ORDER BY started_at DESC
            LIMIT ?
        """,
            (device_ip, limit),
        )

        history = []
        for row in cursor.fetchall():
            history.append(
                {
                    "from_version": row[0],
                    "to_version": row[1],
                    "status": row[2],
                    "started_at": row[3],
                    "completed_at": row[4],
                    "error_message": row[5],
                    "rollback_version": row[6],
                    "initiated_by": row[7],
                }
            )

        conn.close()
        return history

    def verify_compatibility(
        self, device_ip: str, firmware: FirmwareVersion
    ) -> Dict[str, Any]:
        """Verify firmware compatibility with device.

        Args:
            device_ip: Device IP address
            firmware: Firmware to check

        Returns:
            Compatibility check results
        """
        device = self.device_firmware.get(device_ip)
        if not device:
            return {"compatible": False, "reason": "Device not found"}

        results = {"compatible": True, "warnings": [], "errors": []}

        # Check model match
        if firmware.model != device.model:
            results["compatible"] = False
            results["errors"].append(
                f"Model mismatch: device is {device.model}, firmware is for {firmware.model}"
            )

        # Check hardware compatibility
        if not firmware.is_compatible_with(device.hardware_version):
            results["compatible"] = False
            results["errors"].append(
                f"Hardware version {device.hardware_version} not compatible"
            )

        # Check dependencies
        if firmware.dependencies:
            for dep in firmware.dependencies:
                # TODO: Check if dependency is met
                pass

        # Check for known issues
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT incompatible_with, notes FROM firmware_compatibility
            WHERE model = ? AND firmware_version = ?
        """,
            (device.model, firmware.version),
        )

        row = cursor.fetchone()
        if row and row[0]:
            incompatible = json.loads(row[0])
            if device.hardware_version in incompatible:
                results["compatible"] = False
                results["errors"].append(f"Known incompatibility: {row[1]}")

        conn.close()

        return results

    def _verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """Verify file checksum.

        Args:
            file_path: Path to file
            expected_checksum: Expected checksum

        Returns:
            True if checksum matches
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest() == expected_checksum

    def _get_cached_firmware(self, firmware: FirmwareVersion) -> Optional[str]:
        """Get cached firmware file path.

        Args:
            firmware: Firmware version

        Returns:
            File path if cached, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT file_path FROM firmware_cache
            WHERE version = ? AND model = ?
        """,
            (firmware.version, firmware.model),
        )

        row = cursor.fetchone()
        conn.close()

        if row and Path(row[0]).exists():
            return row[0]

        return None

    def _cache_firmware(self, firmware: FirmwareVersion, file_path: str):
        """Cache downloaded firmware.

        Args:
            firmware: Firmware version
            file_path: Path to firmware file
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO firmware_cache 
            (version, model, file_path, checksum, size_bytes)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                firmware.version,
                firmware.model,
                file_path,
                firmware.checksum,
                firmware.size_bytes,
            ),
        )

        conn.commit()
        conn.close()

    def _update_progress(self, device_ip: str, progress: float):
        """Update installation progress.

        Args:
            device_ip: Device IP address
            progress: Progress percentage
        """
        if device_ip in self.update_tasks:
            self.update_tasks[device_ip].progress_percent = int(progress)

    def _record_update_start(self, update: FirmwareUpdate):
        """Record update start in database.

        Args:
            update: Firmware update task
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO firmware_updates 
            (device_ip, from_version, to_version, status, started_at,
             initiated_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                update.device_ip,
                update.from_version,
                update.to_version,
                update.status.value,
                update.started_at,
                "system",
            ),
        )

        conn.commit()
        conn.close()

    def _record_update_complete(self, update: FirmwareUpdate):
        """Record update completion in database.

        Args:
            update: Firmware update task
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE firmware_updates 
            SET status = ?, completed_at = ?, error_message = ?,
                rollback_version = ?
            WHERE device_ip = ? AND started_at = ?
        """,
            (
                update.status.value,
                update.completed_at,
                update.error_message,
                update.rollback_version,
                update.device_ip,
                update.started_at,
            ),
        )

        conn.commit()
        conn.close()

    def _load_device_firmware(self):
        """Load device firmware information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT device_ip, model, current_version, hardware_version,
                   last_updated, auto_update, update_channel, update_policy
            FROM device_firmware
        """
        )

        self.device_firmware = {}
        for row in cursor.fetchall():
            device = DeviceFirmware(
                device_ip=row[0],
                model=row[1],
                current_version=row[2],
                hardware_version=row[3],
                last_updated=datetime.fromisoformat(row[4]) if row[4] else None,
                auto_update=bool(row[5]),
                update_channel=UpdateChannel(row[6]),
                update_policy=UpdatePolicy(row[7]),
            )
            self.device_firmware[device.device_ip] = device

        conn.close()

    def _load_available_firmware(self):
        """Load available firmware versions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT version, model, release_date, channel, size_bytes, checksum,
                   download_url, release_notes, min_hardware_version,
                   max_hardware_version, dependencies, critical, metadata
            FROM firmware_versions
            ORDER BY release_date DESC
        """
        )

        self.available_firmware = {}
        for row in cursor.fetchall():
            firmware = FirmwareVersion(
                version=row[0],
                model=row[1],
                release_date=datetime.fromisoformat(row[2]),
                channel=UpdateChannel(row[3]),
                size_bytes=row[4],
                checksum=row[5],
                download_url=row[6],
                release_notes=row[7],
                min_hardware_version=row[8],
                max_hardware_version=row[9],
                dependencies=json.loads(row[10]) if row[10] else None,
                critical=bool(row[11]),
                metadata=json.loads(row[12]) if row[12] else None,
            )

            key = f"{firmware.model}:{firmware.channel.value}"
            if key not in self.available_firmware:
                self.available_firmware[key] = []
            self.available_firmware[key].append(firmware)

        conn.close()
