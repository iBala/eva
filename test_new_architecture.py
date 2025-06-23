#!/usr/bin/env python3
"""
Test script for the new Eva LLM Agent architecture.

Tests:
1. Tool discovery and conversion
2. LLM agent initialization  
3. Simple message processing
4. Tool calling functionality
"""

import asyncio
import logging
import os
import sys

# Add the eva_assistant directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'eva_assistant'))

from eva_assistant.tools import convert_tools_to_litellm_format, get_all_tools
# LLM Agent removed - using nodes directly
from eva_assistant.agent.graph import get_eva_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_tool_discovery():
    """Test tool discovery and conversion."""
    print("\n=== Testing Tool Discovery ===")
    
    # Get all tools
    tools = get_all_tools()
    print(f"✅ Discovered {len(tools)} tools: {list(tools.keys())}")
    
    # Convert to LiteLLM format
    litellm_tools = convert_tools_to_litellm_format()
    print(f"✅ Converted {len(litellm_tools)} tools to LiteLLM format")
    
    # Print first tool for inspection
    if litellm_tools:
        first_tool = litellm_tools[0]
        print(f"📋 Sample tool: {first_tool['function']['name']}")
        print(f"   Description: {first_tool['function']['description']}")
    
    return len(tools) > 0


async def test_llm_agent():
    """Test LLM agent initialization."""
    print("\n=== Testing LLM Agent ===")
    
    try:
        agent = EvaLLMAgent()
        print(f"✅ LLM Agent initialized with {len(agent.tools)} tools")
        print(f"   Model: {agent.model}")
        print(f"   Temperature: {agent.temperature}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize LLM Agent: {e}")
        return False


async def test_simple_message():
    """Test simple message processing without tools."""
    print("\n=== Testing Simple Message Processing ===")
    
    try:
        agent = EvaLLMAgent()
        
        # Test simple greeting
        result = await agent.process_request(
            user_message="Hello Eva, how are you?",
            user_id="test_user"
        )
        
        print(f"✅ Message processed successfully")
        print(f"   Response: {result['response'][:100]}...")
        print(f"   Tool calls: {len(result['tool_calls'])}")
        print(f"   Success: {result['success']}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Failed to process simple message: {e}")
        return False


async def test_graph_integration():
    """Test graph integration."""
    print("\n=== Testing Graph Integration ===")
    
    try:
        eva_graph = get_eva_graph()
        
        result = await eva_graph.process_message(
            user_message="Hello Eva!",
            user_id="test_user"
        )
        
        print(f"✅ Graph processed message successfully")
        print(f"   Response: {result['response'][:100]}...")
        print(f"   Tool calls: {len(result['tool_calls'])}")
        print(f"   Success: {result['success']}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Failed to process via graph: {e}")
        return False


async def test_calendar_request():
    """Test calendar-related request that should trigger tools."""
    print("\n=== Testing Calendar Request (Tool Calling) ===")
    
    try:
        eva_graph = get_eva_graph()
        
        result = await eva_graph.process_message(
            user_message="Check my calendar availability for tomorrow afternoon",
            user_id="john_doe"  # User we know has calendar connected
        )
        
        print(f"✅ Calendar request processed")
        print(f"   Response: {result['response'][:150]}...")
        print(f"   Tool calls: {len(result['tool_calls'])}")
        print(f"   Success: {result['success']}")
        
        if result['tool_calls']:
            for i, tool_call in enumerate(result['tool_calls']):
                print(f"   Tool {i+1}: {tool_call['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to process calendar request: {e}")
        logger.error(f"Calendar request error details: {e}", exc_info=True)
        return False


async def main():
    """Run all tests."""
    print("🚀 Testing New Eva LLM Agent Architecture")
    print("=" * 50)
    
    tests = [
        ("Tool Discovery", test_tool_discovery),
        ("LLM Agent Init", test_llm_agent),
        ("Simple Message", test_simple_message),
        ("Graph Integration", test_graph_integration),
        ("Calendar Request", test_calendar_request),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! New architecture is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 