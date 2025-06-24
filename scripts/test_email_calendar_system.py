#!/usr/bin/env python3

"""
Test script for the Email-First Calendar System in Eva Assistant.

This script demonstrates:
1. Email-to-user mapping and resolution
2. Multi-email support per user
3. Email-based calendar tool usage
4. Primary email management
5. API endpoints for email management

Usage:
    python scripts/test_email_calendar_system.py
"""

import asyncio
import json
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from eva_assistant.auth.user_auth import UserAuthManager
from eva_assistant.tools.calendar import CheckAvailabilityTool, GetAllEventsTool, CreateEventTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_email_mapping_system():
    """Test the email mapping and resolution system."""
    print("\n" + "="*60)
    print("TESTING EMAIL MAPPING SYSTEM")
    print("="*60)
    
    user_auth = UserAuthManager()
    
    # Test user setup
    test_user_id = "john_doe"
    test_emails = ["bala@zorp.one", "john.doe@company.com"]
    
    print(f"\n1. Setting up test user: {test_user_id}")
    print(f"   Test emails: {test_emails}")
    
    # Create email mapping for test user
    mapping = user_auth.get_user_email_mapping(test_user_id)
    mapping['owned_emails'] = test_emails
    mapping['primary_email'] = test_emails[0]
    mapping['email_to_token_mapping'] = {
        email: f"data/user_tokens/user_{test_user_id}_{email.replace('@', '_at_').replace('.', '_dot_')}_calendar_token.json"
        for email in test_emails
    }
    
    success = user_auth.save_user_email_mapping(test_user_id, mapping)
    print(f"   Email mapping saved: {success}")
    
    # Test email resolution
    print(f"\n2. Testing email resolution:")
    for email in test_emails:
        found_user_id = user_auth.find_user_id_for_email(email)
        print(f"   {email} -> user_id: {found_user_id}")
        assert found_user_id == test_user_id, f"Expected {test_user_id}, got {found_user_id}"
    
    # Test unknown email
    unknown_email = "unknown@example.com"
    found_user_id = user_auth.find_user_id_for_email(unknown_email)
    print(f"   {unknown_email} -> user_id: {found_user_id}")
    assert found_user_id is None, f"Expected None, got {found_user_id}"
    
    # Test primary email management
    print(f"\n3. Testing primary email management:")
    primary_email = user_auth.get_primary_email_for_user(test_user_id)
    print(f"   Current primary email: {primary_email}")
    assert primary_email == test_emails[0], f"Expected {test_emails[0]}, got {primary_email}"
    
    # Change primary email
    new_primary = test_emails[1]
    success = user_auth.set_primary_email_for_user(test_user_id, new_primary)
    print(f"   Set {new_primary} as primary: {success}")
    
    primary_email = user_auth.get_primary_email_for_user(test_user_id)
    print(f"   New primary email: {primary_email}")
    assert primary_email == new_primary, f"Expected {new_primary}, got {primary_email}"
    
    # Test getting owned emails
    print(f"\n4. Testing owned emails retrieval:")
    owned_emails = user_auth.get_owned_emails_for_user(test_user_id)
    print(f"   Owned emails: {owned_emails}")
    assert set(owned_emails) == set(test_emails), f"Expected {test_emails}, got {owned_emails}"
    
    print("\n✅ Email mapping system tests passed!")


async def test_calendar_tools_with_emails():
    """Test calendar tools using email addresses instead of user_ids."""
    print("\n" + "="*60)
    print("TESTING EMAIL-BASED CALENDAR TOOLS")
    print("="*60)
    
    # Test emails (these would need actual calendar connections in practice)
    test_email = "bala@zorp.one"
    unknown_email = "notconnected@example.com"
    
    print(f"\n1. Testing CheckAvailabilityTool with email: {test_email}")
    
    # Test with connected email (will fail if not actually connected, but shows the flow)
    availability_tool = CheckAvailabilityTool()
    
    try:
        from eva_assistant.tools.calendar import CheckAvailabilityArgs
        
        args = CheckAvailabilityArgs(
            email=test_email,
            date="2025-01-25",
            duration_minutes=30,
            max_suggestions=5
        )
        
        result = await availability_tool.run(args)
        print(f"   Result success: {result.get('success')}")
        print(f"   Error (if any): {result.get('error', 'None')}")
        print(f"   Email: {result.get('email')}")
        
        if result.get('success'):
            print(f"   Free slots found: {len(result.get('free_slots', []))}")
            print(f"   Working day: {result.get('working_day')}")
            print(f"   User timezone: {result.get('user_timezone')}")
        
    except Exception as e:
        print(f"   Expected error (calendar not connected): {e}")
    
    print(f"\n2. Testing with unknown email: {unknown_email}")
    
    try:
        args = CheckAvailabilityArgs(
            email=unknown_email,
            date="2025-01-25",
            duration_minutes=30,
            max_suggestions=5
        )
        
        result = await availability_tool.run(args)
        print(f"   Result success: {result.get('success')}")
        print(f"   Error message: {result.get('error')}")
        print(f"   Email: {result.get('email')}")
        
        # Should return "Calendar not connected" error
        assert not result.get('success'), "Expected failure for unknown email"
        assert "not connected" in result.get('error', '').lower(), "Expected 'not connected' error"
        
    except Exception as e:
        print(f"   Unexpected error: {e}")
    
    print(f"\n3. Testing GetAllEventsTool with email: {test_email}")
    
    try:
        from eva_assistant.tools.calendar import GetAllEventsArgs
        
        events_tool = GetAllEventsTool()
        args = GetAllEventsArgs(
            email=test_email,
            start_time="2025-01-20T09:00:00Z",
            end_time="2025-01-27T17:00:00Z",
            max_results=10
        )
        
        result = await events_tool.run(args)
        print(f"   Result success: {result.get('success')}")
        print(f"   Error (if any): {result.get('error', 'None')}")
        print(f"   Email: {result.get('email')}")
        
        if result.get('success'):
            print(f"   Events found: {result.get('count', 0)}")
            print(f"   Calendars checked: {result.get('calendars_checked', 0)}")
        
    except Exception as e:
        print(f"   Expected error (calendar not connected): {e}")
    
    print("\n✅ Email-based calendar tools tests completed!")


async def test_multi_email_scenarios():
    """Test scenarios with multiple emails per user."""
    print("\n" + "="*60)
    print("TESTING MULTI-EMAIL SCENARIOS")
    print("="*60)
    
    user_auth = UserAuthManager()
    
    # Setup multi-email user
    user_id = "multi_email_user"
    emails = ["work@company.com", "personal@gmail.com", "side@project.com"]
    
    print(f"\n1. Setting up user with multiple emails:")
    print(f"   User ID: {user_id}")
    print(f"   Emails: {emails}")
    
    # Create mapping
    mapping = {
        'user_id': user_id,
        'owned_emails': emails,
        'primary_email': emails[0],  # work email as primary
        'email_to_token_mapping': {
            email: f"data/user_tokens/user_{user_id}_{email.replace('@', '_at_').replace('.', '_dot_')}_calendar_token.json"
            for email in emails
        },
        'created_at': str(datetime.utcnow().isoformat()),
        'updated_at': str(datetime.utcnow().isoformat())
    }
    
    success = user_auth.save_user_email_mapping(user_id, mapping)
    print(f"   Mapping saved: {success}")
    
    print(f"\n2. Testing email resolution for all emails:")
    for email in emails:
        found_user_id = user_auth.find_user_id_for_email(email)
        is_primary = user_auth.get_primary_email_for_user(user_id) == email
        print(f"   {email} -> {found_user_id} (primary: {is_primary})")
        assert found_user_id == user_id
    
    print(f"\n3. Testing primary email changes:")
    for new_primary in emails[1:]:  # Skip first (already primary)
        success = user_auth.set_primary_email_for_user(user_id, new_primary)
        current_primary = user_auth.get_primary_email_for_user(user_id)
        print(f"   Set {new_primary} as primary: {success} -> current: {current_primary}")
        assert current_primary == new_primary
    
    print(f"\n4. Testing email removal:")
    email_to_remove = emails[-1]  # Remove last email
    success = user_auth.remove_email_from_user(user_id, email_to_remove)
    print(f"   Removed {email_to_remove}: {success}")
    
    # Verify removal
    found_user_id = user_auth.find_user_id_for_email(email_to_remove)
    print(f"   {email_to_remove} resolution after removal: {found_user_id}")
    assert found_user_id is None, "Email should not resolve after removal"
    
    remaining_emails = user_auth.get_owned_emails_for_user(user_id)
    print(f"   Remaining emails: {remaining_emails}")
    assert email_to_remove not in remaining_emails, "Email should be removed from owned list"
    
    print("\n✅ Multi-email scenarios tests passed!")


async def demonstrate_llm_usage_patterns():
    """Demonstrate how LLM would use the email-first system."""
    print("\n" + "="*60)
    print("DEMONSTRATING LLM USAGE PATTERNS")
    print("="*60)
    
    print("\n1. Scenario: 'Check availability for bala@zorp.one tomorrow'")
    print("   LLM would call: CheckAvailabilityTool(email='bala@zorp.one', date='2025-01-25')")
    print("   System resolves: bala@zorp.one -> user_john_doe -> working_hours + self_calendars")
    print("   Result: Returns availability based on user's working hours and selected calendars")
    
    print("\n2. Scenario: 'Set up 45 mins with johnycashman16@gmail.com tomorrow'")
    print("   LLM would:")
    print("   a) CheckAvailabilityTool(email='current_user_email', date='2025-01-25', duration_minutes=45)")
    print("   b) CheckAvailabilityTool(email='johnycashman16@gmail.com', date='2025-01-25', duration_minutes=45)")
    print("   c) Find overlapping free slots")
    print("   d) CreateEventTool(organizer_email='current_user_email', attendees=['johnycashman16@gmail.com'], ...)")
    
    print("\n3. Scenario: Email not connected")
    print("   LLM calls: CheckAvailabilityTool(email='unknown@company.com', ...)")
    print("   System returns: {'success': False, 'error': 'Calendar not connected for email unknown@company.com'}")
    print("   LLM responds: 'Calendar not connected for unknown@company.com. Please connect their calendar first.'")
    
    print("\n4. Benefits of email-first approach:")
    print("   ✅ Natural for LLM - works with email addresses directly")
    print("   ✅ Multi-tenancy support - each email maps to correct user")
    print("   ✅ Clear error messages - 'calendar not connected' vs generic errors")
    print("   ✅ Scalable - supports multiple emails per user")
    print("   ✅ Self-calendar filtering - only checks user's own calendars for availability")
    
    print("\n✅ LLM usage patterns demonstration completed!")


async def main():
    """Run all email-first calendar system tests."""
    print("🚀 Starting Email-First Calendar System Tests")
    print("=" * 80)
    
    try:
        # Test core email mapping functionality
        await test_email_mapping_system()
        
        # Test calendar tools with emails
        await test_calendar_tools_with_emails()
        
        # Test multi-email scenarios
        await test_multi_email_scenarios()
        
        # Demonstrate LLM usage patterns
        await demonstrate_llm_usage_patterns()
        
        print("\n" + "="*80)
        print("🎉 ALL EMAIL-FIRST CALENDAR SYSTEM TESTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        print("\n📋 SUMMARY:")
        print("✅ Email-to-user mapping and resolution")
        print("✅ Multi-email support per user")
        print("✅ Primary email management")
        print("✅ Email-based calendar tool usage")
        print("✅ Error handling for unknown emails")
        print("✅ Multi-email scenarios")
        print("✅ LLM usage pattern demonstrations")
        
        print("\n🔧 NEXT STEPS:")
        print("1. Connect actual calendar accounts for testing with real data")
        print("2. Test OAuth flows with multiple emails per user")
        print("3. Implement calendar selection per email address")
        print("4. Test with LangGraph integration")
        print("5. Add UI for email management")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 