"""
Pydantic schemas for Eva Assistant API.

Defines request and response models for the FastAPI endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message to Eva")
    user_id: str = Field(default="founder", description="User identifier")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Eva's response")
    conversation_id: str = Field(..., description="Conversation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class StreamChunk(BaseModel):
    """Individual chunk in streaming response."""
    content: str = Field(..., description="Chunk content")
    type: str = Field(default="text", description="Chunk type: text, tool_call, tool_result")
    conversation_id: str = Field(..., description="Conversation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0", description="API version")
    eva_status: str = Field(..., description="Eva's authentication status")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    conversation_id: Optional[str] = Field(None, description="Conversation ID if applicable")


class ConnectCalendarRequest(BaseModel):
    """Request to connect user calendar."""
    user_id: str = Field(..., description="User identifier")


class ConnectCalendarResponse(BaseModel):
    """Response for calendar connection."""
    success: bool = Field(..., description="Connection success status")
    message: str = Field(..., description="Status message")
    user_info: Optional[Dict[str, Any]] = Field(None, description="Connected user info")
    calendars: Optional[List[Dict[str, Any]]] = Field(None, description="Connected calendars")


class DisconnectCalendarRequest(BaseModel):
    """Request to disconnect user calendar."""
    user_id: str = Field(..., description="User identifier")


class DisconnectCalendarResponse(BaseModel):
    """Response for calendar disconnection."""
    success: bool = Field(..., description="Disconnection success status")
    message: str = Field(..., description="Status message") 