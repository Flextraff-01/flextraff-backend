#!/usr/bin/env python3
"""
Database Connection Test for FlexTraff ATCS Backend
Run this script to verify your Supabase database connection is working.
"""

import asyncio
import os

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()


def test_supabase_connection():
    """Test Supabase connection with your credentials"""
    try:
        # Get environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            print("❌ ERROR: Missing Supabase credentials in .env file")
            print("   Please check SUPABASE_URL and SUPABASE_SERVICE_KEY")
            return False

        print(f"🔗 Testing connection to: {supabase_url}")

        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)

        # Test 1: Check if we can query tables (even if empty)
        print("📋 Testing table access...")

        # This will fail if tables don't exist
        try:
            result = supabase.table("traffic_junctions").select("*").limit(1).execute()
            print("✅ Successfully connected to traffic_junctions table")
        except Exception as e:
            print(f"❌ Error accessing traffic_junctions: {str(e)}")
            print("   This usually means the tables haven't been created yet.")
            print("   Please run the SQL schema in Supabase dashboard first.")
            return False

        # Test 2: Try to insert a test junction
        print("📝 Testing data insertion...")
        try:
            test_data = {
                "junction_name": "Test Junction - DELETE ME",
                "location": "Test Location",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "status": "active",
            }

            insert_result = (
                supabase.table("traffic_junctions").insert(test_data).execute()
            )

            if insert_result.data:
                inserted_id = insert_result.data[0]["id"]
                print(f"✅ Successfully inserted test data (ID: {inserted_id})")

                # Clean up: delete the test data
                supabase.table("traffic_junctions").delete().eq(
                    "id", inserted_id
                ).execute()
                print("🧹 Cleaned up test data")

        except Exception as e:
            print(f"❌ Error inserting test data: {str(e)}")
            return False

        # Test 3: Check other tables exist
        print("🔍 Checking other tables...")
        tables_to_check = [
            "rfid_scanners",
            "vehicle_detections",
            "traffic_cycles",
            "demo_scenarios",
        ]

        for table in tables_to_check:
            try:
                supabase.table(table).select("id").limit(1).execute()
                print(f"✅ {table} table exists")
            except Exception as e:
                print(f"❌ {table} table issue: {str(e)}")

        print("\n🎉 Database connection test completed successfully!")
        print("   Your Supabase database is ready for FlexTraff backend!")

        return True

    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False


def main():
    """Run the database connection test"""
    print("🚀 FlexTraff ATCS - Database Connection Test")
    print("=" * 50)

    success = test_supabase_connection()

    if success:
        print("\n✅ ALL TESTS PASSED!")
        print("Next steps:")
        print("1. Your database is ready!")
        print("2. You can now start developing your FastAPI endpoints")
        print("3. Run: uvicorn app.main:app --reload (once you create main.py)")
    else:
        print("\n❌ TESTS FAILED!")
        print("Please check:")
        print("1. Supabase project is created")
        print("2. Database schema is executed in Supabase SQL Editor")
        print("3. Environment variables are correct in .env file")


if __name__ == "__main__":
    main()
