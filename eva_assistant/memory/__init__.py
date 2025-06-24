"""
Memory and learning package for Eva Assistant.

This package handles:
- Conversation memory and context with SQLite persistence
- User preference learning
- Attendee context tracking
- Vector storage with Chroma
"""

from eva_assistant.memory.conversation import ConversationManager

__all__ = ["ConversationManager"] 