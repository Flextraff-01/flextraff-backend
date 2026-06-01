#!/usr/bin/env python3
"""
Simple test for API functionality
"""

import json

import requests


def test_basic_api():
    """Test basic API functionality"""
    base_url = "http://127.0.0.1:8001"

    try:
        print("🧪 Testing FlexTraff API...")

        # Test root endpoint
        print("1. Testing root endpoint...")
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {data['service']} v{data['version']}")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            return False

        # Test health check
        print("2. Testing health check...")
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data['status']}, DB: {data['database_connected']}")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            return False

        # Test traffic calculation
        print("3. Testing traffic calculation...")
        calculation_data = {"lane_counts": [45, 38, 52, 41], "junction_id": 3}

        response = requests.post(f"{base_url}/calculate-timing", json=calculation_data)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Green times: {data['green_times']}")
            print(f"   ✅ Cycle time: {data['cycle_time']}s")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            return False

        print("\n🎉 Basic API tests passed!")
        return True

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on port 8001.")
        return False
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_basic_api()
