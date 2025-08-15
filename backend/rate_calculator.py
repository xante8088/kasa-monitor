"""Electricity rate calculator for various rate structures.

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

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from models import (ElectricityRate, RateType, SeasonalRate, TierRate,
                    TimeOfUseRate)


class RateCalculator:
    """Calculate electricity costs based on various rate structures."""

    @staticmethod
    def calculate_cost(
        kwh: float,
        rate: ElectricityRate,
        timestamp: Optional[datetime] = None,
        monthly_kwh: Optional[float] = None,
        peak_demand_kw: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate electricity cost based on rate structure.

        Args:
            kwh: Energy consumption in kWh
            rate: ElectricityRate configuration
            timestamp: Time of consumption (for time-of-use rates)
            monthly_kwh: Total monthly consumption (for tiered rates)
            peak_demand_kw: Peak demand in kW (for demand charges)

        Returns:
            Dictionary with cost breakdown
        """
        if not timestamp:
            timestamp = datetime.now()

        result = {
            "energy_charge": 0.0,
            "demand_charge": 0.0,
            "service_charge": 0.0,
            "taxes": 0.0,
            "fees": 0.0,
            "total": 0.0,
        }

        # Calculate energy charge based on rate type
        if rate.rate_type == RateType.FLAT:
            result["energy_charge"] = RateCalculator._calculate_flat_rate(kwh, rate)

        elif rate.rate_type == RateType.TIME_OF_USE:
            result["energy_charge"] = RateCalculator._calculate_tou_rate(
                kwh, rate, timestamp
            )

        elif rate.rate_type == RateType.TIERED:
            result["energy_charge"] = RateCalculator._calculate_tiered_rate(
                kwh, rate, monthly_kwh
            )

        elif rate.rate_type == RateType.SEASONAL:
            result["energy_charge"] = RateCalculator._calculate_seasonal_rate(
                kwh, rate, timestamp, monthly_kwh
            )

        elif rate.rate_type == RateType.COMBINED:
            result["energy_charge"] = RateCalculator._calculate_combined_rate(
                kwh, rate, timestamp, monthly_kwh
            )

        elif rate.rate_type == RateType.SEASONAL_TIERED:
            result["energy_charge"] = RateCalculator._calculate_seasonal_tiered_rate(
                kwh, rate, timestamp, monthly_kwh
            )

        # Add demand charge if applicable
        if rate.demand_charge_per_kw and peak_demand_kw:
            result["demand_charge"] = peak_demand_kw * rate.demand_charge_per_kw

        # Add monthly service charge (prorated for partial consumption)
        if rate.monthly_service_charge:
            # Prorate based on consumption period
            result["service_charge"] = rate.monthly_service_charge * (
                kwh / (monthly_kwh or kwh)
            )

        # Calculate subtotal
        subtotal = (
            result["energy_charge"] + result["demand_charge"] + result["service_charge"]
        )

        # Apply taxes
        if rate.tax_rate:
            result["taxes"] = subtotal * (rate.tax_rate / 100)

        # Add additional fees
        if rate.additional_fees:
            for fee_name, fee_amount in rate.additional_fees.items():
                result["fees"] += fee_amount

        # Calculate total
        result["total"] = (
            result["energy_charge"]
            + result["demand_charge"]
            + result["service_charge"]
            + result["taxes"]
            + result["fees"]
        )

        return result

    @staticmethod
    def _calculate_flat_rate(kwh: float, rate: ElectricityRate) -> float:
        """Calculate cost for flat rate structure."""
        if not rate.flat_rate:
            return 0.0
        return kwh * rate.flat_rate

    @staticmethod
    def _calculate_tou_rate(
        kwh: float, rate: ElectricityRate, timestamp: datetime
    ) -> float:
        """Calculate cost for time-of-use rate structure."""
        if not rate.time_of_use_rates:
            return 0.0

        hour = timestamp.hour
        day_of_week = timestamp.weekday()

        # Find applicable rate
        applicable_rate = None
        for tou_rate in rate.time_of_use_rates:
            # Check if day matches
            if tou_rate.days_of_week and day_of_week not in tou_rate.days_of_week:
                continue

            # Check if time matches
            if tou_rate.start_hour <= tou_rate.end_hour:
                # Normal case: e.g., 9-17
                if tou_rate.start_hour <= hour < tou_rate.end_hour:
                    applicable_rate = tou_rate
                    break
            else:
                # Overnight case: e.g., 22-6
                if hour >= tou_rate.start_hour or hour < tou_rate.end_hour:
                    applicable_rate = tou_rate
                    break

        if applicable_rate:
            return kwh * applicable_rate.rate_per_kwh

        # If no specific rate found, use the first rate as default
        return kwh * rate.time_of_use_rates[0].rate_per_kwh

    @staticmethod
    def _calculate_tiered_rate(
        kwh: float, rate: ElectricityRate, monthly_kwh: Optional[float] = None
    ) -> float:
        """Calculate cost for tiered rate structure with usage ranges."""
        if not rate.tier_rates:
            return 0.0

        # Sort tiers by min_kwh
        sorted_tiers = sorted(rate.tier_rates, key=lambda x: x.min_kwh)

        total_cost = 0.0
        total_monthly_usage = monthly_kwh or kwh

        # Calculate cost based on which tier(s) the total monthly usage falls into
        for tier in sorted_tiers:
            tier_min = tier.min_kwh
            tier_max = tier.max_kwh if tier.max_kwh is not None else float("inf")

            if total_monthly_usage <= tier_min:
                # Haven't reached this tier yet
                continue

            # Calculate how much usage falls in this tier
            usage_in_tier = min(total_monthly_usage, tier_max) - tier_min

            # Calculate the proportion of current consumption that falls in this tier
            if total_monthly_usage > 0:
                tier_proportion = usage_in_tier / total_monthly_usage
                kwh_in_tier = kwh * tier_proportion
                total_cost += kwh_in_tier * tier.rate_per_kwh

        return total_cost

    @staticmethod
    def _calculate_seasonal_rate(
        kwh: float,
        rate: ElectricityRate,
        timestamp: datetime,
        monthly_kwh: Optional[float] = None,
    ) -> float:
        """Calculate cost for seasonal rate structure."""
        if not rate.seasonal_rates:
            return 0.0

        month = timestamp.month

        # Find applicable season
        applicable_season = None
        for season in rate.seasonal_rates:
            if season.start_month <= season.end_month:
                # Normal case: e.g., June-September
                if season.start_month <= month <= season.end_month:
                    applicable_season = season
                    break
            else:
                # Winter case: e.g., November-March
                if month >= season.start_month or month <= season.end_month:
                    applicable_season = season
                    break

        if not applicable_season:
            # Use first season as default
            applicable_season = rate.seasonal_rates[0]

        # Check if season has time-of-use rates
        if applicable_season.time_of_use_rates:
            temp_rate = ElectricityRate(
                name="temp",
                rate_type=RateType.TIME_OF_USE,
                time_of_use_rates=applicable_season.time_of_use_rates,
            )
            return RateCalculator._calculate_tou_rate(kwh, temp_rate, timestamp)

        # Check if season has tiered rates
        if applicable_season.tier_rates:
            temp_rate = ElectricityRate(
                name="temp",
                rate_type=RateType.TIERED,
                tier_rates=applicable_season.tier_rates,
            )
            return RateCalculator._calculate_tiered_rate(kwh, temp_rate, monthly_kwh)

        # Use base rate if available, otherwise return 0
        if applicable_season.base_rate:
            return kwh * applicable_season.base_rate

        return 0.0

    @staticmethod
    def _calculate_combined_rate(
        kwh: float,
        rate: ElectricityRate,
        timestamp: datetime,
        monthly_kwh: Optional[float] = None,
    ) -> float:
        """
        Calculate cost for combined rate structure.
        This applies both time-of-use and tiered rates.
        """
        if not rate.time_of_use_rates or not rate.tier_rates:
            # Fall back to simpler calculation if missing components
            if rate.time_of_use_rates:
                return RateCalculator._calculate_tou_rate(kwh, rate, timestamp)
            elif rate.tier_rates:
                return RateCalculator._calculate_tiered_rate(kwh, rate, monthly_kwh)
            else:
                return 0.0

        # First determine the TOU rate multiplier
        hour = timestamp.hour
        day_of_week = timestamp.weekday()

        tou_rate = 1.0  # Default multiplier
        for tou in rate.time_of_use_rates:
            if tou.days_of_week and day_of_week not in tou.days_of_week:
                continue

            if tou.start_hour <= tou.end_hour:
                if tou.start_hour <= hour < tou.end_hour:
                    tou_rate = tou.rate_per_kwh
                    break
            else:
                if hour >= tou.start_hour or hour < tou.end_hour:
                    tou_rate = tou.rate_per_kwh
                    break

        # Then calculate tiered cost with TOU adjustment
        base_cost = RateCalculator._calculate_tiered_rate(kwh, rate, monthly_kwh)

        # Apply TOU multiplier (assuming TOU rate is a multiplier, not absolute)
        # If TOU rates are absolute, use them directly
        return (
            base_cost * (tou_rate if tou_rate < 2.0 else 1.0)
            if base_cost > 0
            else kwh * tou_rate
        )

    @staticmethod
    def _calculate_seasonal_tiered_rate(
        kwh: float,
        rate: ElectricityRate,
        timestamp: datetime,
        monthly_kwh: Optional[float] = None,
    ) -> float:
        """
        Calculate cost for seasonal + tiered rate structure.
        Each season has its own set of tiers.
        """
        if not rate.seasonal_rates:
            return 0.0

        month = timestamp.month

        # Find applicable season
        applicable_season = None
        for season in rate.seasonal_rates:
            if season.start_month <= season.end_month:
                # Normal case: e.g., June-September
                if season.start_month <= month <= season.end_month:
                    applicable_season = season
                    break
            else:
                # Winter case: e.g., November-March
                if month >= season.start_month or month <= season.end_month:
                    applicable_season = season
                    break

        if not applicable_season:
            # Use first season as default
            applicable_season = rate.seasonal_rates[0]

        # If the season has tier rates, use them
        if applicable_season.tier_rates:
            # Sort tiers by min_kwh
            sorted_tiers = sorted(applicable_season.tier_rates, key=lambda x: x.min_kwh)

            total_cost = 0.0
            total_monthly_usage = monthly_kwh or kwh

            # Calculate cost based on which tier(s) the total monthly usage falls into
            for tier in sorted_tiers:
                tier_min = tier.min_kwh
                tier_max = tier.max_kwh if tier.max_kwh is not None else float("inf")

                if total_monthly_usage <= tier_min:
                    # Haven't reached this tier yet
                    continue

                # Calculate how much usage falls in this tier
                usage_in_tier = min(total_monthly_usage, tier_max) - tier_min

                # Calculate the proportion of current consumption that falls in this tier
                if total_monthly_usage > 0:
                    tier_proportion = usage_in_tier / total_monthly_usage
                    kwh_in_tier = kwh * tier_proportion
                    total_cost += kwh_in_tier * tier.rate_per_kwh

            return total_cost
        elif applicable_season.base_rate:
            # Fall back to base rate if available
            return kwh * applicable_season.base_rate
        else:
            # No rates defined for this season
            return 0.0

    @staticmethod
    def estimate_monthly_cost(
        daily_kwh: float, rate: ElectricityRate, days_in_month: int = 30
    ) -> Dict[str, float]:
        """
        Estimate monthly cost based on daily consumption.

        Args:
            daily_kwh: Average daily consumption in kWh
            rate: ElectricityRate configuration
            days_in_month: Number of days in the month

        Returns:
            Dictionary with estimated monthly cost breakdown
        """
        monthly_kwh = daily_kwh * days_in_month

        # For time-of-use rates, estimate distribution
        if rate.rate_type in [RateType.TIME_OF_USE, RateType.COMBINED]:
            # Assume 30% peak, 70% off-peak as a rough estimate
            total_cost = 0.0

            # Calculate cost for different periods
            now = datetime.now()
            for hour in range(24):
                hourly_kwh = daily_kwh / 24
                timestamp = now.replace(hour=hour)
                cost = RateCalculator.calculate_cost(
                    hourly_kwh * days_in_month, rate, timestamp, monthly_kwh
                )
                total_cost += cost["total"]

            return {
                "energy_charge": total_cost * 0.8,  # Rough estimate
                "service_charge": rate.monthly_service_charge or 0,
                "taxes": total_cost * (rate.tax_rate / 100) if rate.tax_rate else 0,
                "total": total_cost,
            }
        else:
            return RateCalculator.calculate_cost(
                monthly_kwh, rate, monthly_kwh=monthly_kwh
            )
