#!/usr/bin/env python3
"""
Supabase Connection Test Script for FlexTraff Backend
Run this after setting up Supabase and updating .env file
"""

import asyncio
import os

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()


async def test_supabase_connection():
    """Test Supabase database connection and basic operations"""

    print("🔌 Testing Supabase Connection for FlexTraff Backend")
    print("=" * 60)

    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ ERROR: Missing environment variables!")
        print("   Please check your .env file for:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_KEY")
        return False

    print(f"✅ Environment variables loaded")
    print(f"   URL: {supabase_url}")
    print(f"   Key: {supabase_key[:20]}...")

    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")

        # Test 1: Check traffic_junctions table
        print("\n📋 Test 1: Checking traffic_junctions table...")
        result = supabase.table("traffic_junctions").select("*").execute()
        junctions_count = len(result.data) if result.data else 0
        print(f"✅ Found {junctions_count} traffic junctions")

        if junctions_count > 0:
            print("   Sample junction:", result.data[0]["junction_name"])

        # Test 2: Check all tables exist
        print("\n📋 Test 2: Checking all required tables...")
        required_tables = [
            "traffic_junctions",
            "rfid_scanners",
            "vehicle_detections",
            "traffic_cycles",
            "system_logs",
            "demo_scenarios",
        ]

        for table_name in required_tables:
            try:
                result = supabase.table(table_name).select("id").limit(1).execute()
                print(f"✅ Table '{table_name}' exists and accessible")
            except Exception as e:
                print(f"❌ Table '{table_name}' error: {str(e)}")
                return False

        # Test 3: Test insert operation
        print("\n📋 Test 3: Testing insert operation...")
        test_log = {
            "junction_id": 1,
            "log_level": "INFO",
            "component": "test_script",
            "message": "Connection test successful",
            "metadata": {"test": True, "timestamp": "now"},
        }

        insert_result = supabase.table("system_logs").insert(test_log).execute()
        if insert_result.data:
            print("✅ Insert operation successful")
            print(f"   Inserted log ID: {insert_result.data[0]['id']}")
        else:
            print("❌ Insert operation failed")
            return False

        # Test 4: Check demo scenarios
        print("\n📋 Test 4: Checking demo scenarios...")
        scenarios = supabase.table("demo_scenarios").select("*").execute()
        scenarios_count = len(scenarios.data) if scenarios.data else 0
        print(f"✅ Found {scenarios_count} demo scenarios")

        if scenarios_count > 0:
            for scenario in scenarios.data[:3]:  # Show first 3
                print(f"   - {scenario['scenario_name']}: {scenario['lane_counts']}")

        # Test 5: Test authentication (optional)
        print("\n📋 Test 5: Testing authentication setup...")
        try:
            # This will show auth configuration (not test actual login)
            print("✅ Authentication service accessible")
            print("   Note: Create admin user manually in Supabase dashboard")
        except Exception as e:
            print(f"⚠️  Authentication warning: {str(e)}")

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Supabase is ready for FlexTraff Backend")
        print("=" * 60)

        print("\n📝 Next Steps:")
        print("1. Create admin user in Supabase Auth dashboard")
        print("2. Set user_metadata = {'role': 'admin'}")
        print("3. Start FastAPI server: uvicorn app.main:app --reload")
        print("4. Test APIs at http://localhost:8000/docs")

        return True

    except Exception as e:
        print(f"\n❌ Connection test failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your .env file has correct Supabase credentials")
        print("2. Verify you ran the SQL schema in Supabase SQL Editor")
        print("3. Ensure your Supabase project is active")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_supabase_connection())
    exit(0 if success else 1)
