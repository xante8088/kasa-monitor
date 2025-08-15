"""Device calibration system for accurate energy measurement.

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
import statistics
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import numpy as np
from scipy import stats


class CalibrationType(Enum):
    """Calibration types."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    REFERENCE = "reference"
    FACTORY = "factory"
    CUSTOM = "custom"


class CalibrationStatus(Enum):
    """Calibration status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class MeasurementType(Enum):
    """Measurement types that can be calibrated."""

    POWER = "power"
    VOLTAGE = "voltage"
    CURRENT = "current"
    ENERGY = "energy"
    POWER_FACTOR = "power_factor"
    FREQUENCY = "frequency"
    TEMPERATURE = "temperature"


@dataclass
class CalibrationProfile:
    """Device calibration profile."""

    device_ip: str
    name: str
    description: str
    calibration_type: CalibrationType
    factors: Dict[str, float]
    offsets: Dict[str, float]
    valid_range: Dict[str, Tuple[float, float]]
    confidence_level: float
    expires_at: Optional[datetime] = None
    reference_device: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["calibration_type"] = self.calibration_type.value
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data

    def apply_calibration(
        self, measurement_type: MeasurementType, value: float
    ) -> float:
        """Apply calibration to a measurement.

        Args:
            measurement_type: Type of measurement
            value: Raw measurement value

        Returns:
            Calibrated value
        """
        key = measurement_type.value
        factor = self.factors.get(key, 1.0)
        offset = self.offsets.get(key, 0.0)

        # Apply linear calibration: calibrated = (raw * factor) + offset
        calibrated = (value * factor) + offset

        # Check valid range
        if key in self.valid_range:
            min_val, max_val = self.valid_range[key]
            calibrated = max(min_val, min(calibrated, max_val))

        return calibrated


@dataclass
class CalibrationPoint:
    """Single calibration data point."""

    timestamp: datetime
    measurement_type: MeasurementType
    raw_value: float
    reference_value: float
    temperature: Optional[float] = None
    humidity: Optional[float] = None

    @property
    def error(self) -> float:
        """Calculate measurement error."""
        if self.reference_value == 0:
            return 0
        return ((self.raw_value - self.reference_value) / self.reference_value) * 100

    @property
    def correction_factor(self) -> float:
        """Calculate correction factor."""
        if self.raw_value == 0:
            return 1.0
        return self.reference_value / self.raw_value


class DeviceCalibrationManager:
    """Manages device calibration profiles and validation."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize calibration manager.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.profiles = {}
        self._init_database()
        self._load_profiles()

    def _init_database(self):
        """Initialize calibration tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calibration profiles table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_ip TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                calibration_type TEXT NOT NULL,
                factors TEXT NOT NULL,
                offsets TEXT NOT NULL,
                valid_range TEXT,
                confidence_level REAL DEFAULT 0.95,
                expires_at TIMESTAMP,
                reference_device TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                UNIQUE(device_ip, name)
            )
        """
        )

        # Calibration data points table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                measurement_type TEXT NOT NULL,
                raw_value REAL NOT NULL,
                reference_value REAL NOT NULL,
                temperature REAL,
                humidity REAL,
                FOREIGN KEY (profile_id) REFERENCES calibration_profiles(id)
            )
        """
        )

        # Calibration history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_ip TEXT NOT NULL,
                profile_id INTEGER NOT NULL,
                calibration_date TIMESTAMP NOT NULL,
                calibration_type TEXT NOT NULL,
                factors_before TEXT,
                factors_after TEXT NOT NULL,
                offsets_before TEXT,
                offsets_after TEXT NOT NULL,
                data_points_used INTEGER,
                rmse REAL,
                max_error REAL,
                notes TEXT,
                performed_by TEXT,
                FOREIGN KEY (profile_id) REFERENCES calibration_profiles(id)
            )
        """
        )

        # Auto-calibration settings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auto_calibration_settings (
                device_ip TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 0,
                measurement_types TEXT NOT NULL,
                sample_interval INTEGER DEFAULT 3600,
                sample_count INTEGER DEFAULT 24,
                max_deviation REAL DEFAULT 0.1,
                last_calibration TIMESTAMP,
                next_calibration TIMESTAMP
            )
        """
        )

        # Calibration validation results table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                validation_date TIMESTAMP NOT NULL,
                measurement_type TEXT NOT NULL,
                sample_count INTEGER,
                mean_error REAL,
                std_deviation REAL,
                max_error REAL,
                min_error REAL,
                passed BOOLEAN,
                FOREIGN KEY (profile_id) REFERENCES calibration_profiles(id)
            )
        """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_device ON calibration_profiles(device_ip)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_active ON calibration_profiles(active)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_data_profile ON calibration_data(profile_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_history_device ON calibration_history(device_ip)"
        )

        conn.commit()
        conn.close()

    def create_profile(self, profile: CalibrationProfile) -> int:
        """Create calibration profile.

        Args:
            profile: Calibration profile

        Returns:
            Profile ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Deactivate existing profiles for this device
            cursor.execute(
                "UPDATE calibration_profiles SET active = 0 WHERE device_ip = ?",
                (profile.device_ip,),
            )

            # Insert new profile
            cursor.execute(
                """
                INSERT INTO calibration_profiles 
                (device_ip, name, description, calibration_type, factors, offsets,
                 valid_range, confidence_level, expires_at, reference_device, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    profile.device_ip,
                    profile.name,
                    profile.description,
                    profile.calibration_type.value,
                    json.dumps(profile.factors),
                    json.dumps(profile.offsets),
                    json.dumps(profile.valid_range),
                    profile.confidence_level,
                    profile.expires_at,
                    profile.reference_device,
                    json.dumps(profile.metadata) if profile.metadata else None,
                ),
            )

            profile_id = cursor.lastrowid
            conn.commit()

            # Add to cache
            self.profiles[profile.device_ip] = profile

            return profile_id

        except sqlite3.IntegrityError:
            return 0
        finally:
            conn.close()

    def add_calibration_point(self, profile_id: int, point: CalibrationPoint) -> bool:
        """Add calibration data point.

        Args:
            profile_id: Profile ID
            point: Calibration data point

        Returns:
            True if added successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO calibration_data 
                (profile_id, timestamp, measurement_type, raw_value, 
                 reference_value, temperature, humidity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    profile_id,
                    point.timestamp,
                    point.measurement_type.value,
                    point.raw_value,
                    point.reference_value,
                    point.temperature,
                    point.humidity,
                ),
            )

            conn.commit()
            return True

        except Exception:
            return False
        finally:
            conn.close()

    def calculate_calibration_factors(
        self,
        device_ip: str,
        measurement_type: MeasurementType,
        data_points: Optional[List[CalibrationPoint]] = None,
        method: str = "linear",
    ) -> Tuple[float, float, float]:
        """Calculate calibration factors from data points.

        Args:
            device_ip: Device IP address
            measurement_type: Type of measurement
            data_points: Calibration data points (if None, uses stored data)
            method: Calibration method (linear, polynomial, etc.)

        Returns:
            Tuple of (factor, offset, confidence)
        """
        if data_points is None:
            data_points = self._get_calibration_data(device_ip, measurement_type)

        if len(data_points) < 2:
            return 1.0, 0.0, 0.0

        # Extract values
        raw_values = [p.raw_value for p in data_points]
        ref_values = [p.reference_value for p in data_points]

        if method == "linear":
            # Linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                raw_values, ref_values
            )

            factor = slope
            offset = intercept
            confidence = r_value**2  # R-squared

        elif method == "polynomial":
            # Polynomial fitting (2nd degree)
            coeffs = np.polyfit(raw_values, ref_values, 2)
            # For simplicity, use linear approximation at mean
            mean_raw = np.mean(raw_values)
            factor = 2 * coeffs[0] * mean_raw + coeffs[1]
            offset = coeffs[2]

            # Calculate R-squared
            poly_func = np.poly1d(coeffs)
            y_pred = poly_func(raw_values)
            ss_res = np.sum((ref_values - y_pred) ** 2)
            ss_tot = np.sum((ref_values - np.mean(ref_values)) ** 2)
            confidence = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        else:
            # Default to simple ratio
            factor = np.mean([p.correction_factor for p in data_points])
            offset = 0.0
            confidence = 1.0 - np.std([p.correction_factor for p in data_points])

        return factor, offset, max(0, min(1, confidence))

    def auto_calibrate(
        self,
        device_ip: str,
        reference_device_ip: Optional[str] = None,
        duration_hours: int = 24,
    ) -> bool:
        """Perform automatic calibration.

        Args:
            device_ip: Device to calibrate
            reference_device_ip: Reference device for comparison
            duration_hours: Duration for data collection

        Returns:
            True if calibration successful
        """
        # TODO: Implement automatic calibration
        # This would:
        # 1. Collect data from both devices over the duration
        # 2. Calculate calibration factors
        # 3. Validate the calibration
        # 4. Create and activate new profile

        return False

    def validate_calibration(
        self, profile_id: int, validation_data: List[CalibrationPoint]
    ) -> Dict[str, Any]:
        """Validate calibration accuracy.

        Args:
            profile_id: Profile ID to validate
            validation_data: Validation data points

        Returns:
            Validation results
        """
        if not validation_data:
            return {"passed": False, "error": "No validation data"}

        # Group by measurement type
        by_type = {}
        for point in validation_data:
            if point.measurement_type not in by_type:
                by_type[point.measurement_type] = []
            by_type[point.measurement_type].append(point)

        results = {}
        overall_passed = True

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for measurement_type, points in by_type.items():
            errors = [p.error for p in points]

            validation = {
                "sample_count": len(points),
                "mean_error": statistics.mean(errors),
                "std_deviation": statistics.stdev(errors) if len(errors) > 1 else 0,
                "max_error": max(errors),
                "min_error": min(errors),
                "passed": abs(statistics.mean(errors)) < 5.0,  # 5% threshold
            }

            results[measurement_type.value] = validation
            overall_passed = overall_passed and validation["passed"]

            # Store validation result
            cursor.execute(
                """
                INSERT INTO calibration_validations 
                (profile_id, validation_date, measurement_type, sample_count,
                 mean_error, std_deviation, max_error, min_error, passed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    profile_id,
                    datetime.now(),
                    measurement_type.value,
                    validation["sample_count"],
                    validation["mean_error"],
                    validation["std_deviation"],
                    validation["max_error"],
                    validation["min_error"],
                    validation["passed"],
                ),
            )

        conn.commit()
        conn.close()

        results["overall_passed"] = overall_passed
        return results

    def get_active_profile(self, device_ip: str) -> Optional[CalibrationProfile]:
        """Get active calibration profile for device.

        Args:
            device_ip: Device IP address

        Returns:
            Active calibration profile or None
        """
        if device_ip in self.profiles:
            profile = self.profiles[device_ip]
            # Check if expired
            if profile.expires_at and profile.expires_at < datetime.now():
                return None
            return profile

        return None

    def apply_calibration(
        self, device_ip: str, measurement_type: MeasurementType, value: float
    ) -> float:
        """Apply calibration to a measurement.

        Args:
            device_ip: Device IP address
            measurement_type: Type of measurement
            value: Raw measurement value

        Returns:
            Calibrated value
        """
        profile = self.get_active_profile(device_ip)
        if profile:
            return profile.apply_calibration(measurement_type, value)
        return value

    def get_calibration_history(self, device_ip: str, limit: int = 10) -> List[Dict]:
        """Get calibration history for device.

        Args:
            device_ip: Device IP address
            limit: Maximum results

        Returns:
            Calibration history
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT calibration_date, calibration_type, factors_after, offsets_after,
                   data_points_used, rmse, max_error, performed_by
            FROM calibration_history
            WHERE device_ip = ?
            ORDER BY calibration_date DESC
            LIMIT ?
        """,
            (device_ip, limit),
        )

        history = []
        for row in cursor.fetchall():
            history.append(
                {
                    "date": row[0],
                    "type": row[1],
                    "factors": json.loads(row[2]),
                    "offsets": json.loads(row[3]),
                    "data_points": row[4],
                    "rmse": row[5],
                    "max_error": row[6],
                    "performed_by": row[7],
                }
            )

        conn.close()
        return history

    def export_calibration_profile(self, profile_id: int) -> Dict:
        """Export calibration profile for backup or sharing.

        Args:
            profile_id: Profile ID

        Returns:
            Exportable profile data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get profile
        cursor.execute(
            """
            SELECT * FROM calibration_profiles WHERE id = ?
        """,
            (profile_id,),
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {}

        # Get calibration data
        cursor.execute(
            """
            SELECT * FROM calibration_data WHERE profile_id = ?
        """,
            (profile_id,),
        )

        data_points = cursor.fetchall()

        conn.close()

        return {
            "profile": {
                "device_ip": row[1],
                "name": row[2],
                "description": row[3],
                "calibration_type": row[4],
                "factors": json.loads(row[5]),
                "offsets": json.loads(row[6]),
                "valid_range": json.loads(row[7]) if row[7] else None,
                "confidence_level": row[8],
                "expires_at": row[9],
                "reference_device": row[10],
                "metadata": json.loads(row[11]) if row[11] else None,
            },
            "data_points": [
                {
                    "timestamp": point[2],
                    "measurement_type": point[3],
                    "raw_value": point[4],
                    "reference_value": point[5],
                    "temperature": point[6],
                    "humidity": point[7],
                }
                for point in data_points
            ],
        }

    def import_calibration_profile(self, profile_data: Dict) -> int:
        """Import calibration profile.

        Args:
            profile_data: Profile data to import

        Returns:
            New profile ID
        """
        profile_dict = profile_data.get("profile", {})

        profile = CalibrationProfile(
            device_ip=profile_dict["device_ip"],
            name=profile_dict["name"],
            description=profile_dict["description"],
            calibration_type=CalibrationType(profile_dict["calibration_type"]),
            factors=profile_dict["factors"],
            offsets=profile_dict["offsets"],
            valid_range=profile_dict.get("valid_range", {}),
            confidence_level=profile_dict.get("confidence_level", 0.95),
            expires_at=(
                datetime.fromisoformat(profile_dict["expires_at"])
                if profile_dict.get("expires_at")
                else None
            ),
            reference_device=profile_dict.get("reference_device"),
            metadata=profile_dict.get("metadata"),
        )

        profile_id = self.create_profile(profile)

        # Import data points if provided
        if profile_id and "data_points" in profile_data:
            for point_data in profile_data["data_points"]:
                point = CalibrationPoint(
                    timestamp=datetime.fromisoformat(point_data["timestamp"]),
                    measurement_type=MeasurementType(point_data["measurement_type"]),
                    raw_value=point_data["raw_value"],
                    reference_value=point_data["reference_value"],
                    temperature=point_data.get("temperature"),
                    humidity=point_data.get("humidity"),
                )
                self.add_calibration_point(profile_id, point)

        return profile_id

    def _get_calibration_data(
        self, device_ip: str, measurement_type: MeasurementType
    ) -> List[CalibrationPoint]:
        """Get calibration data points for device.

        Args:
            device_ip: Device IP address
            measurement_type: Type of measurement

        Returns:
            List of calibration points
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT d.timestamp, d.measurement_type, d.raw_value, d.reference_value,
                   d.temperature, d.humidity
            FROM calibration_data d
            JOIN calibration_profiles p ON d.profile_id = p.id
            WHERE p.device_ip = ? AND d.measurement_type = ?
            ORDER BY d.timestamp DESC
            LIMIT 100
        """,
            (device_ip, measurement_type.value),
        )

        points = []
        for row in cursor.fetchall():
            points.append(
                CalibrationPoint(
                    timestamp=datetime.fromisoformat(row[0]),
                    measurement_type=MeasurementType(row[1]),
                    raw_value=row[2],
                    reference_value=row[3],
                    temperature=row[4],
                    humidity=row[5],
                )
            )

        conn.close()
        return points

    def _load_profiles(self):
        """Load active calibration profiles."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT device_ip, name, description, calibration_type, factors, offsets,
                   valid_range, confidence_level, expires_at, reference_device, metadata
            FROM calibration_profiles
            WHERE active = 1
        """
        )

        self.profiles = {}
        for row in cursor.fetchall():
            profile = CalibrationProfile(
                device_ip=row[0],
                name=row[1],
                description=row[2],
                calibration_type=CalibrationType(row[3]),
                factors=json.loads(row[4]),
                offsets=json.loads(row[5]),
                valid_range=json.loads(row[6]) if row[6] else {},
                confidence_level=row[7],
                expires_at=datetime.fromisoformat(row[8]) if row[8] else None,
                reference_device=row[9],
                metadata=json.loads(row[10]) if row[10] else None,
            )
            self.profiles[profile.device_ip] = profile

        conn.close()
