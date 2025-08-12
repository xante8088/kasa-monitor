"""Data models for Kasa device monitoring.

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

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum


class Permission(str, Enum):
    """System permissions for user roles."""
    # Device management
    DEVICES_VIEW = "devices.view"
    DEVICES_DISCOVER = "devices.discover"
    DEVICES_EDIT = "devices.edit"
    DEVICES_REMOVE = "devices.remove"
    DEVICES_CONTROL = "devices.control"
    
    # Rate management
    RATES_VIEW = "rates.view"
    RATES_EDIT = "rates.edit"
    RATES_DELETE = "rates.delete"
    
    # Cost analysis
    COSTS_VIEW = "costs.view"
    COSTS_EXPORT = "costs.export"
    
    # User management
    USERS_VIEW = "users.view"
    USERS_INVITE = "users.invite"
    USERS_EDIT = "users.edit"
    USERS_REMOVE = "users.remove"
    USERS_PERMISSIONS = "users.permissions"
    
    # System administration
    SYSTEM_CONFIG = "system.config"
    SYSTEM_LOGS = "system.logs"
    SYSTEM_BACKUP = "system.backup"


class UserRole(str, Enum):
    """Predefined user roles with permission sets."""
    ADMIN = "admin"
    OPERATOR = "operator" 
    VIEWER = "viewer"
    GUEST = "guest"


class User(BaseModel):
    """User account model."""
    id: Optional[int] = None
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    is_admin: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    permissions: List[Permission] = []


class UserCreate(BaseModel):
    """Model for creating new users."""
    username: str
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.VIEWER


class UserLogin(BaseModel):
    """Model for user login."""
    username: str
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class DeviceData(BaseModel):
    """Model for device data snapshot."""
    ip: str
    alias: str
    model: str
    device_type: str
    is_on: bool
    rssi: Optional[int] = None
    mac: Optional[str] = None
    current_power_w: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    today_energy_kwh: Optional[float] = None
    month_energy_kwh: Optional[float] = None
    total_energy_kwh: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DeviceReading(BaseModel):
    """Model for storing device readings."""
    device_ip: str
    timestamp: datetime
    is_on: bool
    current_power_w: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    today_energy_kwh: Optional[float] = None
    month_energy_kwh: Optional[float] = None
    total_energy_kwh: Optional[float] = None
    rssi: Optional[int] = None


class RateType(str, Enum):
    """Types of electricity rate structures."""
    FLAT = "flat"
    TIME_OF_USE = "time_of_use"
    TIERED = "tiered"
    SEASONAL = "seasonal"
    COMBINED = "combined"  # TOU + Tiered
    SEASONAL_TIERED = "seasonal_tiered"  # Seasonal + Tiered


class TierRate(BaseModel):
    """Model for tiered rate structure."""
    min_kwh: float = 0  # Starting kWh for this tier
    max_kwh: Optional[float] = None  # None means unlimited
    rate_per_kwh: float
    description: Optional[str] = None


class TimeOfUseRate(BaseModel):
    """Model for time-of-use rate structure."""
    start_hour: int  # 0-23
    end_hour: int    # 0-23
    rate_per_kwh: float
    days_of_week: Optional[List[int]] = None  # 0=Monday, 6=Sunday; None = all days
    description: Optional[str] = None


class SeasonalRate(BaseModel):
    """Model for seasonal rate structure."""
    start_month: int  # 1-12
    end_month: int    # 1-12
    base_rate: float
    time_of_use_rates: Optional[List[TimeOfUseRate]] = None
    tier_rates: Optional[List[TierRate]] = None
    description: Optional[str] = None


class ElectricityRate(BaseModel):
    """Enhanced model for electricity rate configuration."""
    name: str
    rate_type: RateType
    currency: str = "USD"
    
    # Flat rate
    flat_rate: Optional[float] = None
    
    # Time-of-use rates
    time_of_use_rates: Optional[List[TimeOfUseRate]] = None
    
    # Tiered rates
    tier_rates: Optional[List[TierRate]] = None
    
    # Seasonal rates
    seasonal_rates: Optional[List[SeasonalRate]] = None
    
    # Additional charges
    monthly_service_charge: Optional[float] = None
    demand_charge_per_kw: Optional[float] = None
    
    # Taxes and fees
    tax_rate: Optional[float] = None  # As percentage (e.g., 8.5 for 8.5%)
    additional_fees: Optional[Dict[str, float]] = None
    
    # Metadata
    utility_provider: Optional[str] = None
    rate_schedule: Optional[str] = None
    effective_date: Optional[datetime] = None
    notes: Optional[str] = None
    

class DeviceControl(BaseModel):
    """Model for device control commands."""
    action: str  # "on" or "off"
    device_ip: str