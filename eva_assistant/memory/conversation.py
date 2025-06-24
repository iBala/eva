"""
Conversation Memory Management for Eva Assistant.

Handles conversation persistence, message threading, and history retrieval
using SQLite for semi-permanent storage.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation history and persistence using SQLite.
    
    Features:
    - Global conversation IDs (not per-user)
    - Message threading with proper ordering
    - Configurable message history limits
    - Semi-permanent storage with no automatic cleanup
    - JSON metadata support for rich message context
    """
    
    def __init__(self, db_path: str = "data/conversations.db", message_limit: int = 10):
        """
        Initialize conversation manager.
        
        Args:
            db_path: Path to SQLite database file
            message_limit: Maximum number of historical messages to include in context
        """
        self.db_path = Path(db_path)
        self.message_limit = message_limit
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"ConversationManager initialized with db: {self.db_path}, message_limit: {message_limit}")
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with self._get_db() as conn:
            # Conversations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    tool_calls TEXT DEFAULT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                        ON DELETE CASCADE
                )
            """)
            
            # Indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_timestamp 
                ON messages (conversation_id, timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_updated 
                ON conversations (user_id, updated_at DESC)
            """)
            
            conn.commit()
            logger.info("Database tables initialized successfully")
    
    @contextmanager
    def _get_db(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def generate_conversation_id(self) -> str:
        """Generate a unique global conversation ID."""
        return str(uuid.uuid4())
    
    def create_conversation(self, conversation_id: str, user_id: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            user_id: User who owns the conversation
            metadata: Optional conversation metadata
            
        Returns:
            True if created successfully, False if already exists
        """
        try:
            with self._get_db() as conn:
                conn.execute("""
                    INSERT INTO conversations (conversation_id, user_id, metadata)
                    VALUES (?, ?, ?)
                """, (conversation_id, user_id, json.dumps(metadata or {})))
                conn.commit()
                
                logger.info(f"Created conversation {conversation_id} for user {user_id}")
                return True
                
        except sqlite3.IntegrityError:
            logger.debug(f"Conversation {conversation_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to create conversation {conversation_id}: {e}")
            return False
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists."""
        with self._get_db() as conn:
            cursor = conn.execute("""
                SELECT 1 FROM conversations WHERE conversation_id = ?
            """, (conversation_id,))
            return cursor.fetchone() is not None
    
    def get_conversation_info(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation metadata and info."""
        with self._get_db() as conn:
            cursor = conn.execute("""
                SELECT conversation_id, user_id, created_at, updated_at, 
                       metadata, message_count
                FROM conversations 
                WHERE conversation_id = ?
            """, (conversation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "conversation_id": row["conversation_id"],
                "user_id": row["user_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "metadata": json.loads(row["metadata"]),
                "message_count": row["message_count"]
            }
    
    def add_message(self, conversation_id: str, role: str, content: str,
                   metadata: Optional[Dict[str, Any]] = None,
                   tool_calls: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation to add message to
            role: Message role ('user', 'assistant', 'system', 'tool')
            content: Message content
            metadata: Optional message metadata
            tool_calls: Optional tool calls data
            
        Returns:
            True if added successfully
        """
        try:
            with self._get_db() as conn:
                # Add the message
                conn.execute("""
                    INSERT INTO messages (conversation_id, role, content, metadata, tool_calls)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    conversation_id, 
                    role, 
                    content, 
                    json.dumps(metadata or {}),
                    json.dumps(tool_calls) if tool_calls else None
                ))
                
                # Update conversation updated_at and message_count
                conn.execute("""
                    UPDATE conversations 
                    SET updated_at = CURRENT_TIMESTAMP,
                        message_count = message_count + 1
                    WHERE conversation_id = ?
                """, (conversation_id,))
                
                conn.commit()
                
                logger.debug(f"Added {role} message to conversation {conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str, 
                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation message history.
        
        Args:
            conversation_id: Conversation to retrieve
            limit: Maximum number of messages to return (defaults to self.message_limit)
            
        Returns:
            List of messages in chronological order
        """
        if limit is None:
            limit = self.message_limit
        
        with self._get_db() as conn:
            cursor = conn.execute("""
                SELECT id, role, content, timestamp, metadata, tool_calls
                FROM messages 
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (conversation_id, limit))
            
            messages = []
            for row in reversed(cursor.fetchall()):  # Reverse to get chronological order
                message = {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"])
                }
                
                if row["tool_calls"]:
                    message["tool_calls"] = json.loads(row["tool_calls"])
                
                messages.append(message)
            
            logger.debug(f"Retrieved {len(messages)} messages from conversation {conversation_id}")
            return messages
    
    def get_conversation_messages_for_llm(self, conversation_id: str,
                                        limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get conversation messages formatted for LLM context.
        
        Args:
            conversation_id: Conversation to retrieve
            limit: Maximum number of messages to return
            
        Returns:
            List of messages in LLM format: [{"role": "user", "content": "..."}]
        """
        messages = self.get_conversation_history(conversation_id, limit)
        
        llm_messages = []
        for msg in messages:
            llm_message = {
                "role": msg["role"],
                "content": msg["content"]
            }
            
            # Add tool_calls if present (for assistant messages)
            if msg.get("tool_calls"):
                llm_message["tool_calls"] = msg["tool_calls"]
            
            llm_messages.append(llm_message)
        
        return llm_messages
    
    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User to get conversations for
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation info ordered by most recent
        """
        with self._get_db() as conn:
            cursor = conn.execute("""
                SELECT conversation_id, created_at, updated_at, metadata, message_count
                FROM conversations 
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    "conversation_id": row["conversation_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "metadata": json.loads(row["metadata"]),
                    "message_count": row["message_count"]
                })
            
            return conversations
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            conversation_id: Conversation to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            with self._get_db() as conn:
                cursor = conn.execute("""
                    DELETE FROM conversations WHERE conversation_id = ?
                """, (conversation_id,))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted conversation {conversation_id}")
                else:
                    logger.warning(f"Conversation {conversation_id} not found for deletion")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_db() as conn:
            # Total conversations
            cursor = conn.execute("SELECT COUNT(*) as count FROM conversations")
            total_conversations = cursor.fetchone()["count"]
            
            # Total messages
            cursor = conn.execute("SELECT COUNT(*) as count FROM messages")
            total_messages = cursor.fetchone()["count"]
            
            # Recent activity (last 24 hours)
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM conversations 
                WHERE updated_at > datetime('now', '-1 day')
            """)
            recent_conversations = cursor.fetchone()["count"]
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "recent_conversations": recent_conversations,
                "message_limit": self.message_limit,
                "db_path": str(self.db_path)
            } 