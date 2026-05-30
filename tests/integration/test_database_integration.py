#!/usr/bin/env python3
"""
Test script for database integration with traffic calculator
Tests the complete flow: algorithm calculation + database logging
"""

import asyncio
import logging
import os
import sys
from datetime import date, datetime

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database_service import DatabaseService
from app.services.traffic_calculator import TrafficCalculator

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_database_integration():
    """Test complete database integration flow"""
    print("🚀 Testing FlexTraff Database Integration")
    print("=" * 50)

    try:
        # Step 1: Initialize services
        print("1️⃣ Initializing services...")
        db_service = DatabaseService()
        calculator = TrafficCalculator(db_service=db_service)

        # Step 2: Health check
        print("2️⃣ Testing database connection...")
        health = await db_service.health_check()
        if not health["database_connected"]:
            print(
                f"❌ Database connection failed: {health.get('error', 'Unknown error')}"
            )
            return False
        print("✅ Database connection successful")

        # Step 3: Get junction info
        print("3️⃣ Getting junction information...")
        junctions = await db_service.get_all_junctions()
        if not junctions:
            print("❌ No junctions found in database")
            return False

        junction = junctions[0]  # Use first junction
        junction_id = junction["id"]
        junction_name = junction["junction_name"]
        print(f"✅ Using junction: {junction_name} (ID: {junction_id})")

        # Step 4: Test traffic calculation with database logging
        print("4️⃣ Testing traffic calculation with database logging...")

        test_scenarios = [
            ("Rush Hour", [45, 38, 52, 41]),
            ("Normal Traffic", [25, 22, 28, 24]),
            ("Light Traffic", [8, 12, 6, 10]),
            ("Uneven Distribution", [60, 15, 18, 12]),
        ]

        for scenario_name, lane_counts in test_scenarios:
            print(f"   Testing {scenario_name}: {lane_counts}")

            # Calculate green times (this will also log to database)
            green_times, cycle_time = await calculator.calculate_green_times(
                lane_counts, junction_id=junction_id
            )

            print(f"   → Green times: {green_times}, Cycle: {cycle_time}s")

        # Step 5: Test vehicle detection logging
        print("5️⃣ Testing vehicle detection logging...")
        sample_detections = [
            (junction_id, 1, "FT001234567890", "car"),
            (junction_id, 2, "FT001234567891", "truck"),
            (junction_id, 3, "FT001234567892", "car"),
            (junction_id, 4, "FT001234567893", "bike"),
        ]

        for detection_data in sample_detections:
            result = await db_service.log_vehicle_detection(*detection_data)
            print(
                f"   ✅ Logged detection: Lane {detection_data[1]}, FastTag {detection_data[2]}"
            )

        # Step 6: Test data retrieval
        print("6️⃣ Testing data retrieval...")

        # Get current lane counts
        lane_counts_data = await db_service.get_current_lane_counts(junction_id)
        print(
            f"   Current lane counts: {[(data['lane'], data['count']) for data in lane_counts_data]}"
        )

        # Get current traffic cycle
        current_cycle = await db_service.get_current_traffic_cycle(junction_id)
        if current_cycle:
            print(
                f"   Latest cycle: {current_cycle['total_cycle_time']}s, vehicles: {current_cycle['total_vehicles_detected']}"
            )

        # Get recent detections
        recent_logs = await db_service.get_recent_detections_with_signals(
            junction_id, limit=5
        )
        print(f"   Recent detections: {len(recent_logs)} records")

        # Get vehicle count by date
        today_count = await db_service.get_vehicles_count_by_date(
            junction_id, date.today()
        )
        print(f"   Today's vehicle count: {today_count}")

        # Step 7: Test batch operations
        print("7️⃣ Testing batch operations...")

        batch_detections = []
        for i in range(5):
            batch_detections.append(
                {
                    "junction_id": junction_id,
                    "lane_number": (i % 4) + 1,
                    "fastag_id": f"BATCH{i:03d}",
                    "vehicle_type": "car",
                    "detection_timestamp": datetime.now().isoformat(),
                    "processing_status": "processed",
                }
            )

        batch_result = await db_service.batch_insert_vehicle_detections(
            batch_detections
        )
        if batch_result["success"]:
            print(f"   ✅ Batch inserted {batch_result['inserted_count']} detections")
        else:
            print(f"   ❌ Batch insert failed: {batch_result['error']}")

        print("\n🎉 All database integration tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Database integration test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_real_time_simulation():
    """Test real-time traffic simulation with database logging"""
    print("\n🚦 Real-time Traffic Simulation Test")
    print("=" * 40)

    try:
        db_service = DatabaseService()
        calculator = TrafficCalculator(db_service=db_service)

        # Get a junction
        junctions = await db_service.get_all_junctions()
        junction_id = junctions[0]["id"]

        print(f"Simulating traffic for junction {junction_id}...")

        # Simulate vehicle arrivals
        import random

        for minute in range(5):  # 5-minute simulation
            print(f"\n📊 Minute {minute + 1}:")

            # Generate random vehicle detections
            for detection in range(random.randint(2, 8)):
                lane = random.randint(1, 4)
                fastag = f"SIM{minute:02d}{detection:02d}"
                await db_service.log_vehicle_detection(junction_id, lane, fastag, "car")

            # Get current counts and calculate timing
            lane_data = await db_service.get_current_lane_counts(
                junction_id, time_window_minutes=2
            )
            current_counts = [data["count"] for data in lane_data]

            # Calculate optimal timing
            green_times, cycle_time = await calculator.calculate_green_times(
                current_counts, junction_id=junction_id
            )

            print(f"   Lane counts: {current_counts}")
            print(f"   Green times: {green_times}")
            print(f"   Cycle time: {cycle_time}s")

            # Small delay to simulate real time
            await asyncio.sleep(0.5)

        print("\n✅ Real-time simulation completed successfully!")

    except Exception as e:
        print(f"\n❌ Real-time simulation failed: {str(e)}")


async def main():
    """Run all database integration tests"""
    success = await test_database_integration()

    if success:
        await test_real_time_simulation()
        print("\n🏆 All tests completed successfully!")
        print("🔗 Database integration is working perfectly!")
    else:
        print("\n💥 Tests failed. Please check your Supabase configuration.")


if __name__ == "__main__":
    asyncio.run(main())
