"""
Test configuration and fixtures for FlexTraff API tests
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.services.database_service import DatabaseService
from app.services.traffic_calculator import TrafficCalculator
from main import app, get_db_service, get_traffic_calculator

# Test configuration
TEST_BASE_URL = "http://127.0.0.1:8001"
API_TIMEOUT = 30

# Removed deprecated event_loop fixture - using pytest-asyncio defaults


@pytest.fixture
def mock_db_service():
    """Mock database service for unit testing"""
    mock_db = MagicMock()

    # Mock health check (async)
    mock_db.health_check = AsyncMock(return_value={
        "database_connected": True,
        "status": "healthy",
    })

    # Mock junction data (async)
    mock_db.get_all_junctions = AsyncMock(return_value=[
        {
            "id": 1,
            "junction_name": "Test Junction 1",
            "location": "Test Location 1",
            "status": "active",
        },
        {
            "id": 2,
            "junction_name": "Test Junction 2",
            "location": "Test Location 2",
            "status": "active",
        },
    ])

    # Mock vehicle detection logging (async)
    mock_db.log_vehicle_detection = AsyncMock(return_value={"id": 1, "status": "logged"})

    # Mock traffic cycle logging (async)
    mock_db.log_traffic_cycle = AsyncMock(return_value={"id": 1, "status": "logged"})

    # Mock lane counts (async)
    mock_db.get_current_lane_counts = AsyncMock(return_value=[
        {"lane": "North", "lane_number": 1, "count": 10},
        {"lane": "South", "lane_number": 2, "count": 8},
        {"lane": "East", "lane_number": 3, "count": 12},
        {"lane": "West", "lane_number": 4, "count": 6},
    ])

    # Mock current traffic cycle (async)
    mock_db.get_current_traffic_cycle = AsyncMock(return_value={
        "id": 1,
        "total_cycle_time": 120,
        "total_vehicles_detected": 36,
        "cycle_start_time": "2025-09-15T12:00:00",
    })

    # Mock vehicles count by date (async)
    mock_db.get_vehicles_count_by_date = AsyncMock(return_value=150)

    # Mock recent detections (async)
    mock_db.get_recent_detections_with_signals = AsyncMock(return_value=[
        {
            "id": 1,
            "fastag_id": "TEST123",
            "lane_number": 1,
            "vehicle_type": "car",
            "detection_timestamp": "2025-09-15T12:00:00",
        }
    ])

    # Mock log_system_event (async)
    mock_db.log_system_event = AsyncMock(return_value=None)

    return mock_db


@pytest.fixture
def mock_traffic_calculator(mock_db_service):
    """Mock traffic calculator for unit testing"""
    mock_calculator = MagicMock()

    # Mock calculate_green_times method (async)
    mock_calculator.calculate_green_times = AsyncMock(return_value=([30, 25, 35, 20], 110))

    # Mock get_algorithm_info method (sync)
    mock_calculator.get_algorithm_info.return_value = {
        "algorithm": "ATCS",
        "version": "1.0",
        "execution_time_ms": 15,
        "optimization_level": "high",
    }

    # Set the db_service attribute to the mocked database service
    mock_calculator.db_service = mock_db_service

    return mock_calculator


@pytest.fixture
def test_client(
    mock_db_service,
    mock_traffic_calculator,
) -> Generator[TestClient, None, None]:

    """Create FastAPI test client with mocked dependencies"""
    # Override dependencies
    app.dependency_overrides[get_db_service] = lambda: mock_db_service
    app.dependency_overrides[get_traffic_calculator] = lambda: mock_traffic_calculator

    client = TestClient(app)

    yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def aio_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Create aiohttp session for testing live API"""
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
    ) as session:
        yield session


# Test data samples
class TestData:
    """Test data constants and samples"""

    # Valid lane counts for different scenarios
    RUSH_HOUR_LANES = [45, 38, 52, 41]
    NORMAL_TRAFFIC_LANES = [25, 22, 28, 24]
    LIGHT_TRAFFIC_LANES = [8, 12, 6, 10]
    UNEVEN_TRAFFIC_LANES = [60, 15, 18, 12]
    ZERO_TRAFFIC_LANES = [0, 0, 0, 0]
    SINGLE_LANE_TRAFFIC = [50, 0, 0, 0]

    # Invalid lane counts
    INVALID_LANE_COUNTS = [
        [],  # Empty
        [10, 20],  # Too few lanes
        [10, 20, 30, 40, 50],  # Too many lanes
        [-5, 10, 20, 30],  # Negative values
        [10, 20, 30, "invalid"],  # Invalid type
    ]

    # Valid junction IDs
    VALID_JUNCTION_IDS = [1, 2, 3]

    # Invalid junction IDs
    INVALID_JUNCTION_IDS = [-1, 0, 999, "invalid", None]

    # Vehicle detection samples
    VALID_VEHICLE_DETECTIONS = [
        {
            "junction_id": 1,
            "lane_number": 1,
            "fastag_id": "TEST123456789",
            "vehicle_type": "car",
        },
        {
            "junction_id": 2,
            "lane_number": 2,
            "fastag_id": "TRUCK987654321",
            "vehicle_type": "truck",
        },
        {
            "junction_id": 1,
            "lane_number": 3,
            "fastag_id": "BIKE111222333",
            "vehicle_type": "bike",
        },
    ]

    # Invalid vehicle detections
    INVALID_VEHICLE_DETECTIONS = [
        {
            "junction_id": -1,  # Invalid junction
            "lane_number": 1,
            "fastag_id": "TEST123",
            "vehicle_type": "car",
        },
        {
            "junction_id": 1,
            "lane_number": 5,  # Invalid lane (>4)
            "fastag_id": "TEST123",
            "vehicle_type": "car",
        },
        {
            "junction_id": 1,
            "lane_number": 1,
            "fastag_id": "",  # Empty fastag
            "vehicle_type": "car",
        },
    ]

    # Expected response structures
    TRAFFIC_CALCULATION_RESPONSE_SCHEMA = {
        "green_times": list,
        "cycle_time": int,
        "algorithm_info": dict,
    }

    HEALTH_RESPONSE_SCHEMA = {
        "status": str,
        "database_connected": bool,
        "algorithm_version": str,
        "uptime": str,
    }

    JUNCTION_STATUS_RESPONSE_SCHEMA = {
        "junction_id": int,
        "junction_name": str,
        "current_lane_counts": list,
        "total_vehicles_today": int,
    }


# Utility functions for tests
def assert_response_schema(response_data: dict, expected_schema: dict):
    """Assert that response data matches expected schema"""
    for key, expected_type in expected_schema.items():
        assert key in response_data, f"Missing key: {key}"
        assert isinstance(
            response_data[key], expected_type
        ), f"Wrong type for {key}: expected {expected_type}, got {type(response_data[key])}"


def assert_valid_green_times(green_times: list):
    """Assert that green times are valid"""
    assert len(green_times) == 4, "Should have 4 green times"
    assert all(
        isinstance(t, int) and t >= 15 for t in green_times
    ), "All green times should be integers >= 15"
    assert sum(green_times) <= 180, "Total green time should not exceed 180s"


def assert_valid_cycle_time(cycle_time: int):
    """Assert that cycle time is valid"""
    assert isinstance(cycle_time, int), "Cycle time should be an integer"
    assert (
        60 <= cycle_time <= 180
    ), f"Cycle time should be between 60-180s, got {cycle_time}"
