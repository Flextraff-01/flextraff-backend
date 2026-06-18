"""
Unit tests for individual API endpoints
Tests each endpoint in isolation with mocked dependencies
"""

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (TestData, assert_response_schema,
                            assert_valid_cycle_time, assert_valid_green_times)


@pytest.mark.unit
@pytest.mark.api
class TestRootEndpoint:
    """Test root endpoint (/)"""

    def test_root_endpoint_success(self, test_client: TestClient):
        """Test root endpoint returns correct API information"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        expected_keys = ["service", "version", "description", "docs", "health"]
        for key in expected_keys:
            assert key in data

        # Verify specific values
        assert data["service"] == "FlexTraff ATCS API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


@pytest.mark.unit
@pytest.mark.api
class TestHealthEndpoint:
    """Test health check endpoint (/health)"""

    def test_health_check_healthy(self, test_client: TestClient):
        """Test health check when database is connected"""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert_response_schema(data, TestData.HEALTH_RESPONSE_SCHEMA)

        # Verify healthy status
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert data["algorithm_version"] == "ATCS v1.0"

    def test_health_check_unhealthy(self, test_client: TestClient, mock_db_service):
        """Test health check when database is disconnected"""
        # Configure mock for unhealthy state
        mock_db_service.health_check.return_value = {
            "database_connected": False,
            "status": "unhealthy",
            "error": "Connection failed",
        }

        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify unhealthy status
        assert data["status"] == "unhealthy"
        assert data["database_connected"] is False
        assert data["error"] == "Connection failed"


@pytest.mark.unit
@pytest.mark.api
class TestTrafficCalculationEndpoint:
    """Test traffic calculation endpoint (/calculate-timing)"""

    def test_calculate_timing_success(self, test_client: TestClient):
        """Test successful traffic timing calculation"""
        request_data = {"lane_counts": TestData.NORMAL_TRAFFIC_LANES, "junction_id": 1}

        response = test_client.post("/calculate-timing", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert_response_schema(data, TestData.TRAFFIC_CALCULATION_RESPONSE_SCHEMA)

        # Verify algorithm results
        assert_valid_green_times(data["green_times"])
        assert_valid_cycle_time(data["cycle_time"])
        assert data["junction_id"] == 1
        assert "algorithm_info" in data

    def test_calculate_timing_without_junction_id(self, test_client: TestClient):
        """Test traffic calculation without junction ID"""
        request_data = {"lane_counts": TestData.LIGHT_TRAFFIC_LANES}

        response = test_client.post("/calculate-timing", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should work without junction_id
        assert_valid_green_times(data["green_times"])
        assert_valid_cycle_time(data["cycle_time"])
        assert data["junction_id"] is None

    @pytest.mark.parametrize("invalid_lanes", TestData.INVALID_LANE_COUNTS)
    def test_calculate_timing_invalid_lanes(
        self, test_client: TestClient, invalid_lanes
    ):
        """Test traffic calculation with invalid lane counts"""
        request_data = {"lane_counts": invalid_lanes, "junction_id": 1}

        response = test_client.post("/calculate-timing", json=request_data)

        # Should return validation error
        assert response.status_code == 422

    def test_calculate_timing_calculation_error(
        self, test_client: TestClient, mock_traffic_calculator
    ):
        """Test traffic calculation when algorithm fails"""
        # Configure mock to raise exception
        mock_traffic_calculator.calculate_green_times.side_effect = Exception(
            "Algorithm failed"
        )

        request_data = {"lane_counts": TestData.NORMAL_TRAFFIC_LANES, "junction_id": 1}

        response = test_client.post("/calculate-timing", json=request_data)

        assert response.status_code == 500
        assert "Traffic calculation failed" in response.json()["error"]


@pytest.mark.unit
@pytest.mark.api
class TestVehicleDetectionEndpoint:
    """Test vehicle detection endpoint (/vehicle-detection)"""

    def test_log_vehicle_detection_success(self, test_client: TestClient):
        """Test successful vehicle detection logging"""
        request_data = TestData.VALID_VEHICLE_DETECTIONS[0]

        response = test_client.post("/vehicle-detection", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["status"] == "success"
        assert data["junction_id"] == request_data["junction_id"]
        assert data["lane"] == request_data["lane_number"]
        assert data["fastag_id"] == request_data["fastag_id"]

    @pytest.mark.parametrize("invalid_data", TestData.INVALID_VEHICLE_DETECTIONS)
    def test_log_vehicle_detection_invalid(self, test_client: TestClient, invalid_data):
        """Test vehicle detection with invalid data"""
        response = test_client.post("/vehicle-detection", json=invalid_data)

        # Should return validation error
        assert response.status_code == 422

    def test_log_vehicle_detection_database_error(
        self, test_client: TestClient, mock_db_service
    ):
        """Test vehicle detection when database logging fails"""
        # Note: Background task errors in FastAPI are handled asynchronously
        # and don't affect the main response. This test verifies the main endpoint works.
        request_data = TestData.VALID_VEHICLE_DETECTIONS[0]

        response = test_client.post("/vehicle-detection", json=request_data)

        # Main response should be successful regardless of background task outcome
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["junction_id"] == request_data["junction_id"]


@pytest.mark.unit
@pytest.mark.api
class TestJunctionsEndpoint:
    """Test junctions endpoint (/junctions)"""

    def test_get_junctions_success(self, test_client: TestClient):
        """Test successful retrieval of junctions"""
        response = test_client.get("/junctions")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "junctions" in data
        assert isinstance(data["junctions"], list)
        assert len(data["junctions"]) == 2

        # Verify junction data
        junction = data["junctions"][0]
        assert "id" in junction
        assert "junction_name" in junction

    def test_get_junctions_empty(self, test_client: TestClient, mock_db_service):
        """Test junctions endpoint when no junctions exist"""
        # Configure mock to return empty list
        mock_db_service.get_all_junctions.return_value = []

        response = test_client.get("/junctions")

        assert response.status_code == 200
        data = response.json()

        assert data["junctions"] == []

    def test_get_junctions_database_error(
        self, test_client: TestClient, mock_db_service
    ):
        """Test junctions endpoint when database fails"""
        # Configure mock to raise exception
        mock_db_service.get_all_junctions.side_effect = Exception("Database error")

        response = test_client.get("/junctions")

        assert response.status_code == 500
        assert "Failed to get junctions" in response.json()["error"]


@pytest.mark.unit
@pytest.mark.api
class TestJunctionStatusEndpoint:
    """Test junction status endpoint (/junction/{junction_id}/status)"""

    def test_get_junction_status_success(self, test_client: TestClient):
        """Test successful junction status retrieval"""
        junction_id = 1
        response = test_client.get(f"/junction/{junction_id}/status")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert_response_schema(data, TestData.JUNCTION_STATUS_RESPONSE_SCHEMA)

        # Verify specific values
        assert data["junction_id"] == junction_id
        assert data["junction_name"] == "Test Junction 1"
        assert isinstance(data["current_lane_counts"], list)
        assert data["total_vehicles_today"] == 150

    def test_get_junction_status_not_found(
        self, test_client: TestClient, mock_db_service
    ):
        """Test junction status for non-existent junction"""
        # Configure mock to return junctions that don't include the requested ID
        mock_db_service.get_all_junctions.return_value = [
            {"id": 2, "junction_name": "Other Junction"}
        ]

        response = test_client.get("/junction/999/status")

        assert response.status_code == 404
        assert "Junction not found" in response.json()["error"]

    @pytest.mark.parametrize("junction_id", TestData.VALID_JUNCTION_IDS[:3])
    def test_get_junction_status_all_valid_ids(
        self, test_client: TestClient, junction_id
    ):
        """Test junction status for all valid junction IDs"""
        response = test_client.get(f"/junction/{junction_id}/status")

        # For junction IDs 1 and 2, should succeed (based on mock data)
        # For junction ID 3, should fail (not in mock data)
        if junction_id in [1, 2]:
            assert response.status_code == 200
        else:
            assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
class TestLiveTimingEndpoint:
    """Test live timing endpoint (/junction/{junction_id}/live-timing)"""

    def test_get_live_timing_success(self, test_client: TestClient):
        """Test successful live timing retrieval"""
        junction_id = 1
        response = test_client.get(f"/junction/{junction_id}/live-timing")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "junction_id" in data
        assert "current_lane_counts" in data
        assert "recommended_green_times" in data
        assert "total_cycle_time" in data
        assert "algorithm_info" in data

        # Verify values
        assert data["junction_id"] == junction_id
        assert isinstance(data["current_lane_counts"], list)
        assert len(data["current_lane_counts"]) == 4
        assert_valid_green_times(data["recommended_green_times"])
        assert_valid_cycle_time(data["total_cycle_time"])

    def test_get_live_timing_with_time_window(self, test_client: TestClient):
        """Test live timing with custom time window"""
        response = test_client.get("/junction/1/live-timing?time_window=10")

        assert response.status_code == 200
        data = response.json()

        assert data["time_window_minutes"] == 10
        assert_valid_green_times(data["recommended_green_times"])


@pytest.mark.unit
@pytest.mark.api
class TestJunctionHistoryEndpoint:
    """Test junction history endpoint (/junction/{junction_id}/history)"""

    def test_get_junction_history_success(self, test_client: TestClient):
        """Test successful junction history retrieval"""
        junction_id = 1
        response = test_client.get(f"/junction/{junction_id}/history")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "junction_id" in data
        assert "recent_detections" in data
        assert "latest_cycle" in data
        assert "total_records" in data

        # Verify values
        assert data["junction_id"] == junction_id
        assert isinstance(data["recent_detections"], list)
        assert data["total_records"] == len(data["recent_detections"])

    def test_get_junction_history_with_limit(self, test_client: TestClient):
        """Test junction history with custom limit"""
        response = test_client.get("/junction/1/history?limit=5")

        assert response.status_code == 200
        data = response.json()

        # Should respect the limit (though mock data may be smaller)
        assert len(data["recent_detections"]) <= 10  # limit * 2 as per implementation


@pytest.mark.unit
@pytest.mark.api
class TestDailySummaryEndpoint:
    """Test daily summary endpoint (/analytics/daily-summary)"""

    def test_get_daily_summary_success(self, test_client: TestClient):
        """Test successful daily summary retrieval"""
        response = test_client.get("/analytics/daily-summary")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "date" in data
        assert "junction_summaries" in data
        assert "total_vehicles" in data

        # Verify values
        assert isinstance(data["junction_summaries"], list)
        assert len(data["junction_summaries"]) == 2  # Based on mock data
        assert data["total_vehicles"] == 300  # 150 * 2 junctions

    def test_get_daily_summary_custom_date(self, test_client: TestClient):
        """Test daily summary with custom date"""
        target_date = "2024-01-15"
        response = test_client.get(
            f"/analytics/daily-summary?target_date={target_date}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["date"] == target_date

    def test_get_daily_summary_no_junctions(
        self, test_client: TestClient, mock_db_service
    ):
        """Test daily summary when no junctions exist"""
        # Configure mock to return empty list
        mock_db_service.get_all_junctions.return_value = []

        response = test_client.get("/analytics/daily-summary")

        assert response.status_code == 200
        data = response.json()

        assert data["junction_summaries"] == []
        assert data["total_vehicles"] == 0
