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
    auto_select_primary: bool = Field(False, description="Automatically select primary calendar without prompting")


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


class UserStatusRequest(BaseModel):
    """Request to get user authentication status."""
    user_id: str = Field(..., description="User identifier")


class UserStatusResponse(BaseModel):
    """Response with user authentication status."""
    user_id: str = Field(..., description="User identifier")
    connected: bool = Field(..., description="Whether user calendar is connected")
    auth_status: Dict[str, Any] = Field(..., description="Detailed authentication status")
    calendars_count: Optional[int] = Field(None, description="Number of connected calendars")


class ListUsersResponse(BaseModel):
    """Response with list of connected users."""
    connected_users: List[str] = Field(..., description="List of connected user IDs")
    count: int = Field(..., description="Total number of connected users")


class UpdateCalendarSelectionRequest(BaseModel):
    """Request to update user's calendar selection."""
    user_id: str = Field(..., description="User identifier")


class UpdateCalendarSelectionResponse(BaseModel):
    """Response for calendar selection update."""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Status message")
    selected_calendars: Optional[List[Dict[str, Any]]] = Field(None, description="Updated calendar selection")
    total_calendars: Optional[int] = Field(None, description="Total available calendars")
    selected_count: Optional[int] = Field(None, description="Number of selected calendars")


class GetCalendarInfoRequest(BaseModel):
    """Request to get user's calendar info."""
    user_id: str = Field(..., description="User identifier")


class GetCalendarInfoResponse(BaseModel):
    """Response with user's calendar information."""
    user_id: str = Field(..., description="User identifier")
    connected: bool = Field(..., description="Whether user calendar is connected")
    has_calendar_selection: bool = Field(..., description="Whether user has made calendar selection")
    selected_calendar_count: int = Field(..., description="Number of selected calendars")
    selected_calendar_ids: List[str] = Field(..., description="List of selected calendar IDs")
    message: Optional[str] = Field(None, description="Additional info message")


class StreamChatRequest(BaseModel):
    """Schema for streaming chat requests."""
    message: str = Field(..., description="User message")
    user_id: str = Field(default="default", description="User identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")


# Timezone management schemas

class SetTimezoneRequest(BaseModel):
    """Schema for setting user timezone."""
    user_id: str = Field(..., description="User identifier")
    timezone: str = Field(..., description="Timezone string (e.g., 'America/New_York', 'UTC')")


class TimezoneResponse(BaseModel):
    """Schema for timezone responses."""
    success: bool = Field(..., description="Whether the operation was successful")
    user_id: str = Field(..., description="User identifier")
    timezone: str = Field(..., description="User's timezone")
    current_time: Optional[str] = Field(None, description="Current time in user's timezone")
    message: Optional[str] = Field(None, description="Success or error message")


class UserProfileResponse(BaseModel):
    """Schema for user profile responses."""
    user_id: str = Field(..., description="User identifier")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    display_name: Optional[str] = Field(None, description="User's display name")
    email: Optional[str] = Field(None, description="User's email address")
    timezone: str = Field(..., description="User's timezone")
    created_at: str = Field(..., description="Profile creation timestamp")
    updated_at: str = Field(..., description="Profile last update timestamp")
    current_time: Optional[str] = Field(None, description="Current time in user's timezone")


class AvailableTimezonesResponse(BaseModel):
    """Schema for available timezones response."""
    common_timezones: List[Dict[str, str]] = Field(..., description="List of common timezones with current time")
    total_available: int = Field(..., description="Total number of available timezones")


# User name management schemas

class SetUserNameRequest(BaseModel):
    """Schema for setting user name."""
    user_id: str = Field(..., description="User identifier")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    display_name: Optional[str] = Field(None, description="User's display name")
    email: Optional[str] = Field(None, description="User's email address")


class UserNameResponse(BaseModel):
    """Schema for user name responses."""
    success: bool = Field(..., description="Whether the operation was successful")
    user_id: str = Field(..., description="User identifier")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    display_name: Optional[str] = Field(None, description="User's display name")
    email: Optional[str] = Field(None, description="User's email address")
    message: Optional[str] = Field(None, description="Success or error message") 