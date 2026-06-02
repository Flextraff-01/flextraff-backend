#!/usr/bin/env python3
"""
Debug script to understand the light traffic scenario issue
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from app.services.traffic_calculator import TrafficCalculator

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


def debug_light_traffic():
    calculator = TrafficCalculator()
    lane_counts = [8, 12, 6, 10]  # Light traffic - all ≤15

    print(f"Input: {lane_counts}")
    print(f"All lanes ≤15? {all(count <= 15 for count in lane_counts)}")
    print(f"Total vehicles: {sum(lane_counts)}")

    green_times, cycle_time = calculator.calculate_green_times(lane_counts)

    print(f"Output: {green_times}")
    print(f"Cycle time: {cycle_time}")
    print(f"Sum of green times: {sum(green_times)}")
    print(f"Expected cycle time (≤100 vehicles): 120s")
    print(f"Expected green times: [15, 15, 15, 15] (all lanes ≤15 vehicles)")

    # Check what went wrong
    for i, (count, time) in enumerate(zip(lane_counts, green_times)):
        print(f"Lane {i+1}: {count} vehicles → {time}s green time")


if __name__ == "__main__":
    debug_light_traffic()
