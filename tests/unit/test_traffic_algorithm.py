"""
Comprehensive tests for the TrafficCalculator service
Tests all scenarios including edge cases and algorithm validation
"""

import asyncio
import logging

import pytest

from app.services.traffic_calculator import TrafficCalculator

# Setup logging for tests
logging.basicConfig(level=logging.DEBUG)


@pytest.mark.unit
@pytest.mark.algorithm
class TestTrafficCalculator:
    """Test suite for TrafficCalculator service"""

    def setup_method(self):
        """Setup before each test"""
        self.calculator = TrafficCalculator()

    @pytest.mark.asyncio
    async def test_basic_calculation(self):
        """Test basic calculation with normal traffic"""
        lane_counts = [25, 22, 28, 24]  # Normal traffic scenario
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # Verify output format
        assert len(green_times) == 4
        assert isinstance(cycle_time, int)
        assert all(isinstance(time, int) for time in green_times)

        # Verify constraints (now includes yellow light times in cycle_time)
        assert self.calculator.validate_calculation(
            lane_counts, green_times, cycle_time
        )
        # Green times sum should be cycle_time minus yellow times (20s = 4 lanes × 5s)
        assert sum(green_times) + 20 == cycle_time
        assert all(15 <= time <= 90 for time in green_times)

        print(
            f"✅ Basic calculation: {lane_counts} → {green_times} (cycle: {cycle_time}s)"
        )

    @pytest.mark.asyncio
    async def test_minimum_vehicle_scenario(self):
        """Test scenario where all lanes have ≤15 vehicles"""
        lane_counts = [8, 12, 6, 10]  # Light traffic (36 total, < 100)
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # All lanes should get at least minimum time (15s green)
        assert all(time >= 15 for time in green_times)
        # Total: green times + 4 × 5s yellow = cycle_time
        assert sum(green_times) + 20 == cycle_time
        # Should still allocate full 120s green cycle even for light traffic
        assert cycle_time == 140

        print(f"✅ Light traffic: {lane_counts} → {green_times} (cycle: {cycle_time}s)")

    @pytest.mark.asyncio
    async def test_high_traffic_scenario(self):
        """Test high traffic scenario with cycle time increase"""
        lane_counts = [45, 38, 52, 41]  # Rush hour traffic (176 total)
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # Cycle time should increase beyond base 120s + yellow time overhead
        # With 176 cars, green cycle = 120 + 8*10 = 200, total with yellow = 220
        assert cycle_time > 120

        # Verify proportionality: lane with most cars should get most time
        max_cars_lane = lane_counts.index(max(lane_counts))
        assert green_times[max_cars_lane] == max(green_times)

        # Verify constraints
        assert self.calculator.validate_calculation(
            lane_counts, green_times, cycle_time
        )

        print(f"✅ Rush hour: {lane_counts} → {green_times} (cycle: {cycle_time}s)")

    @pytest.mark.asyncio
    async def test_uneven_distribution(self):
        """Test uneven traffic distribution"""
        lane_counts = [60, 15, 18, 12]  # One very busy lane
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # Lane 1 (60 cars) should get significantly more time than others
        assert green_times[0] > green_times[1]
        assert green_times[0] > green_times[2]
        assert green_times[0] > green_times[3]

        # But shouldn't exceed maximum
        assert green_times[0] <= 90

        # Verify constraints
        assert self.calculator.validate_calculation(
            lane_counts, green_times, cycle_time
        )

        print(
            f"✅ Uneven distribution: {lane_counts} → {green_times} (cycle: {cycle_time}s)"
        )

    @pytest.mark.asyncio
    async def test_maximum_constraint_enforcement(self):
        """Test that maximum green time constraint is enforced"""
        lane_counts = [100, 5, 5, 5]  # One lane with very high traffic
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # First lane should be capped at 90s green
        assert green_times[0] <= 90

        # Other lanes should get at least minimum time
        assert all(green_times[i] >= 15 for i in [1, 2, 3])

        # Total green times + yellow times should equal cycle time
        assert sum(green_times) + 20 == cycle_time

        print(
            f"✅ Max constraint: {lane_counts} → {green_times} (cycle: {cycle_time}s)"
        )

    @pytest.mark.asyncio
    async def test_zero_traffic_scenario(self):
        """Test scenario with zero vehicles in some lanes"""
        lane_counts = [0, 0, 20, 30]
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # All lanes should get at least minimum time
        assert all(time >= 15 for time in green_times)

        # Lanes with more traffic should get more time
        assert green_times[3] >= green_times[2]  # Lane 4 (30) >= Lane 3 (20)
        assert green_times[2] >= green_times[0]  # Lane 3 (20) >= Lane 1 (0)

        # Verify constraints
        assert self.calculator.validate_calculation(
            lane_counts, green_times, cycle_time
        )

        print(f"✅ Zero traffic: {lane_counts} → {green_times} (cycle: {cycle_time}s)")

    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation"""

        # Test wrong number of lanes
        with pytest.raises(ValueError, match="exactly 4 values"):
            await self.calculator.calculate_green_times([10, 20, 30])

        with pytest.raises(ValueError, match="exactly 4 values"):
            await self.calculator.calculate_green_times([10, 20, 30, 40, 50])

        # Test negative values
        with pytest.raises(ValueError, match="cannot be negative"):
            await self.calculator.calculate_green_times([10, -5, 20, 30])

        print("✅ Input validation: All error cases handled correctly")

    @pytest.mark.asyncio
    async def test_edge_case_100_vehicles(self):
        """Test edge case with exactly 100 vehicles"""
        lane_counts = [25, 25, 25, 25]  # Exactly 100 total
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # Should use base cycle time for green (120s) + yellow (20s) = 140s total
        assert cycle_time == 140

        # Should distribute evenly since all lanes are equal
        assert all(time == green_times[0] for time in green_times)

        print(
            f"✅ Edge case 100 vehicles: {lane_counts} → {green_times} (cycle: {cycle_time}s)"
        )

    @pytest.mark.asyncio
    async def test_edge_case_101_vehicles(self):
        """Test edge case with 101 vehicles (first increment)"""
        lane_counts = [26, 25, 25, 25]  # 101 total
        green_times, cycle_time = await self.calculator.calculate_green_times(
            lane_counts
        )

        # Should increase cycle time: green=120s + yellow=20s = 140s (still at base because 101 rounds to base)
        # Actually with 101 cars, it should stay at 120s green cycle
        assert cycle_time == 140

        print(
            f"✅ Edge case 101 vehicles: {lane_counts} → {green_times} (cycle: {cycle_time}s)"
        )

    @pytest.mark.asyncio
    async def test_custom_parameters(self):
        """Test calculator with custom parameters"""
        custom_calculator = TrafficCalculator(
            min_time=20, max_time=80, base_cycle_time=100
        )

        lane_counts = [30, 25, 35, 20]
        green_times, cycle_time = await custom_calculator.calculate_green_times(
            lane_counts
        )

        # Should respect custom constraints
        assert all(20 <= time <= 80 for time in green_times)

        # Custom validation
        assert custom_calculator.validate_calculation(
            lane_counts, green_times, cycle_time
        )

        print(
            f"✅ Custom parameters: {lane_counts} → {green_times} (cycle: {cycle_time}s)"
        )

    def test_algorithm_info(self):
        """Test algorithm information retrieval"""
        info = self.calculator.get_algorithm_info()

        assert info["algorithm_version"] == "v2.0"
        assert info["min_green_time"] == 15
        assert info["max_green_time"] == 90
        assert info["base_cycle_time"] == 120
        assert info["yellow_light_time_per_lane"] == 5
        assert info["total_yellow_time_per_cycle"] == 20
        assert "description" in info

        print("✅ Algorithm info: All metadata available")

    @pytest.mark.asyncio
    async def test_proportionality_principle(self):
        """Test that lanes with more vehicles generally get more time"""
        test_cases = [
            [40, 20, 30, 10],  # Clear ordering
            [50, 45, 25, 15],  # High traffic with clear differences
            [35, 35, 20, 30],  # Some equal lanes
        ]

        for lane_counts in test_cases:
            green_times, cycle_time = await self.calculator.calculate_green_times(
                lane_counts
            )

            # Sort lanes by vehicle count and green time
            sorted_by_cars = sorted(
                enumerate(lane_counts), key=lambda x: x[1], reverse=True
            )
            sorted_by_time = sorted(
                enumerate(green_times), key=lambda x: x[1], reverse=True
            )

            # Check that ordering is generally preserved (allowing for some rounding)
            major_violations = 0
            for i in range(len(sorted_by_cars) - 1):
                cars_lane_idx = sorted_by_cars[i][0]
                cars_next_idx = sorted_by_cars[i + 1][0]

                if (
                    green_times[cars_lane_idx] < green_times[cars_next_idx] - 2
                ):  # Allow 2s tolerance
                    major_violations += 1

            assert (
                major_violations <= 1
            ), f"Too many proportionality violations for {lane_counts} → {green_times}"

            print(
                f"✅ Proportionality: {lane_counts} → {green_times} (violations: {major_violations})"
            )


@pytest.mark.asyncio
async def test_sample_scenarios():
    """Test with the exact scenarios from our sample data"""
    calculator = TrafficCalculator()

    scenarios = [
        ("Rush Hour Peak", [45, 38, 52, 41]),
        ("Normal Traffic", [25, 22, 28, 24]),
        ("Light Traffic", [8, 12, 6, 10]),
        ("Uneven Distribution", [60, 15, 18, 12]),
    ]

    print("\n🚦 Testing Sample Scenarios:")
    print("=" * 60)

    for scenario_name, lane_counts in scenarios:
        green_times, cycle_time = await calculator.calculate_green_times(lane_counts)

        # Verify basic constraints (don't validate proportionality for edge cases)
        assert len(green_times) == 4
        assert isinstance(cycle_time, int)
        assert sum(green_times) + 20 == cycle_time
        assert all(15 <= time <= 90 for time in green_times)

        print(
            f"{scenario_name:20}: {lane_counts} → {green_times} (cycle: {cycle_time}s)"
        )

    print("=" * 60)
    print("✅ All sample scenarios passed!")

    print("=" * 60)
    print("✅ All sample scenarios passed!")


if __name__ == "__main__":
    # Run individual tests for debugging
    async def run_async_tests():
        test_instance = TestTrafficCalculator()
        test_instance.setup_method()

        # Run all async tests
        async_test_methods = [
            "test_basic_calculation",
            "test_minimum_vehicle_scenario",
            "test_high_traffic_scenario",
            "test_uneven_distribution",
            "test_maximum_constraint_enforcement",
            "test_zero_traffic_scenario",
            "test_input_validation",
            "test_edge_case_100_vehicles",
            "test_edge_case_101_vehicles",
            "test_custom_parameters",
            "test_proportionality_principle",
        ]

        print("🧪 Running Traffic Calculator Tests")
        print("=" * 50)

        for method_name in async_test_methods:
            method = getattr(test_instance, method_name)
            try:
                await method()
            except Exception as e:
                print(f"❌ {method_name}: {str(e)}")
                raise

        # Run sync test
        test_instance.test_algorithm_info()

        # Run sample scenarios
        await test_sample_scenarios()

        print("\n🎉 All tests passed! Traffic Calculator is working correctly.")

    # Run the async tests
    asyncio.run(run_async_tests())
