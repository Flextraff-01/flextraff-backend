"""
Traffic Calculator Service - Adaptive Traffic Light Timing Algorithm
Includes support for green and yellow light phases
"""

import logging
from typing import List, Tuple
from datetime import datetime


class TrafficCalculator:
    """
    ATCS Core Algorithm - Adaptive Traffic Light Timing Calculator

    Implements intelligent traffic timing calculation algorithm that
    dynamically adjusts green light durations based on real-time vehicle counts.
    Now includes yellow light phase (5 seconds per lane).
    """

    # Yellow light configuration (constant)
    YELLOW_LIGHT_TIME = 5  # Fixed 5 seconds per lane

    def __init__(self, min_time: int = 15, max_time: int = 90, base_cycle_time: int = 120, db_service=None):
        self.min_time = min_time
        self.max_time = max_time
        self.base_cycle_time = base_cycle_time
        self.db_service = db_service
        self.logger = logging.getLogger(__name__)

    async def calculate_green_times(
        self,
        lane_counts: List[int],
        junction_id: int = None
    ) -> Tuple[List[int], int]:
        """
        Calculate optimal green times for each lane based on vehicle counts

        Algorithm Logic:
        1. Count total vehicles across all 4 lanes
        2. Calculate yellow light time: 4 lanes × 5 seconds = 20 seconds total
        3. Determine cycle time: 120s base (for green only), +10s per 10 vehicles over 100, max 180s
        4. For each lane: ≤15 vehicles = 15s green time, else proportional allocation
        5. Calculate remaining time for adjustable lanes
        6. Cap at 90s max per lane with redistribution
        7. Round to whole seconds and balance total
        8. Total cycle time = green times + yellow times

        Args:
            lane_counts (List[int]): Vehicle count [lane1, lane2, lane3, lane4]
            junction_id (int, optional): Junction ID for logging

        Returns:
            Tuple[List[int], int]: (green_times_per_lane, total_cycle_time_including_yellow)
        """
        start_time = datetime.now()

        if len(lane_counts) != 4:
            raise ValueError("Lane counts must contain exactly 4 values")

        if any(count < 0 for count in lane_counts):
            raise ValueError("Lane counts cannot be negative")

        num_lanes = 4
        total_cars = sum(lane_counts)

        # Calculate yellow light overhead (5 seconds per lane)
        total_yellow_time = num_lanes * self.YELLOW_LIGHT_TIME

        self.logger.info(
            f"Calculating green times for lane counts: {lane_counts}, "
            f"total vehicles: {total_cars}, yellow time overhead: {total_yellow_time}s"
        )

        # Step 1: Calculate base cycle time (for green phases only)
        if total_cars <= 100:
            green_cycle_time = self.base_cycle_time
        else:
            increments = (total_cars - 100) // 10
            green_cycle_time = self.base_cycle_time + increments * 10
            green_cycle_time = min(green_cycle_time, 180)

        # Step 2: Initial green time allocation
        rem_time = green_cycle_time - self.min_time * num_lanes
        green_times_raw = []
        fixed_lanes = []
        adjustable_lanes = []

        for idx, count in enumerate(lane_counts):
            if count <= self.min_time:
                green_times_raw.append(self.min_time)
                fixed_lanes.append(idx)
            else:
                green_time = self.min_time + ((count - self.min_time) / total_cars) * rem_time
                green_times_raw.append(green_time)
                adjustable_lanes.append(idx)

        # Step 3: Proportional allocation for adjustable lanes
        fixed_sum = sum(green_times_raw[i] for i in fixed_lanes)
        adjustable_cycle_time = green_cycle_time - fixed_sum
        adjustable_raw_sum = sum(green_times_raw[i] for i in adjustable_lanes)

        green_times = green_times_raw.copy()
        if adjustable_raw_sum > 0:
            for i in adjustable_lanes:
                green_times[i] = (green_times_raw[i] / adjustable_raw_sum) * adjustable_cycle_time

        # Step 4: Enforce maximum time with redistribution
        while True:
            excess_time = 0
            under_max_lanes = []
            for i in adjustable_lanes:
                if green_times[i] > self.max_time:
                    excess_time += green_times[i] - self.max_time
                    green_times[i] = self.max_time
                else:
                    under_max_lanes.append(i)

            if excess_time > 0 and under_max_lanes:
                distribute_per_lane = excess_time / len(under_max_lanes)
                for i in under_max_lanes:
                    green_times[i] += distribute_per_lane
            else:
                break

        # Step 5: Final rounding and balancing (green times only)
        green_times_rounded = [round(t) for t in green_times]
        diff = green_cycle_time - sum(green_times_rounded)
        green_times_rounded[-1] += diff

        # Step 6: Calculate total cycle time (green + yellow)
        total_cycle_time = green_cycle_time + total_yellow_time

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        self.logger.info(
            f"Calculated green times: {green_times_rounded}, "
            f"green cycle time: {green_cycle_time}s, "
            f"yellow cycle time: {total_yellow_time}s, "
            f"total cycle time: {total_cycle_time}s, "
            f"execution time: {execution_time:.2f}ms"
        )

        return green_times_rounded, total_cycle_time

    def get_yellow_times(self) -> List[int]:
        """
        Get yellow light times for all lanes

        Returns:
            List[int]: Yellow times for each lane [5, 5, 5, 5]
        """
        return [self.YELLOW_LIGHT_TIME] * 4

    # def get_full_cycle_breakdown(
    #     self,
    #     lane_counts: List[int],
    #     junction_id: int = None
    # ) -> dict:
    #     """
    #     Get detailed breakdown of traffic light cycle including green and yellow phases

    #     Returns:
    #         dict: Complete cycle breakdown with green times, yellow times, and totals
    #     """
    #     # Will be implemented as async
    #     raise NotImplementedError("Use async version: get_full_cycle_breakdown_async")

    async def get_full_cycle_breakdown_async(
        self,
        lane_counts: List[int],
        junction_id: int = None
    ) -> dict:
        """
        Get detailed breakdown of traffic light cycle including green and yellow phases

        Args:
            lane_counts (List[int]): Vehicle count per lane
            junction_id (int, optional): Junction ID for logging

        Returns:
            dict: Complete cycle breakdown with green times, yellow times, and totals
        """
        green_times, total_cycle_time = await self.calculate_green_times(
            lane_counts, junction_id
        )
        yellow_times = self.get_yellow_times()
        green_cycle_time = total_cycle_time - sum(yellow_times)

        return {
            "lane_counts": lane_counts,
            "green_times": green_times,
            "yellow_times": yellow_times,
            "green_cycle_time": green_cycle_time,
            "yellow_cycle_time": sum(yellow_times),
            "total_cycle_time": total_cycle_time,
            "lane_phases": [
                {
                    "lane": i + 1,
                    "vehicles": lane_counts[i],
                    "green_time": green_times[i],
                    "yellow_time": yellow_times[i],
                    "total_lane_time": green_times[i] + yellow_times[i],
                }
                for i in range(4)
            ],
        }

    def validate_calculation(
        self,
        lane_counts: List[int],
        green_times: List[int],
        cycle_time: int
    ) -> bool:
        """
        Validate that calculated times meet all constraints

        Args:
            lane_counts (List[int]): Vehicle counts per lane
            green_times (List[int]): Calculated green times per lane
            cycle_time (int): Total cycle time (green + yellow)

        Returns:
            bool: True if all constraints are met
        """
        # Check bounds
        if any(time < self.min_time or time > self.max_time for time in green_times):
            return False

        # Calculate expected green cycle time (cycle_time - yellow_time)
        total_yellow = len(lane_counts) * self.YELLOW_LIGHT_TIME
        green_cycle_time = cycle_time - total_yellow

        # Check green times sum equals green cycle time
        if sum(green_times) != green_cycle_time:
            return False

        # Check proportionality (allow 2s rounding difference)
        for i in range(len(lane_counts)):
            for j in range(i + 1, len(lane_counts)):
                if lane_counts[i] > lane_counts[j] and green_times[i] < green_times[j]:
                    if green_times[j] - green_times[i] > 2:
                        return False

        return True

    def get_algorithm_info(self) -> dict:
        """
        Get algorithm metadata and configuration

        Returns:
            dict: Algorithm information including version and parameters
        """
        return {
            "algorithm_version": "v2.0",
            "algorithm_name": "Adaptive Traffic Control System (ATCS) with Yellow Lights",
            "min_green_time": self.min_time,
            "max_green_time": self.max_time,
            "base_cycle_time": self.base_cycle_time,
            "yellow_light_time_per_lane": self.YELLOW_LIGHT_TIME,
            "total_yellow_time_per_cycle": 4 * self.YELLOW_LIGHT_TIME,
            "description": (
                "Calculates optimal green light timing based on vehicle counts. "
                "Includes fixed 5-second yellow phase per lane. "
                "Dynamically adjusts cycle time based on total vehicle count. "
                "Ensures proportional allocation while respecting min/max constraints."
            ),
        }

    def get_fallback_times(self) -> Tuple[List[int], int]:
        """
        Get fallback/offline mode timing when internet/vehicle detection is unavailable.
        Uses maximum cycle time with equal distribution across all lanes.

        This is used when:
        - Raspberry Pi loses internet connection
        - Vehicle detection system is offline
        - Communication with backend server fails

        Returns:
            Tuple[List[int], int]: (green_times_per_lane, total_cycle_time_with_yellow)
        """
        # Each lane gets maximum green time (90s) for safe traffic flow
        max_green_time_per_lane = self.max_time
        green_times = [max_green_time_per_lane] * 4

        # Calculate total: max green time per lane × 4 lanes + yellow times
        total_green_cycle = sum(green_times)
        total_yellow_time = 4 * self.YELLOW_LIGHT_TIME
        total_cycle_time = total_green_cycle + total_yellow_time

        self.logger.warning(
            "⚠️ FALLBACK MODE ACTIVATED: Using offline/safe timing. "
            f"All lanes get {max_green_time_per_lane}s green + "
            f"{self.YELLOW_LIGHT_TIME}s yellow. "
            f"Total cycle time: {total_cycle_time}s"
        )

        return green_times, total_cycle_time

    async def calculate_green_times_with_fallback(
        self,
        lane_counts: List[int],
        junction_id: int = None,
        is_offline: bool = False
    ) -> Tuple[List[int], int, bool]:
        """
        Calculate green times with automatic fallback to offline mode.

        This method checks for connectivity/data availability and automatically
        switches to safe offline timing if needed.

        Args:
            lane_counts (List[int]): Vehicle count [lane1, lane2, lane3, lane4]
            junction_id (int, optional): Junction ID for logging
            is_offline (bool): Flag to force offline mode (for testing/simulation)

        Returns:
            Tuple[List[int], int, bool]: (green_times, cycle_time, is_using_fallback)
                                         Third element indicates if fallback was used
        """
        if is_offline or lane_counts is None or len(lane_counts) == 0:
            green_times, cycle_time = self.get_fallback_times()
            return green_times, cycle_time, True

        try:
            # Try to calculate with actual vehicle data
            green_times, cycle_time = await self.calculate_green_times(
                lane_counts, junction_id
            )
            self.logger.info(
                f"✅ Online mode: Calculated adaptive timing "
                f"for {lane_counts} vehicles"
            )
            return green_times, cycle_time, False

        except Exception as e:
            # If calculation fails, fall back to safe offline mode
            self.logger.error(
                f"❌ Error calculating green times: {str(e)}. "
                f"Switching to fallback/offline mode."
            )
            green_times, cycle_time = self.get_fallback_times()
            return green_times, cycle_time, True

    def get_fallback_info(self) -> dict:
        """
        Get information about fallback/offline mode

        Returns:
            dict: Fallback mode configuration and behavior
        """
        fallback_green, fallback_cycle = self.get_fallback_times()
        return {
            "mode": "fallback_offline",
            "description": "Safe offline mode for when internet/detection is unavailable",
            "trigger_conditions": [
                "Raspberry Pi internet connection lost",
                "Vehicle detection system offline",
                "Communication with backend server failed",
                "Invalid or null vehicle count data"
            ],
            "green_times_per_lane": fallback_green,
            "yellow_time_per_lane": self.YELLOW_LIGHT_TIME,
            "total_cycle_time": fallback_cycle,
            "behavior": "Equal distribution - all lanes get maximum safe green time",
            "safety_level": "High - ensures safe traffic flow even without real-time data"
        }
