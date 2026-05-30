#!/usr/bin/env python3
"""
Standalone test runner for Traffic Calculator
Shows detailed results for all test scenarios
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from app.services.traffic_calculator import TrafficCalculator

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_all_scenarios():
    """Run and display results for all traffic scenarios"""
    calculator = TrafficCalculator()

    # Test scenarios from our sample data
    scenarios = [
        ("Rush Hour Peak", [45, 38, 52, 41]),
        ("Normal Traffic", [25, 22, 28, 24]),
        ("Light Traffic", [8, 12, 6, 10]),
        ("Uneven Distribution", [60, 15, 18, 12]),
        ("Emergency Scenario", [30, 35, 40, 25]),
    ]

    print("🚦 FlexTraff ATCS - Traffic Calculator Test Results")
    print("=" * 65)
    print(f"{'Scenario':<20} {'Input':<20} {'Green Times':<20} {'Cycle':<8} {'Valid'}")
    print("-" * 65)

    for scenario_name, lane_counts in scenarios:
        green_times, cycle_time = calculator.calculate_green_times(lane_counts)
        valid = calculator.validate_calculation(lane_counts, green_times, cycle_time)

        input_str = str(lane_counts)
        output_str = str(green_times)
        status = "✅" if valid else "❌"

        print(
            f"{scenario_name:<20} {input_str:<20} {output_str:<20} {cycle_time:<8} {status}"
        )

    print("-" * 65)

    # Edge cases
    print("\n🔍 Edge Cases:")
    print("-" * 40)

    edge_cases = [
        ("All Zero", [0, 0, 0, 0]),
        ("One High", [100, 5, 5, 5]),
        ("Exactly 100", [25, 25, 25, 25]),
        ("Just Over 100", [26, 25, 25, 25]),
        ("Very High", [80, 70, 60, 50]),  # 260 total
    ]

    for case_name, lane_counts in edge_cases:
        green_times, cycle_time = calculator.calculate_green_times(lane_counts)
        valid = calculator.validate_calculation(lane_counts, green_times, cycle_time)
        status = "✅" if valid else "❌"

        print(
            f"{case_name:<12}: {lane_counts} → {green_times} (cycle: {cycle_time}s) {status}"
        )

    print("\n📊 Algorithm Info:")
    info = calculator.get_algorithm_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    print("\n🎉 All scenarios completed successfully!")


if __name__ == "__main__":
    run_all_scenarios()
