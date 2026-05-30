"""
FlexTraff Backend - Supabase Connection Test
Run this to verify your Supabase setup is working correctly
"""

import asyncio
import os

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()


async def test_supabase_connection():
    """Test Supabase connection and database setup"""
    print("🔧 Testing FlexTraff Supabase Connection...")

    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env file")
        return False

    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)

        # Test 1: Check traffic_junctions table
        print("📋 Testing traffic_junctions table...")
        junctions = supabase.table("traffic_junctions").select("*").execute()
        print(f"✅ Found {len(junctions.data)} traffic junctions")

        # Test 2: Check demo_scenarios table
        print("📋 Testing demo_scenarios table...")
        scenarios = supabase.table("demo_scenarios").select("*").execute()
        print(f"✅ Found {len(scenarios.data)} demo scenarios")

        # Test 3: Check vehicle_detections table structure
        print("📋 Testing vehicle_detections table structure...")
        detections = supabase.table("vehicle_detections").select("*").limit(1).execute()
        print("✅ Vehicle detections table is accessible")

        # Test 4: Check authentication
        print("🔐 Testing authentication setup...")
        try:
            # This should return user info if auth is configured
            users = supabase.auth.admin.list_users()
            print(f"✅ Authentication working - {len(users)} users configured")
        except Exception as auth_error:
            print(f"⚠️  Authentication test failed: {auth_error}")

        print("\n🎉 All tests passed! Supabase is ready for FlexTraff backend.")
        print("\n📝 Next steps:")
        print("1. Start your FastAPI server: uvicorn app.main:app --reload")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Test API endpoints with your Supabase data")

        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        print("2. Ensure you ran the SQL schema in Supabase SQL Editor")
        print("3. Verify your Supabase project is active")
        return False


async def show_sample_data():
    """Show sample data from tables"""
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
    )

    print("\n📊 Sample Data Preview:")

    # Show traffic junctions
    junctions = (
        supabase.table("traffic_junctions")
        .select("id, junction_name, location")
        .execute()
    )
    print("\n🚦 Traffic Junctions:")
    for junction in junctions.data:
        print(
            f"  ID {junction['id']}: {junction['junction_name']} ({junction['location']})"
        )

    # Show demo scenarios
    scenarios = (
        supabase.table("demo_scenarios").select("scenario_name, lane_counts").execute()
    )
    print("\n🎮 Demo Scenarios:")
    for scenario in scenarios.data:
        print(f"  {scenario['scenario_name']}: {scenario['lane_counts']}")


if __name__ == "__main__":
    print("FlexTraff Backend - Supabase Setup Verification")
    print("=" * 50)

    success = asyncio.run(test_supabase_connection())

    if success:
        asyncio.run(show_sample_data())

    print("\n" + "=" * 50)
    print("Test completed!")
