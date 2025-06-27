#!/usr/bin/env python3
"""
Test script for Eva Assistant user name functionality.

Demonstrates:
- Setting user names
- Getting user names  
- Display name fallback logic
- Dynamic prompts with user context
- Email signatures with user names
"""

import asyncio
import sys
import os

# Add the eva_assistant directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from eva_assistant.auth.user_auth import UserAuthManager
from eva_assistant.agent.prompts import get_user_context, get_meeting_agent_prompt


async def test_user_names():
    """Test user name functionality."""
    print("🧪 Testing Eva Assistant User Name System")
    print("=" * 50)
    
    user_auth = UserAuthManager()
    
    # Test 1: Set user name for founder
    print("\n1️⃣ Setting user name for 'founder'")
    success = user_auth.set_user_name(
        user_id="founder",
        first_name="John",
        last_name="Doe", 
        display_name="John Doe",
        email="john.doe@company.com"
    )
    print(f"✅ Set name: {success}")
    
    # Test 2: Get user name information
    print("\n2️⃣ Getting user name information")
    name_info = user_auth.get_user_name("founder")
    print(f"📝 Name info: {name_info}")
    
    # Test 3: Get display name with fallback logic
    print("\n3️⃣ Testing display name fallback logic")
    display_name = user_auth.get_user_display_name("founder")
    print(f"👤 Display name: '{display_name}'")
    
    # Test 4: Test with user that has no name set
    print("\n4️⃣ Testing fallback for user with no name")
    no_name_display = user_auth.get_user_display_name("test_user")
    print(f"👤 No name display: '{no_name_display}'")
    
    # Test 5: Test with partial name info
    print("\n5️⃣ Setting partial name (first name only)")
    user_auth.set_user_name(
        user_id="partial_user",
        first_name="Jane"
    )
    partial_display = user_auth.get_user_display_name("partial_user")
    print(f"👤 Partial name display: '{partial_display}'")
    
    # Test 6: Test user context for prompts
    print("\n6️⃣ Testing user context for prompts")
    user_context = get_user_context("founder")
    print(f"🎯 User context: {user_context}")
    
    # Test 7: Test dynamic prompt generation
    print("\n7️⃣ Testing dynamic prompt generation")
    mock_state = {
        'user_id': 'founder',
        'primary_user_id': 'founder',
        'primary_email': 'john.doe@company.com',
        'current_request': 'Schedule a meeting with Alice',
        'context': {},
        'tool_results': []
    }
    
    prompt = get_meeting_agent_prompt(mock_state)
    # Show just the first few lines to see the personalization
    prompt_lines = prompt.split('\n')[:5]
    print("📝 Dynamic prompt (first 5 lines):")
    for line in prompt_lines:
        print(f"   {line}")
    
    # Test 8: Test different name combinations
    print("\n8️⃣ Testing different name combinations")
    
    test_cases = [
        ("user_display_only", {"display_name": "CEO Smith"}, "CEO Smith"),
        ("user_first_last", {"first_name": "Alice", "last_name": "Johnson"}, "Alice Johnson"),
        ("user_email_only", {"email": "bob@company.com"}, "bob@company.com"),
        ("user_empty", {}, "user_empty")
    ]
    
    for user_id, name_data, expected in test_cases:
        user_auth.set_user_name(user_id, **name_data)
        actual = user_auth.get_user_display_name(user_id)
        status = "✅" if actual == expected else "❌"
        print(f"   {status} {user_id}: expected '{expected}', got '{actual}'")
    
    print("\n9️⃣ Testing profile retrieval with names")
    profile = user_auth.get_user_profile("founder")
    print(f"📋 Full profile keys: {list(profile.keys())}")
    print(f"📋 Name fields: first_name='{profile.get('first_name')}', last_name='{profile.get('last_name')}', display_name='{profile.get('display_name')}'")
    
    print("\n🎉 User name testing completed!")
    print("\n💡 Key improvements:")
    print("   • User names are now stored in profiles")
    print("   • Display names have smart fallback logic")
    print("   • Prompts are dynamically personalized")
    print("   • Email signatures use actual user names")
    print("   • API endpoints support name management")


if __name__ == "__main__":
    asyncio.run(test_user_names()) 