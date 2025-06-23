#!/usr/bin/env python3
"""
Test script to demonstrate calendar tool input/output logging.

This script shows exactly what parameters are passed to calendar tools
and what results are returned, helping with debugging and monitoring.
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from eva_assistant.agent.graph import EvaGraph

# Configure logging to show all INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress some verbose logs but keep calendar tool logs
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


async def test_calendar_tool_logging():
    """Test calendar tools with comprehensive logging."""
    print("=" * 60)
    print("CALENDAR TOOL INPUT/OUTPUT LOGGING TEST")
    print("=" * 60)
    print()
    
    graph = EvaGraph()
    
    # Test scenarios that trigger different calendar tools
    test_scenarios = [
        {
            "name": "Availability Check",
            "message": "Check my availability tomorrow from 9 AM to 5 PM for a 30-minute meeting",
            "expected_tool": "check_calendar_availability"
        },
        {
            "name": "Event Creation",
            "message": "Schedule a meeting tomorrow at 2 PM for 1 hour with test@example.com titled 'Team Sync'",
            "expected_tool": "create_calendar_event"
        },
        {
            "name": "Get Events",
            "message": "What meetings do I have tomorrow?",
            "expected_tool": "get_all_calendar_events"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*20} TEST {i}: {scenario['name']} {'='*20}")
        print(f"Query: {scenario['message']}")
        print(f"Expected tool: {scenario['expected_tool']}")
        print("-" * 60)
        
        try:
            result = await graph.process_message(
                scenario['message'],
                user_id='john_doe'
            )
            
            print("\n" + "="*20 + " SUMMARY " + "="*20)
            print(f"✅ Success: {result['success']}")
            print(f"🔧 Tool calls made: {len(result.get('tool_calls', []))}")
            print(f"📝 Response length: {len(result['response'])} characters")
            print(f"🎯 Reflection approved: {result.get('reflection_approved', False)}")
            
            if result.get('error'):
                print(f"❌ Error: {result['error']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        print("\n" + "="*60)
        
        # Add delay between tests to make logs more readable
        await asyncio.sleep(2)
    
    print("\n🎉 All calendar tool logging tests completed!")
    print("\nKey logging features demonstrated:")
    print("✅ Input parameters with normalized datetime formats")
    print("✅ Output results with success status and data")
    print("✅ Error handling and fallback logging")
    print("✅ Calendar selection and authentication flow")
    print("✅ Tool execution timing and performance")


if __name__ == "__main__":
    print("Starting calendar tool logging demonstration...")
    asyncio.run(test_calendar_tool_logging()) 