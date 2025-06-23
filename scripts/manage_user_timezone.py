#!/usr/bin/env python3
"""
User timezone management script.

This script allows you to:
- Set a user's timezone
- Get a user's current timezone
- List available timezones
- Test timezone conversion
"""

import asyncio
import logging
import sys
from pathlib import Path
import pytz
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.auth.user_auth import UserAuthManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def list_common_timezones():
    """List commonly used timezones."""
    common_timezones = [
        'UTC',
        'US/Eastern',
        'US/Central', 
        'US/Mountain',
        'US/Pacific',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Kolkata',
        'Australia/Sydney',
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
        'America/Toronto',
        'America/Vancouver',
        'Pacific/Auckland'
    ]
    
    print("\n🌍 Common Timezones:")
    print("=" * 50)
    for tz in common_timezones:
        try:
            zone = pytz.timezone(tz)
            now = datetime.now(zone)
            print(f"  {tz:<20} - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception as e:
            print(f"  {tz:<20} - Invalid timezone")


def search_timezones(search_term: str):
    """Search for timezones matching a term."""
    print(f"\n🔍 Timezones matching '{search_term}':")
    print("=" * 50)
    
    matches = [tz for tz in pytz.all_timezones if search_term.lower() in tz.lower()]
    
    if not matches:
        print(f"No timezones found matching '{search_term}'")
        return
    
    for tz in sorted(matches)[:20]:  # Limit to first 20 matches
        try:
            zone = pytz.timezone(tz)
            now = datetime.now(zone)
            print(f"  {tz:<30} - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception as e:
            print(f"  {tz:<30} - Invalid timezone")
    
    if len(matches) > 20:
        print(f"  ... and {len(matches) - 20} more matches")


async def main():
    """Main function for timezone management."""
    if len(sys.argv) < 2:
        print("User Timezone Management")
        print("=" * 30)
        print("Usage:")
        print("  python scripts/manage_user_timezone.py set <user_id> <timezone>")
        print("  python scripts/manage_user_timezone.py get <user_id>")
        print("  python scripts/manage_user_timezone.py list")
        print("  python scripts/manage_user_timezone.py search <search_term>")
        print("  python scripts/manage_user_timezone.py test <user_id>")
        print("\nExamples:")
        print("  python scripts/manage_user_timezone.py set john_doe America/New_York")
        print("  python scripts/manage_user_timezone.py get john_doe")
        print("  python scripts/manage_user_timezone.py search america")
        return
    
    command = sys.argv[1].lower()
    user_auth = UserAuthManager()
    
    if command == "set":
        if len(sys.argv) != 4:
            print("❌ Usage: set <user_id> <timezone>")
            return
        
        user_id = sys.argv[2]
        timezone = sys.argv[3]
        
        print(f"Setting timezone for user '{user_id}' to '{timezone}'...")
        
        success = user_auth.set_user_timezone(user_id, timezone)
        if success:
            print(f"✅ Successfully set timezone for {user_id}: {timezone}")
            
            # Show current time in that timezone
            try:
                zone = pytz.timezone(timezone)
                current_time = datetime.now(zone)
                print(f"📅 Current time in {timezone}: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            except Exception as e:
                print(f"⚠️ Could not display current time: {e}")
        else:
            print(f"❌ Failed to set timezone for {user_id}")
    
    elif command == "get":
        if len(sys.argv) != 3:
            print("❌ Usage: get <user_id>")
            return
        
        user_id = sys.argv[2]
        
        timezone = user_auth.get_user_timezone(user_id)
        profile = user_auth.get_user_profile(user_id)
        
        print(f"\n👤 User Profile: {user_id}")
        print("=" * 40)
        print(f"Timezone: {timezone}")
        print(f"Created: {profile.get('created_at', 'Unknown')}")
        print(f"Updated: {profile.get('updated_at', 'Unknown')}")
        
        # Show current time in user's timezone
        try:
            zone = pytz.timezone(timezone)
            current_time = datetime.now(zone)
            print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception as e:
            print(f"⚠️ Could not display current time: {e}")
    
    elif command == "list":
        list_common_timezones()
    
    elif command == "search":
        if len(sys.argv) != 3:
            print("❌ Usage: search <search_term>")
            return
        
        search_term = sys.argv[2]
        search_timezones(search_term)
    
    elif command == "test":
        if len(sys.argv) != 3:
            print("❌ Usage: test <user_id>")
            return
        
        user_id = sys.argv[2]
        
        print(f"\n🧪 Testing timezone conversion for user: {user_id}")
        print("=" * 50)
        
        user_timezone = user_auth.get_user_timezone(user_id)
        print(f"User timezone: {user_timezone}")
        
        # Test datetime conversion
        from eva_assistant.tools.calendar import convert_datetime_to_user_timezone, convert_datetime_from_user_timezone
        
        # Test with current UTC time
        utc_time = datetime.utcnow().isoformat() + 'Z'
        user_time = convert_datetime_to_user_timezone(utc_time, user_timezone)
        back_to_utc = convert_datetime_from_user_timezone(user_time, user_timezone)
        
        print(f"\n🔄 Conversion Test:")
        print(f"UTC time:      {utc_time}")
        print(f"User time:     {user_time}")
        print(f"Back to UTC:   {back_to_utc}")
        
        # Test with a specific meeting time
        meeting_time = "2025-01-23T14:30:00Z"  # 2:30 PM UTC
        user_meeting_time = convert_datetime_to_user_timezone(meeting_time, user_timezone)
        
        print(f"\n📅 Meeting Time Example:")
        print(f"Meeting in UTC:        {meeting_time}")
        print(f"Meeting in user TZ:    {user_meeting_time}")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: set, get, list, search, test")


if __name__ == "__main__":
    asyncio.run(main()) 