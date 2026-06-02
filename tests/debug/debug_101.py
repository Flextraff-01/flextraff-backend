#!/usr/bin/env python3
"""
Debug script for 101 vehicles edge case
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from app.services.traffic_calculator import TrafficCalculator

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


def debug_101_vehicles():
    calculator = TrafficCalculator()
    lane_counts = [26, 25, 25, 25]  # 101 total

    print(f"Input: {lane_counts}")
    print(f"Total vehicles: {sum(lane_counts)}")

    green_times, cycle_time = calculator.calculate_green_times(lane_counts)

    print(f"Output: {green_times}")
    print(f"Cycle time: {cycle_time}")
    print(f"Expected cycle time for 101 vehicles: 130s (120 + 10)")

    # Manual calculation check
    total = sum(lane_counts)
    if total <= 100:
        expected_cycle = 120
    else:
        excess = total - 100
        increments = (excess + 9) // 10  # Ceiling division
        expected_cycle = 120 + increments * 10

    print(
        f"Manual calculation: excess={total-100}, increments={(total-100+9)//10}, expected={expected_cycle}"
    )


if __name__ == "__main__":
    debug_101_vehicles()
