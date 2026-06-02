"""
Performance and load tests for FlexTraff API
Tests system behavior under various load conditions
"""

import asyncio
import random
import statistics
import time
from typing import Any, Dict, List

import aiohttp
import pytest

from tests.conftest import TestData


@pytest.mark.skip(reason="Requires running API server - use for manual testing only")
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.api
class TestAPIPerformance:
    """Performance benchmarking tests"""

    API_BASE_URL = "http://127.0.0.1:8001"

    @pytest.mark.asyncio
    async def test_single_calculation_performance(
        self, aio_session: aiohttp.ClientSession
    ):
        """Test performance of single traffic calculation"""
        # Get a junction ID
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Measure calculation time
        request_data = {
            "lane_counts": TestData.RUSH_HOUR_LANES,
            "junction_id": junction_id,
        }

        start_time = time.time()
        async with aio_session.post(
            f"{self.API_BASE_URL}/calculate-timing", json=request_data
        ) as response:
            assert response.status == 200
            data = await response.json()
        end_time = time.time()

        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        # Assert reasonable response time (< 100ms for single calculation)
        assert response_time < 100, f"Response time too slow: {response_time:.2f}ms"

        print(f"Single calculation response time: {response_time:.2f}ms")

    @pytest.mark.asyncio
    async def test_calculation_consistency(self, aio_session: aiohttp.ClientSession):
        """Test that calculations are consistent for same inputs"""
        # Get a junction ID
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        request_data = {
            "lane_counts": TestData.RUSH_HOUR_LANES,
            "junction_id": junction_id,
        }

        # Make 10 identical requests
        results = []
        for _ in range(10):
            async with aio_session.post(
                f"{self.API_BASE_URL}/calculate-timing", json=request_data
            ) as response:
                assert response.status == 200
                data = await response.json()
                results.append(data)

        # Verify all results are identical
        first_result = results[0]
        for result in results[1:]:
            assert result["green_times"] == first_result["green_times"]
            assert result["cycle_time"] == first_result["cycle_time"]

        print(f"Calculation consistency verified across {len(results)} requests")

    @pytest.mark.asyncio
    async def test_response_time_distribution(self, aio_session: aiohttp.ClientSession):
        """Test response time distribution across multiple requests"""
        # Get a junction ID
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        response_times = []
        scenarios = [
            TestData.RUSH_HOUR_LANES,
            TestData.NORMAL_TRAFFIC_LANES,
            TestData.LIGHT_TRAFFIC_LANES,
            TestData.UNEVEN_TRAFFIC_LANES,
        ]

        # Measure 50 requests with different scenarios
        for i in range(50):
            scenario = scenarios[i % len(scenarios)]
            request_data = {"lane_counts": scenario, "junction_id": junction_id}

            start_time = time.time()
            async with aio_session.post(
                f"{self.API_BASE_URL}/calculate-timing", json=request_data
            ) as response:
                assert response.status == 200
            end_time = time.time()

            response_times.append((end_time - start_time) * 1000)

        # Calculate statistics
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
        max_time = max(response_times)

        print(f"Response time statistics (ms):")
        print(f"  Average: {avg_time:.2f}")
        print(f"  Median: {median_time:.2f}")
        print(f"  95th percentile: {p95_time:.2f}")
        print(f"  Maximum: {max_time:.2f}")

        # Assert performance benchmarks
        assert avg_time < 50, f"Average response time too high: {avg_time:.2f}ms"
        assert p95_time < 100, f"95th percentile too high: {p95_time:.2f}ms"


@pytest.mark.skip(reason="Requires running API server - use for manual testing only")
class TestAPILoadTesting:
    """Load testing for API endpoints"""

    API_BASE_URL = "http://127.0.0.1:8001"

    @pytest.mark.asyncio
    async def test_concurrent_calculations_load(
        self, aio_session: aiohttp.ClientSession
    ):
        """Test system behavior under concurrent calculation load"""
        # Get a junction ID
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        async def make_calculation_request(request_id: int):
            """Make a single calculation request"""
            scenarios = [
                TestData.RUSH_HOUR_LANES,
                TestData.NORMAL_TRAFFIC_LANES,
                TestData.LIGHT_TRAFFIC_LANES,
                TestData.UNEVEN_TRAFFIC_LANES,
            ]

            scenario = scenarios[request_id % len(scenarios)]
            request_data = {"lane_counts": scenario, "junction_id": junction_id}

            start_time = time.time()
            try:
                async with aio_session.post(
                    f"{self.API_BASE_URL}/calculate-timing", json=request_data
                ) as response:
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000

                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "response_time": response_time,
                            "status_code": response.status,
                            "request_id": request_id,
                        }
                    else:
                        return {
                            "success": False,
                            "response_time": response_time,
                            "status_code": response.status,
                            "request_id": request_id,
                        }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "response_time": (end_time - start_time) * 1000,
                    "error": str(e),
                    "request_id": request_id,
                }

        # Test with 50 concurrent requests
        concurrent_requests = 50
        tasks = [make_calculation_request(i) for i in range(concurrent_requests)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Analyze results
        successful_requests = [
            r for r in results if isinstance(r, dict) and r.get("success", False)
        ]
        failed_requests = [
            r for r in results if not isinstance(r, dict) or not r.get("success", False)
        ]

        success_rate = len(successful_requests) / concurrent_requests * 100
        avg_response_time = (
            statistics.mean([r["response_time"] for r in successful_requests])
            if successful_requests
            else 0
        )
        throughput = concurrent_requests / total_time

        print(f"Load test results ({concurrent_requests} concurrent requests):")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.1f} req/s")
        print(f"  Failed requests: {len(failed_requests)}")

        # Assert minimum performance requirements
        assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
        assert (
            avg_response_time < 200
        ), f"Average response time too high: {avg_response_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_sustained_load(self, aio_session: aiohttp.ClientSession):
        """Test system behavior under sustained load"""
        # Get a junction ID
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        async def sustained_request_worker():
            """Worker that makes continuous requests"""
            results = []
            scenarios = [
                TestData.RUSH_HOUR_LANES,
                TestData.NORMAL_TRAFFIC_LANES,
                TestData.LIGHT_TRAFFIC_LANES,
                TestData.UNEVEN_TRAFFIC_LANES,
            ]

            for i in range(20):  # 20 requests per worker
                scenario = scenarios[i % len(scenarios)]
                request_data = {"lane_counts": scenario, "junction_id": junction_id}

                start_time = time.time()
                try:
                    async with aio_session.post(
                        f"{self.API_BASE_URL}/calculate-timing", json=request_data
                    ) as response:
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000

                        results.append(
                            {
                                "success": response.status == 200,
                                "response_time": response_time,
                                "status_code": response.status,
                            }
                        )

                except Exception as e:
                    end_time = time.time()
                    results.append(
                        {
                            "success": False,
                            "response_time": (end_time - start_time) * 1000,
                            "error": str(e),
                        }
                    )

                # Small delay between requests
                await asyncio.sleep(0.1)

            return results

        # Run 5 workers concurrently for sustained load
        workers = 5
        start_time = time.time()
        worker_results = await asyncio.gather(
            *[sustained_request_worker() for _ in range(workers)]
        )
        total_time = time.time() - start_time

        # Flatten results
        all_results = []
        for worker_result in worker_results:
            all_results.extend(worker_result)

        # Analyze sustained load results
        successful_requests = [r for r in all_results if r["success"]]
        success_rate = len(successful_requests) / len(all_results) * 100
        avg_response_time = (
            statistics.mean([r["response_time"] for r in successful_requests])
            if successful_requests
            else 0
        )
        total_requests = len(all_results)
        throughput = total_requests / total_time

        print(
            f"Sustained load test results ({workers} workers, {total_requests} total requests):"
        )
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.1f} req/s")

        # Assert sustained performance
        assert (
            success_rate >= 98
        ), f"Sustained success rate too low: {success_rate:.1f}%"
        assert (
            avg_response_time < 150
        ), f"Sustained response time too high: {avg_response_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_mixed_workload(self, aio_session: aiohttp.ClientSession):
        """Test system with mixed API endpoint workload"""
        # Get a junction ID
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        async def mixed_request_worker(worker_id: int):
            """Worker that makes requests to different endpoints"""
            results = []

            for i in range(15):  # 15 requests per worker
                request_type = random.choice(
                    [
                        "calculation",
                        "vehicle_detection",
                        "status",
                        "live_timing",
                        "history",
                        "health",
                    ]
                )

                start_time = time.time()
                try:
                    if request_type == "calculation":
                        scenario = random.choice(
                            [
                                TestData.RUSH_HOUR_LANES,
                                TestData.NORMAL_TRAFFIC_LANES,
                                TestData.LIGHT_TRAFFIC_LANES,
                            ]
                        )
                        request_data = {
                            "lane_counts": scenario,
                            "junction_id": junction_id,
                        }
                        async with aio_session.post(
                            f"{self.API_BASE_URL}/calculate-timing", json=request_data
                        ) as response:
                            success = response.status == 200

                    elif request_type == "vehicle_detection":
                        detection_data = {
                            "junction_id": junction_id,
                            "lane_number": random.randint(1, 4),
                            "fastag_id": f"LOAD_TEST_{worker_id}_{i}",
                            "vehicle_type": "car",
                        }
                        async with aio_session.post(
                            f"{self.API_BASE_URL}/vehicle-detection",
                            json=detection_data,
                        ) as response:
                            success = response.status == 200

                    elif request_type == "status":
                        async with aio_session.get(
                            f"{self.API_BASE_URL}/junction/{junction_id}/status"
                        ) as response:
                            success = response.status == 200

                    elif request_type == "live_timing":
                        async with aio_session.get(
                            f"{self.API_BASE_URL}/junction/{junction_id}/live-timing"
                        ) as response:
                            success = response.status == 200

                    elif request_type == "history":
                        async with aio_session.get(
                            f"{self.API_BASE_URL}/junction/{junction_id}/history"
                        ) as response:
                            success = response.status == 200

                    elif request_type == "health":
                        async with aio_session.get(
                            f"{self.API_BASE_URL}/health"
                        ) as response:
                            success = response.status == 200

                    end_time = time.time()
                    results.append(
                        {
                            "request_type": request_type,
                            "success": success,
                            "response_time": (end_time - start_time) * 1000,
                        }
                    )

                except Exception as e:
                    end_time = time.time()
                    results.append(
                        {
                            "request_type": request_type,
                            "success": False,
                            "response_time": (end_time - start_time) * 1000,
                            "error": str(e),
                        }
                    )

                # Small delay between requests
                await asyncio.sleep(0.05)

            return results

        # Run mixed workload with 8 workers
        workers = 8
        start_time = time.time()
        worker_results = await asyncio.gather(
            *[mixed_request_worker(i) for i in range(workers)]
        )
        total_time = time.time() - start_time

        # Flatten and analyze results
        all_results = []
        for worker_result in worker_results:
            all_results.extend(worker_result)

        # Group by request type
        by_type = {}
        for result in all_results:
            req_type = result["request_type"]
            if req_type not in by_type:
                by_type[req_type] = []
            by_type[req_type].append(result)

        overall_success_rate = (
            len([r for r in all_results if r["success"]]) / len(all_results) * 100
        )

        print(
            f"Mixed workload test results ({workers} workers, {len(all_results)} total requests):"
        )
        print(f"  Overall success rate: {overall_success_rate:.1f}%")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Overall throughput: {len(all_results) / total_time:.1f} req/s")

        for req_type, results in by_type.items():
            successful = [r for r in results if r["success"]]
            success_rate = len(successful) / len(results) * 100
            avg_time = (
                statistics.mean([r["response_time"] for r in successful])
                if successful
                else 0
            )
            print(f"  {req_type}: {success_rate:.1f}% success, {avg_time:.2f}ms avg")

        # Assert mixed workload performance
        assert (
            overall_success_rate >= 95
        ), f"Overall success rate too low: {overall_success_rate:.1f}%"


@pytest.mark.skip(reason="Requires running API server - use for manual testing only")
class TestAPIStabilityTesting:
    """Stability and stress tests"""

    API_BASE_URL = "http://127.0.0.1:8001"

    @pytest.mark.asyncio
    async def test_edge_case_inputs(self, aio_session: aiohttp.ClientSession):
        """Test API with edge case inputs"""
        # Get a junction ID
        async with aio_session.get(f"{self.API_BASE_URL}/junctions") as response:
            junctions_data = await response.json()
            if not junctions_data["junctions"]:
                pytest.skip("No junctions available for testing")

            junction_id = junctions_data["junctions"][0]["id"]

        # Test edge cases
        edge_cases = [
            TestData.ZERO_TRAFFIC_LANES,  # All zeros
            TestData.SINGLE_LANE_TRAFFIC,  # Only one lane has traffic
            [1, 1, 1, 1],  # Minimum traffic
            [999, 999, 999, 999],  # Very high traffic
            [1, 999, 1, 999],  # Extreme imbalance
        ]

        success_count = 0
        for i, lane_counts in enumerate(edge_cases):
            request_data = {"lane_counts": lane_counts, "junction_id": junction_id}

            try:
                async with aio_session.post(
                    f"{self.API_BASE_URL}/calculate-timing", json=request_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Verify response is valid
                        assert len(data["green_times"]) == 4
                        assert isinstance(data["cycle_time"], int)
                        success_count += 1
                        print(
                            f"Edge case {i+1}: {lane_counts} -> {data['green_times']} ({data['cycle_time']}s)"
                        )

            except Exception as e:
                print(f"Edge case {i+1} failed: {lane_counts} -> {str(e)}")

        success_rate = success_count / len(edge_cases) * 100
        print(f"Edge case handling: {success_rate:.1f}% success rate")

        # Should handle most edge cases gracefully
        assert (
            success_rate >= 80
        ), f"Edge case success rate too low: {success_rate:.1f}%"
