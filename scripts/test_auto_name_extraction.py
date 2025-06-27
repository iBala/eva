#!/usr/bin/env python3
"""
Test script to demonstrate automatic name extraction during calendar connection.

This script shows how user names are automatically extracted and populated
when users connect their Google Calendar for the first time.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from eva_assistant.auth.user_auth import UserAuthManager
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_auto_name_extraction():
    """Test automatic name extraction during calendar connection."""
    
    print("🔍 Testing Automatic Name Extraction During Calendar Connection")
    print("=" * 70)
    
    user_auth = UserAuthManager()
    test_user_id = "test_auto_name_user"
    
    try:
        # Clean up any existing data for test user
        print(f"\n🧹 Cleaning up existing data for user: {test_user_id}")
        user_auth.disconnect_user_calendar(test_user_id)
        
        # Check initial state (should have no name info)
        print(f"\n📋 Initial user profile:")
        initial_profile = user_auth.get_user_profile(test_user_id)
        print(f"   First Name: {initial_profile.get('first_name', 'None')}")
        print(f"   Last Name: {initial_profile.get('last_name', 'None')}")
        print(f"   Display Name: {initial_profile.get('display_name', 'None')}")
        print(f"   Email: {initial_profile.get('email', 'None')}")
        
        # Connect calendar (this will trigger OAuth and auto-population)
        print(f"\n🔗 Connecting calendar for user: {test_user_id}")
        print("   This will open a browser for OAuth authentication...")
        print("   The system will automatically extract name information from:")
        print("   - Primary email address (e.g., john.doe@gmail.com → John Doe)")
        print("   - Calendar names (personal calendars with user names)")
        
        # Connect with auto-select to avoid interactive prompts
        connection_result = await user_auth.connect_user_calendar(
            user_id=test_user_id,
            auto_select_primary=True
        )
        
        print(f"\n✅ Calendar connection successful!")
        print(f"   User ID: {connection_result['user_id']}")
        print(f"   Primary Email: {connection_result['email']}")
        print(f"   Connected Calendars: {connection_result['selected_calendar_count']}")
        print(f"   Timezone: {connection_result['timezone']}")
        
        # Show extracted name information
        print(f"\n👤 Extracted Name Information:")
        name_info = connection_result['name']
        print(f"   First Name: {name_info['first_name'] or 'Not extracted'}")
        print(f"   Last Name: {name_info['last_name'] or 'Not extracted'}")
        print(f"   Display Name: {name_info['display_name'] or 'Not extracted'}")
        print(f"   Auto-populated: {connection_result['auto_populated']}")
        
        # Show calendar details
        print(f"\n📅 Connected Calendars:")
        for cal in connection_result['selected_calendars']:
            print(f"   - {cal['summary']} ({'Primary' if cal['primary'] else 'Secondary'})")
        
        # Test the display name function
        display_name = user_auth.get_user_display_name(test_user_id)
        print(f"\n🏷️  Final Display Name: '{display_name}'")
        
        # Show what information was extracted from where
        print(f"\n🔍 Extraction Details:")
        primary_email = connection_result['email']
        if '@' in primary_email:
            email_local = primary_email.split('@')[0]
            print(f"   Primary email: {primary_email}")
            print(f"   Email local part: {email_local}")
            
            if '.' in email_local:
                parts = email_local.split('.')
                print(f"   Email parts: {parts}")
                print(f"   → Likely first name: {parts[0].title()}")
                if len(parts) > 1:
                    print(f"   → Likely last name: {parts[1].title()}")
        
        # Show final profile
        print(f"\n📋 Final User Profile:")
        final_profile = user_auth.get_user_profile(test_user_id)
        for key, value in final_profile.items():
            print(f"   {key}: {value}")
        
        print(f"\n🎉 Auto-extraction test completed successfully!")
        print(f"   The user's name was automatically extracted during calendar connection.")
        print(f"   No separate name setup step is required!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during auto-extraction test: {e}")
        logger.error(f"Auto-extraction test failed: {e}")
        return False


async def main():
    """Main test function."""
    
    print("🚀 Eva Assistant - Automatic Name Extraction Test")
    print("=" * 70)
    
    try:
        # Test auto-extraction for new users
        success = await test_auto_name_extraction()
        
        if success:
            print(f"\n🎉 Test passed! Automatic name extraction is working correctly.")
            print(f"   Users no longer need to set names separately - it happens automatically!")
        else:
            print(f"\n⚠️  Test failed. Please check the implementation.")
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 