#!/usr/bin/env python3
"""
Test script for LangSmith integration with Eva Assistant.

This script helps verify that the langgraph.json configuration works
and that Eva can be monitored in LangSmith.
"""

import os
import asyncio
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.agent.graph import get_eva_graph
from eva_assistant.agent.state import create_eva_state


async def test_eva_with_langsmith():
    """Test Eva Assistant with LangSmith tracing enabled."""
    
    print("🚀 Testing Eva Assistant with LangSmith...")
    
    # Set up LangSmith environment if not already set
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("⚠️  LANGCHAIN_API_KEY not set - tracing will be disabled")
    
    # Get the graph (this is what LangSmith will call)
    graph = get_eva_graph()
    print("✅ Graph loaded successfully")
    
    # Create test state
    test_state = create_eva_state(
        user_id="test_user",
        conversation_id="test_conv_001",
        current_request="Schedule a meeting with Alice tomorrow at 3pm"
    )
    
    print(f"📋 Test request: {test_state['current_request']}")
    print("🔄 Processing with LangSmith tracing...")
    
    try:
        # Run the graph (this will be traced in LangSmith)
        final_state = None
        step_count = 0
        
        async for state_update in graph.astream(test_state):
            step_count += 1
            node_name = list(state_update.keys())[0]
            print(f"   Step {step_count}: {node_name}")
            final_state = state_update
        
        print(f"✅ Graph completed successfully in {step_count} steps")
        
        # Extract final response
        if final_state:
            last_node_state = list(final_state.values())[0]
            if isinstance(last_node_state, dict) and "final_response" in last_node_state:
                print(f"💬 Eva's response: {last_node_state['final_response']}")
            else:
                print("📝 Response ready (check LangSmith for details)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error running graph: {e}")
        return False


def main():
    """Main test function."""
    print("Eva Assistant - LangSmith Integration Test")
    print("=" * 50)
    
    # Show environment status
    print(f"🔧 Environment:")
    print(f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"   LANGCHAIN_API_KEY: {'✅ Set' if os.getenv('LANGCHAIN_API_KEY') else '⚠️  Not set'}")
    print(f"   LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2', 'false')}")
    print(f"   LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT', 'eva-assistant')}")
    print()
    
    # Run async test
    success = asyncio.run(test_eva_with_langsmith())
    
    if success:
        print("\n🎉 Test completed successfully!")
        if os.getenv("LANGCHAIN_API_KEY"):
            print("📊 Check your LangSmith dashboard to see the traced execution")
        else:
            print("💡 Set LANGCHAIN_API_KEY to enable LangSmith tracing")
    else:
        print("\n💥 Test failed - check the logs above")
        sys.exit(1)


if __name__ == "__main__":
    main() 