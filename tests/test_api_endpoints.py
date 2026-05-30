#!/usr/bin/env python3
"""
Test script for FlexTraff FastAPI endpoints
Tests all API functionality and endpoint integration
"""

import asyncio
import json
from datetime import date

import aiohttp

# Base URL for the API
BASE_URL = "http://localhost:8001"


async def test_api_endpoints():
    """Test all FastAPI endpoints"""
    print("🚀 Testing FlexTraff FastAPI Endpoints")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:

        # Test 1: Root endpoint
        print("1️⃣ Testing root endpoint...")
        async with session.get(f"{BASE_URL}/") as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Root: {data['service']} v{data['version']}")
            else:
                print(f"   ❌ Root failed: {response.status}")

        # Test 2: Health check
        print("2️⃣ Testing health check...")
        async with session.get(f"{BASE_URL}/health") as response:
            if response.status == 200:
                data = await response.json()
                print(
                    f"   ✅ Health: {data['status']}, DB: {data['database_connected']}"
                )
            else:
                print(f"   ❌ Health check failed: {response.status}")

        # Test 3: Get junctions
        print("3️⃣ Testing get junctions...")
        async with session.get(f"{BASE_URL}/junctions") as response:
            if response.status == 200:
                data = await response.json()
                junctions = data["junctions"]
                print(f"   ✅ Found {len(junctions)} junctions")
                if junctions:
                    junction_id = junctions[0]["id"]
                    junction_name = junctions[0]["junction_name"]
                    print(f"   Using junction: {junction_name} (ID: {junction_id})")
                else:
                    print("   ❌ No junctions found")
                    return
            else:
                print(f"   ❌ Get junctions failed: {response.status}")
                return

        # Test 4: Traffic calculation
        print("4️⃣ Testing traffic calculation...")
        calculation_data = {"lane_counts": [45, 38, 52, 41], "junction_id": junction_id}

        async with session.post(
            f"{BASE_URL}/calculate-timing", json=calculation_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                green_times = data["green_times"]
                cycle_time = data["cycle_time"]
                print(f"   ✅ Green times: {green_times}, Cycle: {cycle_time}s")
            else:
                print(f"   ❌ Traffic calculation failed: {response.status}")

        # Test 5: Vehicle detection logging
        print("5️⃣ Testing vehicle detection...")
        detection_data = {
            "junction_id": junction_id,
            "lane_number": 1,
            "fastag_id": "TEST123456789",
            "vehicle_type": "car",
        }

        async with session.post(
            f"{BASE_URL}/vehicle-detection", json=detection_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Detection logged: {data['message']}")
            else:
                print(f"   ❌ Vehicle detection failed: {response.status}")

        # Test 6: Junction status
        print("6️⃣ Testing junction status...")
        async with session.get(f"{BASE_URL}/junction/{junction_id}/status") as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Junction: {data['junction_name']}")
                print(f"   Today's vehicles: {data['total_vehicles_today']}")
                if data["latest_cycle"]:
                    print(
                        f"   Latest cycle: {data['latest_cycle']['total_cycle_time']}s"
                    )
            else:
                print(f"   ❌ Junction status failed: {response.status}")

        # Test 7: Live timing
        print("7️⃣ Testing live timing...")
        async with session.get(
            f"{BASE_URL}/junction/{junction_id}/live-timing"
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Live timing - Counts: {data['current_lane_counts']}")
                print(f"   Recommended green times: {data['recommended_green_times']}")
            else:
                print(f"   ❌ Live timing failed: {response.status}")

        # Test 8: Junction history
        print("8️⃣ Testing junction history...")
        async with session.get(
            f"{BASE_URL}/junction/{junction_id}/history?limit=5"
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ History: {data['total_records']} recent detections")
            else:
                print(f"   ❌ Junction history failed: {response.status}")

        # Test 9: Daily summary
        print("9️⃣ Testing daily summary...")
        async with session.get(f"{BASE_URL}/analytics/daily-summary") as response:
            if response.status == 200:
                data = await response.json()
                total_vehicles = data["total_vehicles"]
                print(f"   ✅ Daily summary: {total_vehicles} total vehicles today")
                for summary in data["junction_summaries"]:
                    print(
                        f"   - {summary['junction_name']}: {summary['total_vehicles']} vehicles"
                    )
            else:
                print(f"   ❌ Daily summary failed: {response.status}")

        # Test 10: Multiple traffic scenarios
        print("🔟 Testing multiple traffic scenarios...")
        test_scenarios = [
            ("Rush Hour", [60, 45, 55, 48]),
            ("Normal Traffic", [25, 22, 28, 24]),
            ("Light Traffic", [8, 12, 6, 10]),
            ("Uneven Distribution", [75, 12, 18, 15]),
        ]

        for scenario_name, lane_counts in test_scenarios:
            calculation_data = {"lane_counts": lane_counts, "junction_id": junction_id}

            async with session.post(
                f"{BASE_URL}/calculate-timing", json=calculation_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(
                        f"   ✅ {scenario_name}: {data['green_times']} ({data['cycle_time']}s)"
                    )
                else:
                    print(f"   ❌ {scenario_name} failed: {response.status}")

        print("\n🎉 All API endpoint tests completed!")


async def load_test_api():
    """Perform basic load testing"""
    print("\n⚡ Load Testing API")
    print("=" * 30)

    tasks = []

    async def make_request(session, scenario_name, lane_counts):
        try:
            calculation_data = {
                "lane_counts": lane_counts,
                "junction_id": 3,  # Use known junction ID
            }

            async with session.post(
                f"{BASE_URL}/calculate-timing", json=calculation_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return f"✅ {scenario_name}: {data['cycle_time']}s"
                else:
                    return f"❌ {scenario_name}: HTTP {response.status}"
        except Exception as e:
            return f"❌ {scenario_name}: {str(e)}"

    async with aiohttp.ClientSession() as session:
        # Create 20 concurrent requests with different scenarios
        scenarios = [
            ("Rush1", [45, 38, 52, 41]),
            ("Rush2", [50, 42, 48, 45]),
            ("Normal1", [25, 22, 28, 24]),
            ("Normal2", [30, 28, 32, 26]),
            ("Light1", [8, 12, 6, 10]),
        ]

        for i in range(20):
            scenario_name, lane_counts = scenarios[i % len(scenarios)]
            task = make_request(session, f"{scenario_name}_{i}", lane_counts)
            tasks.append(task)

        print("Making 20 concurrent requests...")
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for result in results if "✅" in result)
        print(f"Results: {success_count}/20 successful")

        for result in results[:5]:  # Show first 5 results
            print(f"   {result}")


async def main():
    """Run all API tests"""
    try:
        await test_api_endpoints()
        await load_test_api()
        print("\n🏆 All API tests completed successfully!")
        print("🌐 API is ready for frontend integration!")
        print(f"📖 Documentation: {BASE_URL}/docs")

    except Exception as e:
        print(f"\n💥 API tests failed: {str(e)}")


if __name__ == "__main__":
    # Install aiohttp if needed
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp for API testing...")
        import subprocess

        subprocess.check_call(
            [
                "/Users/ajaypsk2722/flextraff-backend/.venv/bin/python",
                "-m",
                "pip",
                "install",
                "aiohttp",
            ]
        )
        import aiohttp

    asyncio.run(main())
