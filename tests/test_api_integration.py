"""
Integration tests for FlexTraff API endpoints
Tests actual API server with real database connections
"""

import asyncio
from datetime import date
from typing import Any, Dict

import aiohttp
import pytest

from tests.conftest import (TestData, assert_response_schema,
                            assert_valid_cycle_time, assert_valid_green_times)


@pytest.mark.skip(reason="Requires running API server - use for manual testing only")
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestAPIIntegration:
    """Integration tests for the live API server"""

    API_BASE_URL = "http://127.0.0.1:8001"

    @pytest.mark.asyncio
    async def test_api_server_running(self, aio_session: aiohttp.ClientSession):
        """Test that API server is running and accessible"""
        async with aio_session.get(f"{self.API_BASE_URL}/") as response:
            assert response.status == 200
            data = await response.json()
            assert data["service"] == "FlexTraff ATCS API"

    @pytest.mark.asyncio
    async def test_health_check_integration(self, aio_session: aiohttp.ClientSession):
        """Test health check endpoint with real database"""
        async with aio_session.get(f"{self.API_BASE_URL}/health") as response:
            assert response.status == 200
            data = await response.json()

            # Verify response schema
            assert_response_schema(data, TestData.HEALTH_RESPONSE_SCHEMA)

            # Should have database connection in integration test
            assert data["database_connected"] is True
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_junctions_integration(self, aio_session: aiohttp.ClientSession):
        """Test junctions endpoint with real database"""
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            assert response.status == 200
            data = await response.json()

            assert "junctions" in data
            assert isinstance(data["junctions"], list)

            # Should have at least one junction in test database
            if data["junctions"]:
                junction = data["junctions"][0]
                assert "id" in junction
                assert "junction_name" in junction
                assert "status" in junction

    @pytest.mark.asyncio
    async def test_traffic_calculation_integration(
        self, aio_session: aiohttp.ClientSession
    ):
        """Test traffic calculation with real algorithm"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Test calculation with various scenarios
        test_scenarios = [
            ("Rush Hour", TestData.RUSH_HOUR_LANES),
            ("Normal Traffic", TestData.NORMAL_TRAFFIC_LANES),
            ("Light Traffic", TestData.LIGHT_TRAFFIC_LANES),
            ("Uneven Traffic", TestData.UNEVEN_TRAFFIC_LANES),
        ]

        for scenario_name, lane_counts in test_scenarios:
            request_data = {"lane_counts": lane_counts, "junction_id": junction_id}

            async with aio_session.post(
                f"{self.API_BASE_URL}/calculate-timing", json=request_data
            ) as response:
                assert response.status == 200, f"Failed for {scenario_name}"
                data = await response.json()

                # Verify response schema
                assert_response_schema(
                    data, TestData.TRAFFIC_CALCULATION_RESPONSE_SCHEMA
                )

                # Verify calculation results
                assert_valid_green_times(data["green_times"])
                assert_valid_cycle_time(data["cycle_time"])
                assert data["junction_id"] == junction_id

                # Verify algorithm info
                assert "algorithm_info" in data
                assert isinstance(data["algorithm_info"], dict)

    @pytest.mark.asyncio
    async def test_vehicle_detection_integration(
        self, aio_session: aiohttp.ClientSession
    ):
        """Test vehicle detection logging with real database"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Test vehicle detection logging
        detection_data = {
            "junction_id": junction_id,
            "lane_number": 1,
            "fastag_id": f"INTEGRATION_TEST_{asyncio.current_task().get_name()}",
            "vehicle_type": "car",
        }

        async with aio_session.post(
            f"{self.API_BASE_URL}/vehicle-detection", json=detection_data
        ) as response:
            assert response.status == 200
            data = await response.json()

            assert data["status"] == "success"
            assert data["junction_id"] == junction_id
            assert data["lane"] == 1
            assert detection_data["fastag_id"] in data["fastag_id"]

    @pytest.mark.asyncio
    async def test_junction_status_integration(
        self, aio_session: aiohttp.ClientSession
    ):
        """Test junction status with real database"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Test junction status
        async with aio_session.get(
            f"{self.API_BASE_URL}/junction/{junction_id}/status"
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Verify response schema
            assert_response_schema(data, TestData.JUNCTION_STATUS_RESPONSE_SCHEMA)

            # Verify data
            assert data["junction_id"] == junction_id
            assert isinstance(data["junction_name"], str)
            assert isinstance(data["current_lane_counts"], list)
            assert isinstance(data["total_vehicles_today"], int)

    @pytest.mark.asyncio
    async def test_live_timing_integration(self, aio_session: aiohttp.ClientSession):
        """Test live timing calculation with real data"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Test live timing
        async with aio_session.get(
            f"{self.API_BASE_URL}/junction/{junction_id}/live-timing"
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Verify response structure
            expected_keys = [
                "junction_id",
                "current_lane_counts",
                "recommended_green_times",
                "total_cycle_time",
                "time_window_minutes",
                "algorithm_info",
            ]
            for key in expected_keys:
                assert key in data

            # Verify data types and values
            assert data["junction_id"] == junction_id
            assert isinstance(data["current_lane_counts"], list)
            assert len(data["current_lane_counts"]) == 4
            assert_valid_green_times(data["recommended_green_times"])
            assert_valid_cycle_time(data["total_cycle_time"])
            assert isinstance(data["time_window_minutes"], int)
            assert data["time_window_minutes"] == 5  # default value

    @pytest.mark.asyncio
    async def test_live_timing_custom_time_window(
        self, aio_session: aiohttp.ClientSession
    ):
        """Test live timing with custom time window"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Test with custom time window
        time_window = 10
        async with aio_session.get(
            f"{self.API_BASE_URL}/junction/{junction_id}/live-timing?time_window={time_window}"
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data["time_window_minutes"] == time_window

    @pytest.mark.asyncio
    async def test_junction_history_integration(
        self, aio_session: aiohttp.ClientSession
    ):
        """Test junction history with real database"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Test junction history
        async with aio_session.get(
            f"{self.API_BASE_URL}/junction/{junction_id}/history"
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Verify response structure
            expected_keys = [
                "junction_id",
                "recent_detections",
                "latest_cycle",
                "total_records",
            ]
            for key in expected_keys:
                assert key in data

            # Verify data types
            assert data["junction_id"] == junction_id
            assert isinstance(data["recent_detections"], list)
            assert isinstance(data["total_records"], int)
            assert data["total_records"] == len(data["recent_detections"])

    @pytest.mark.asyncio
    async def test_daily_summary_integration(self, aio_session: aiohttp.ClientSession):
        """Test daily summary with real database"""
        async with aio_session.get(
            f"{self.API_BASE_URL}/analytics/daily-summary"
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Verify response structure
            expected_keys = ["date", "junction_summaries", "total_vehicles"]
            for key in expected_keys:
                assert key in data

            # Verify data types
            assert data["date"] == date.today().isoformat()
            assert isinstance(data["junction_summaries"], list)
            assert isinstance(data["total_vehicles"], int)

            # Verify junction summaries structure
            for summary in data["junction_summaries"]:
                required_keys = [
                    "junction_id",
                    "junction_name",
                    "total_vehicles",
                    "date",
                ]
                for key in required_keys:
                    assert key in summary
                assert isinstance(summary["junction_id"], int)
                assert isinstance(summary["junction_name"], str)
                assert isinstance(summary["total_vehicles"], int)
                assert summary["date"] == data["date"]

            # Verify total vehicles calculation
            calculated_total = sum(
                s["total_vehicles"] for s in data["junction_summaries"]
            )
            assert data["total_vehicles"] == calculated_total


@pytest.mark.skip(reason="Requires running API server - use for manual testing only")
class TestAPIErrorHandling:
    """Test error handling in API endpoints"""

    API_BASE_URL = "http://127.0.0.1:8001"

    @pytest.mark.asyncio
    async def test_invalid_junction_id(self, aio_session: aiohttp.ClientSession):
        """Test endpoints with invalid junction IDs"""
        invalid_id = 99999

        # Test junction status with invalid ID
        async with aio_session.get(
            f"{self.API_BASE_URL}/junction/{invalid_id}/status"
        ) as response:
            assert response.status == 404

        # Test live timing with invalid ID
        async with aio_session.get(
            f"{self.API_BASE_URL}/junction/{invalid_id}/live-timing"
        ) as response:
            # Should return 200 but with empty/zero data
            assert response.status == 200

        # Test junction history with invalid ID
        async with aio_session.get(
            f"{self.API_BASE_URL}/junction/{invalid_id}/history"
        ) as response:
            # Should return 200 but with empty data
            assert response.status == 200

    @pytest.mark.asyncio
    async def test_invalid_request_data(self, aio_session: aiohttp.ClientSession):
        """Test endpoints with invalid request data"""
        # Test traffic calculation with invalid data
        invalid_requests = [
            {},  # Missing lane_counts
            {"lane_counts": []},  # Empty lane_counts
            {"lane_counts": [10, 20]},  # Too few lanes
            {"lane_counts": [10, 20, 30, 40, 50]},  # Too many lanes
            {"lane_counts": [-5, 10, 20, 30]},  # Negative values
            {"lane_counts": "invalid"},  # Wrong type
        ]

        for invalid_data in invalid_requests:
            async with aio_session.post(
                f"{self.API_BASE_URL}/calculate-timing", json=invalid_data
            ) as response:
                assert response.status == 422  # Validation error

        # Test vehicle detection with invalid data
        invalid_detections = [
            {},  # Missing fields
            {
                "junction_id": -1,
                "lane_number": 1,
                "fastag_id": "TEST",
                "vehicle_type": "car",
            },  # Invalid junction
            {
                "junction_id": 1,
                "lane_number": 5,
                "fastag_id": "TEST",
                "vehicle_type": "car",
            },  # Invalid lane
            {
                "junction_id": 1,
                "lane_number": 1,
                "fastag_id": "",
                "vehicle_type": "car",
            },  # Empty fastag
        ]

        for invalid_data in invalid_detections:
            async with aio_session.post(
                f"{self.API_BASE_URL}/vehicle-detection", json=invalid_data
            ) as response:
                assert response.status == 422  # Validation error

    @pytest.mark.asyncio
    async def test_malformed_json(self, aio_session: aiohttp.ClientSession):
        """Test endpoints with malformed JSON"""
        malformed_json = '{"lane_counts": [10, 20, 30, 40'  # Missing closing bracket

        async with aio_session.post(
            f"{self.API_BASE_URL}/calculate-timing",
            data=malformed_json,
            headers={"Content-Type": "application/json"},
        ) as response:
            assert response.status == 422  # JSON decode error

    @pytest.mark.asyncio
    async def test_unsupported_methods(self, aio_session: aiohttp.ClientSession):
        """Test endpoints with unsupported HTTP methods"""
        # Test GET on POST-only endpoints
        async with aio_session.get(f"{self.API_BASE_URL}/calculate-timing") as response:
            assert response.status == 405  # Method not allowed

        async with aio_session.get(
            f"{self.API_BASE_URL}/vehicle-detection"
        ) as response:
            assert response.status == 405  # Method not allowed

        # Test POST on GET-only endpoints
        async with aio_session.post(f"{self.API_BASE_URL}/junctions") as response:
            assert response.status == 405  # Method not allowed


@pytest.mark.skip(reason="Requires running API server - use for manual testing only")
class TestAPIPerformance:
    """Performance tests for API endpoints"""

    API_BASE_URL = "http://127.0.0.1:8001"

    @pytest.mark.asyncio
    async def test_concurrent_calculations(self, aio_session: aiohttp.ClientSession):
        """Test concurrent traffic calculations"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Create multiple concurrent requests
        tasks = []
        scenarios = [
            TestData.RUSH_HOUR_LANES,
            TestData.NORMAL_TRAFFIC_LANES,
            TestData.LIGHT_TRAFFIC_LANES,
            TestData.UNEVEN_TRAFFIC_LANES,
        ]

        async def make_calculation_request(lane_counts):
            request_data = {"lane_counts": lane_counts, "junction_id": junction_id}
            async with aio_session.post(
                f"{self.API_BASE_URL}/calculate-timing", json=request_data
            ) as response:
                assert response.status == 200
                return await response.json()

        # Create 10 concurrent requests
        for i in range(10):
            scenario = scenarios[i % len(scenarios)]
            tasks.append(make_calculation_request(scenario))

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert len(results) == 10
        for result in results:
            assert_valid_green_times(result["green_times"])
            assert_valid_cycle_time(result["cycle_time"])

    @pytest.mark.asyncio
    async def test_rapid_vehicle_detections(self, aio_session: aiohttp.ClientSession):
        """Test rapid vehicle detection logging"""
        # Get a junction ID first
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Create multiple rapid detection requests
        async def log_detection(detection_id):
            detection_data = {
                "junction_id": junction_id,
                "lane_number": (detection_id % 4) + 1,
                "fastag_id": f"PERF_TEST_{detection_id}",
                "vehicle_type": "car",
            }
            async with aio_session.post(
                f"{self.API_BASE_URL}/vehicle-detection", json=detection_data
            ) as response:
                assert response.status == 200
                return await response.json()

        # Log 20 detections rapidly
        tasks = [log_detection(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all detections were logged
        assert len(results) == 20
        for result in results:
            assert result["status"] == "success"
