#!/usr/bin/env python3
"""
Test script for Eva Assistant name management API endpoints.

Tests:
- POST /user/name - Set user name
- GET /user/{user_id}/name - Get user name
- GET /user/{user_id}/display-name - Get display name
- GET /user/{user_id}/profile - Get full profile with names
"""

import asyncio
import httpx
import json
import sys
import os

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "api_test_user"


async def test_name_api():
    """Test the name management API endpoints."""
    print("🧪 Testing Eva Assistant Name Management API")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Set user name
        print("\n1️⃣ Setting user name via API")
        set_name_data = {
            "user_id": TEST_USER_ID,
            "first_name": "Alice",
            "last_name": "Smith",
            "display_name": "Alice Smith",
            "email": "alice.smith@company.com"
        }
        
        try:
            response = await client.post(f"{BASE_URL}/user/name", json=set_name_data)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Set name successful: {result.get('success')}")
                print(f"📝 Response: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ Set name failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Set name error: {e}")
        
        # Test 2: Get user name
        print("\n2️⃣ Getting user name via API")
        try:
            response = await client.get(f"{BASE_URL}/user/{TEST_USER_ID}/name")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Get name successful: {result.get('success')}")
                print(f"📝 Name info: first='{result.get('first_name')}', last='{result.get('last_name')}', display='{result.get('display_name')}'")
            else:
                print(f"❌ Get name failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Get name error: {e}")
        
        # Test 3: Get display name
        print("\n3️⃣ Getting display name via API")
        try:
            response = await client.get(f"{BASE_URL}/user/{TEST_USER_ID}/display-name")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Get display name successful: {result.get('success')}")
                print(f"👤 Display name: '{result.get('display_name')}'")
            else:
                print(f"❌ Get display name failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Get display name error: {e}")
        
        # Test 4: Get full profile
        print("\n4️⃣ Getting full profile via API")
        try:
            response = await client.get(f"{BASE_URL}/user/{TEST_USER_ID}/profile")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Get profile successful")
                print(f"📋 Profile: user_id='{result.get('user_id')}', timezone='{result.get('timezone')}'")
                print(f"📋 Names: first='{result.get('first_name')}', last='{result.get('last_name')}', display='{result.get('display_name')}'")
                print(f"📋 Email: '{result.get('email')}'")
            else:
                print(f"❌ Get profile failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Get profile error: {e}")
        
        # Test 5: Test partial update (only first name)
        print("\n5️⃣ Testing partial name update")
        partial_update = {
            "user_id": TEST_USER_ID,
            "first_name": "Alexandra"
            # Not updating other fields
        }
        
        try:
            response = await client.post(f"{BASE_URL}/user/name", json=partial_update)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Partial update successful")
                print(f"📝 Updated name: first='{result.get('first_name')}', last='{result.get('last_name')}'")
            else:
                print(f"❌ Partial update failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Partial update error: {e}")
        
        # Test 6: Test with non-existent user
        print("\n6️⃣ Testing with non-existent user")
        try:
            response = await client.get(f"{BASE_URL}/user/nonexistent_user/name")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Non-existent user handled gracefully")
                print(f"📝 Default values: first='{result.get('first_name')}', last='{result.get('last_name')}'")
            else:
                print(f"❌ Non-existent user failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Non-existent user error: {e}")
    
    print("\n🎉 API testing completed!")
    print("\n💡 Available endpoints:")
    print("   • POST /user/name - Set user name information")
    print("   • GET /user/{user_id}/name - Get user name information")
    print("   • GET /user/{user_id}/display-name - Get display name with fallbacks")
    print("   • GET /user/{user_id}/profile - Get full profile including names")


async def check_server():
    """Check if the Eva Assistant server is running."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                return True
    except Exception:
        pass
    return False


async def main():
    """Main function."""
    print("🔍 Checking if Eva Assistant server is running...")
    
    if not await check_server():
        print(f"❌ Eva Assistant server is not running at {BASE_URL}")
        print("💡 Please start the server first:")
        print("   cd /Users/balapanneerselvam/playground/eva")
        print("   uvicorn eva_assistant.app.main:app --reload")
        return
    
    print(f"✅ Eva Assistant server is running at {BASE_URL}")
    await test_name_api()


if __name__ == "__main__":
    asyncio.run(main()) 