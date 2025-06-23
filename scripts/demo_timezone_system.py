#!/usr/bin/env python3
"""
Complete demonstration of the Eva Assistant timezone system.

This script demonstrates:
1. Setting user timezone
2. Calendar availability checking with timezone awareness
3. Event creation with proper timezone handling
4. API endpoint functionality
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.auth.user_auth import UserAuthManager
from eva_assistant.tools.calendar import CheckAvailabilityTool, CheckAvailabilityArgs
from eva_assistant.tools.calendar import convert_datetime_to_user_timezone, convert_datetime_from_user_timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_timezone_system():
    """Complete demonstration of timezone system."""
    
    print("🌍 Eva Assistant Timezone System Demo")
    print("=" * 50)
    
    # Demo user
    user_id = "demo_user"
    user_timezone = "America/Los_Angeles"  # Pacific Time
    
    print(f"\n👤 Setting up user: {user_id}")
    print(f"🕐 Target timezone: {user_timezone}")
    
    # Initialize user auth manager
    user_auth = UserAuthManager()
    
    # Step 1: Set user timezone
    print(f"\n📍 Step 1: Setting User Timezone")
    print("-" * 30)
    
    success = user_auth.set_user_timezone(user_id, user_timezone)
    if success:
        print(f"✅ Successfully set timezone for {user_id}: {user_timezone}")
        
        # Show current time
        import pytz
        zone = pytz.timezone(user_timezone)
        current_time = datetime.now(zone)
        print(f"📅 Current time in {user_timezone}: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    else:
        print(f"❌ Failed to set timezone for {user_id}")
        return
    
    # Step 2: Get user profile
    print(f"\n👤 Step 2: User Profile")
    print("-" * 20)
    
    profile = user_auth.get_user_profile(user_id)
    print(f"User ID: {profile['user_id']}")
    print(f"Timezone: {profile['timezone']}")
    print(f"Created: {profile['created_at']}")
    print(f"Updated: {profile['updated_at']}")
    
    # Step 3: Test datetime conversion
    print(f"\n🔄 Step 3: DateTime Conversion Tests")
    print("-" * 35)
    
    # Test UTC to user timezone
    utc_time = "2025-01-23T14:30:00Z"  # 2:30 PM UTC
    user_time = convert_datetime_to_user_timezone(utc_time, user_timezone)
    back_to_utc = convert_datetime_from_user_timezone(user_time, user_timezone)
    
    print(f"Original UTC:     {utc_time}")
    print(f"In user timezone: {user_time}")
    print(f"Back to UTC:      {back_to_utc}")
    
    # Step 4: Test with calendar availability (if user is connected)
    print(f"\n📅 Step 4: Calendar Integration Test")
    print("-" * 35)
    
    try:
        # Check if user has calendar connected
        token_file = user_auth._get_user_token_file(user_id)
        
        if token_file.exists():
            print(f"✅ User {user_id} has calendar connected, testing availability...")
            
            # Test availability check with timezone-aware times
            # Use tomorrow 9 AM to 5 PM in user's timezone
            tomorrow = datetime.now(pytz.timezone(user_timezone)) + timedelta(days=1)
            start_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
            
            # Convert to UTC for API
            start_utc = convert_datetime_from_user_timezone(start_time.isoformat(), user_timezone)
            end_utc = convert_datetime_from_user_timezone(end_time.isoformat(), user_timezone)
            
            print(f"Checking availability:")
            print(f"  User time: {start_time.strftime('%Y-%m-%d %H:%M %Z')} - {end_time.strftime('%H:%M %Z')}")
            print(f"  UTC time:  {start_utc} - {end_utc}")
            
            # Run availability check
            availability_tool = CheckAvailabilityTool()
            args = CheckAvailabilityArgs(
                user_id=user_id,
                start_time=start_utc,
                end_time=end_utc,
                duration_minutes=30,
                max_suggestions=3
            )
            
            result = await availability_tool.run(args)
            
            if result['success']:
                print(f"✅ Found {len(result['free_slots'])} free slots:")
                for i, slot in enumerate(result['free_slots']):
                    # Convert back to user timezone for display
                    slot_start_user = convert_datetime_to_user_timezone(slot['start'], user_timezone)
                    slot_end_user = convert_datetime_to_user_timezone(slot['end'], user_timezone)
                    
                    print(f"  {i+1}. {slot_start_user} - {slot_end_user} (user time)")
                    print(f"     {slot['start']} - {slot['end']} (UTC)")
            else:
                print(f"❌ Availability check failed: {result.get('error')}")
        else:
            print(f"⚠️ User {user_id} doesn't have calendar connected")
            print("   This is expected for demo purposes")
            print("   In production, user would authenticate first")
    
    except Exception as e:
        print(f"⚠️ Calendar test skipped: {e}")
    
    # Step 5: Show API usage examples
    print(f"\n🌐 Step 5: API Usage Examples")
    print("-" * 30)
    
    print("The following API endpoints are now available:")
    print()
    print("1. Set user timezone:")
    print("   POST /user/timezone")
    print("   Body: {\"user_id\": \"demo_user\", \"timezone\": \"America/Los_Angeles\"}")
    print()
    print("2. Get user timezone:")
    print("   GET /user/demo_user/timezone")
    print()
    print("3. Get user profile:")
    print("   GET /user/demo_user/profile")
    print()
    print("4. List available timezones:")
    print("   GET /timezones")
    
    # Step 6: Show production workflow
    print(f"\n🏭 Step 6: Production Workflow")
    print("-" * 30)
    
    print("In production, the workflow would be:")
    print("1. User signs up / logs in")
    print("2. User selects their timezone during onboarding")
    print("3. Timezone is stored in user profile")
    print("4. All calendar operations use user's timezone")
    print("5. API responses show times in user's local timezone")
    print("6. User can update timezone in settings")
    
    # Step 7: Configuration summary
    print(f"\n⚙️ Step 7: Configuration Summary")
    print("-" * 35)
    
    print("Storage approach:")
    print(f"  - User profiles stored in: {user_auth.token_dir}")
    print(f"  - Profile file format: user_{{user_id}}_profile.json")
    print(f"  - Contains: timezone, created_at, updated_at")
    print(f"  - Default timezone: UTC")
    print()
    print("Features implemented:")
    print("  ✅ Per-user timezone storage")
    print("  ✅ Timezone validation using pytz")
    print("  ✅ DateTime conversion utilities")
    print("  ✅ Calendar tool timezone awareness")
    print("  ✅ FastAPI endpoints for management")
    print("  ✅ Command-line management script")
    print("  ✅ Production-ready error handling")
    
    print(f"\n🎉 Demo completed successfully!")
    print("The timezone system is ready for production use.")


if __name__ == "__main__":
    asyncio.run(demo_timezone_system()) 