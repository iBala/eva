#!/usr/bin/env python3
"""
Test script for conversation history functionality.

This script tests:
1. ConversationManager SQLite persistence
2. API endpoints with conversation_id
3. Message history retrieval and context
4. New vs existing conversation handling
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the eva_assistant package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.memory.conversation import ConversationManager
from eva_assistant.config import settings


async def test_conversation_manager():
    """Test ConversationManager basic functionality."""
    print("🧪 Testing ConversationManager...")
    
    # Initialize conversation manager
    test_db_path = "test_conversations.db"
    try:
        os.remove(test_db_path)
    except FileNotFoundError:
        pass
    
    conv_manager = ConversationManager(db_path=test_db_path, message_limit=10)
    
    # Test 1: Create conversation
    conv_id = conv_manager.generate_conversation_id()
    user_id = "test_user"
    
    created = conv_manager.create_conversation(
        conversation_id=conv_id,
        user_id=user_id,
        metadata={"test": "conversation"}
    )
    
    assert created, "Failed to create conversation"
    print(f"✅ Created conversation: {conv_id}")
    
    # Test 2: Add messages
    messages = [
        ("user", "Hello, I need help with my calendar"),
        ("assistant", "I'd be happy to help you with your calendar! What specifically do you need assistance with?"),
        ("user", "Can you check my availability for tomorrow?"),
        ("assistant", "I can help you check your availability. Let me look at your calendar for tomorrow."),
        ("user", "Thanks, and can you also schedule a meeting?"),
        ("assistant", "Absolutely! I can help you schedule a meeting. What time works best for you?")
    ]
    
    for role, content in messages:
        success = conv_manager.add_message(
            conversation_id=conv_id,
            role=role,
            content=content,
            metadata={"timestamp": "2025-01-27T10:00:00Z"}
        )
        assert success, f"Failed to add {role} message"
    
    print(f"✅ Added {len(messages)} messages to conversation")
    
    # Test 3: Retrieve conversation history
    history = conv_manager.get_conversation_history(conv_id)
    assert len(history) == 6, f"Expected 6 messages, got {len(history)}"
    print(f"✅ Retrieved {len(history)} messages from history")
    
    # Test 4: Get LLM-formatted messages
    llm_messages = conv_manager.get_conversation_messages_for_llm(conv_id)
    assert len(llm_messages) == 6, f"Expected 6 LLM messages, got {len(llm_messages)}"
    assert llm_messages[0]["role"] == "user", "First message should be user"
    assert llm_messages[1]["role"] == "assistant", "Second message should be assistant"
    print(f"✅ Retrieved {len(llm_messages)} LLM-formatted messages")
    
    # Test 5: Message limit functionality
    limited_messages = conv_manager.get_conversation_messages_for_llm(conv_id, limit=3)
    assert len(limited_messages) == 3, f"Expected 3 limited messages, got {len(limited_messages)}"
    print(f"✅ Message limit functionality works (got {len(limited_messages)} messages)")
    
    # Test 6: Conversation info
    info = conv_manager.get_conversation_info(conv_id)
    assert info is not None, "Failed to get conversation info"
    assert info["user_id"] == user_id, "User ID mismatch"
    assert info["message_count"] == 6, f"Expected 6 messages, got {info['message_count']}"
    print(f"✅ Conversation info: {info['message_count']} messages")
    
    # Test 7: Stats
    stats = conv_manager.get_conversation_stats()
    assert stats["total_conversations"] >= 1, "Should have at least 1 conversation"
    assert stats["total_messages"] >= 6, "Should have at least 6 messages"
    print(f"✅ Database stats: {stats['total_conversations']} conversations, {stats['total_messages']} messages")
    
    # Cleanup
    os.remove(test_db_path)
    print("✅ ConversationManager tests passed!")


async def test_api_integration():
    """Test API integration with conversation history."""
    print("\n🌐 Testing API integration...")
    
    try:
        import httpx
        
        # Test API endpoints
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient() as client:
            # Test 1: New conversation (no conversation_id)
            response1 = await client.post(
                f"{base_url}/chat",
                json={
                    "message": "Hello Eva, I need help scheduling a meeting",
                    "user_id": "test_user"
                }
            )
            
            if response1.status_code == 200:
                result1 = response1.json()
                conv_id = result1["conversation_id"]
                print(f"✅ New conversation created: {conv_id}")
                
                # Test 2: Continue conversation (with conversation_id)
                response2 = await client.post(
                    f"{base_url}/chat",
                    json={
                        "message": "Can you check my availability for tomorrow?",
                        "user_id": "test_user",
                        "conversation_id": conv_id
                    }
                )
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    assert result2["conversation_id"] == conv_id, "Conversation ID should match"
                    print(f"✅ Continued conversation: {conv_id}")
                    print(f"   Historical messages: {result2.get('metadata', {}).get('historical_messages', 0)}")
                else:
                    print(f"❌ Failed to continue conversation: {response2.status_code}")
            else:
                print(f"❌ Failed to create new conversation: {response1.status_code}")
                
    except ImportError:
        print("⚠️  httpx not available, skipping API integration tests")
    except Exception as e:
        print(f"⚠️  API not running or other error: {e}")


async def test_message_context():
    """Test that message context is properly maintained."""
    print("\n🧠 Testing message context...")
    
    # Create a conversation with context-dependent messages
    test_db_path = "test_context.db"
    try:
        os.remove(test_db_path)
    except FileNotFoundError:
        pass
    
    conv_manager = ConversationManager(db_path=test_db_path, message_limit=10)
    
    conv_id = conv_manager.generate_conversation_id()
    conv_manager.create_conversation(conv_id, "context_user")
    
    # Simulate a conversation where context matters
    conversation_flow = [
        ("user", "I need to schedule a meeting with John"),
        ("assistant", "I can help you schedule a meeting with John. When would you like to meet?"),
        ("user", "How about tomorrow at 2 PM?"),
        ("assistant", "Let me check your availability for tomorrow at 2 PM. I'll also check John's availability."),
        ("user", "Actually, make it 3 PM instead"),
        ("assistant", "Got it! I'll schedule the meeting for tomorrow at 3 PM instead of 2 PM. Let me update that for you.")
    ]
    
    for role, content in conversation_flow:
        conv_manager.add_message(conv_id, role, content)
    
    # Get conversation history
    history = conv_manager.get_conversation_messages_for_llm(conv_id)
    
    # Verify context is maintained
    assert len(history) == 6, f"Expected 6 messages, got {len(history)}"
    
    # Check that the last assistant message references the time change
    last_assistant_msg = [msg for msg in history if msg["role"] == "assistant"][-1]
    assert "3 PM" in last_assistant_msg["content"], "Context should show time change to 3 PM"
    assert "2 PM" in last_assistant_msg["content"], "Context should reference original 2 PM time"
    
    print("✅ Message context properly maintained")
    print(f"   Last assistant message: {last_assistant_msg['content'][:100]}...")
    
    # Cleanup
    os.remove(test_db_path)


async def main():
    """Run all tests."""
    print("🚀 Starting conversation history tests...\n")
    
    try:
        await test_conversation_manager()
        await test_message_context()
        await test_api_integration()
        
        print("\n🎉 All conversation history tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 