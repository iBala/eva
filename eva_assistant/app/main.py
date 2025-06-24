"""
FastAPI application for Eva Assistant.

Provides REST API endpoints for:
- Chat interactions with Eva
- Streaming responses
- User calendar connections
- Health checks
"""

import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

from eva_assistant.app.schemas import (
    ChatRequest, ChatResponse, StreamChunk, HealthResponse, ErrorResponse,
    ConnectCalendarRequest, ConnectCalendarResponse,
    DisconnectCalendarRequest, DisconnectCalendarResponse,
    UserStatusRequest, UserStatusResponse, ListUsersResponse,
    UpdateCalendarSelectionRequest, UpdateCalendarSelectionResponse,
    GetCalendarInfoRequest, GetCalendarInfoResponse,
    SetTimezoneRequest, TimezoneResponse, UserProfileResponse,
    AvailableTimezonesResponse
)
from eva_assistant.auth.user_auth import UserAuthManager
from eva_assistant.auth.eva_auth import EvaAuthManager
from eva_assistant.config import settings, get_eva_oauth_config
from eva_assistant.agent.graph import get_eva_graph
from eva_assistant.memory.conversation import ConversationManager  # NEW: Add conversation management

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting Eva Assistant API...")
    
    # Initialize ConversationManager - NEW: Add conversation persistence
    try:
        conversation_manager = ConversationManager(
            db_path=settings.conversation_db_path,
            message_limit=settings.conversation_message_limit
        )
        app.state.conversation_manager = conversation_manager
        logger.info("✅ ConversationManager initialized successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize ConversationManager: {e}")
        # Continue without conversation management
    
    # Initialize LangGraph agent
    try:
        eva_graph = get_eva_graph()
        logger.info("✅ Eva LangGraph agent initialized successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Eva agent: {e}")
        # Continue without agent - will use mock responses
    
    logger.info("✅ Eva Assistant API started successfully!")
    yield
    logger.info("🛑 Shutting down Eva Assistant API...")


# Create FastAPI app
app = FastAPI(
    title="Eva Assistant API",
    description="AI Executive Assistant for Meeting Scheduling and Calendar Management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_conversation_id() -> str:
    """Generate a unique conversation ID."""
    return str(uuid.uuid4())


async def eva_response(message: str, user_id: str, conversation_id: str = None, 
                      conversation_history: list = None) -> str:
    """
    Get Eva's response using the new LLM agent with conversation history.
    
    Args:
        message: User message
        user_id: User identifier
        conversation_id: Conversation ID (optional, used for logging)
        conversation_history: Historical messages for context
        
    Returns:
        Eva's response
    """
    try:
        # Use the new LLM agent through the graph with conversation history
        eva_graph = get_eva_graph()
        result = await eva_graph.process_message(
            message, 
            user_id, 
            conversation_id=conversation_id,
            conversation_history=conversation_history or []
        )
        
        logger.info(f"Eva processed message successfully: {len(result.get('tool_calls', []))} tool calls")
        return result.get("response", "I apologize, but I'm having trouble processing your request right now.")
        
    except Exception as e:
        logger.error(f"Eva agent error: {e}")
        
        # Fallback to mock response
        logger.info(f"Using fallback response for: {message}")
        
        if "meeting" in message.lower() or "schedule" in message.lower():
            return f"I can help you schedule a meeting! To proceed, I'll need to check your calendar availability. Would you like me to find a suitable time slot?"
        elif "calendar" in message.lower():
            return f"I can access your calendar to check availability and schedule meetings. What would you like me to help you with?"
        elif "hello" in message.lower() or "hi" in message.lower():
            return f"Hello! I'm Eva, your AI executive assistant. I can help you schedule meetings, check calendar availability, and manage your email communications. What can I assist you with today?"
        else:
            return f"I understand you'd like help with: {message}. As your executive assistant, I can help with meeting scheduling, calendar management, and email coordination. Could you provide more details about what you need?"


async def eva_stream(message: str, user_id: str, conversation_id: str, 
                    conversation_history: list = None) -> AsyncGenerator[StreamChunk, None]:
    """
    Stream Eva's response using the new LLM agent.
    
    Args:
        message: User message
        user_id: User identifier
        conversation_id: Conversation ID
        
    Yields:
        StreamChunk: Individual response chunks
    """
    try:
        # Use the new LLM agent streaming with conversation history
        eva_graph = get_eva_graph()
        
        async for chunk in eva_graph.stream_message(message, user_id, conversation_id, conversation_history):
            if chunk.get("type") == "content":
                # Stream content as it comes
                yield StreamChunk(
                    content=chunk.get("content", ""),
                    type="text",
                    conversation_id=conversation_id
                )
            elif chunk.get("type") == "tool_execution":
                # Send tool execution updates
                yield StreamChunk(
                    content=chunk.get("message", "Processing..."),
                    type="progress",
                    conversation_id=conversation_id
                )
            elif chunk.get("type") == "final_response":
                # Send final response with tool results
                response = chunk.get("content", "")
                tool_calls = chunk.get("tool_calls", [])
                
                # Stream the final response
                words = response.split()
                current_chunk = ""
                
                for i, word in enumerate(words):
                    current_chunk += word + " "
                    
                    # Send chunk every 4 words or at the end
                    if (i + 1) % 4 == 0 or i == len(words) - 1:
                        yield StreamChunk(
                            content=current_chunk.strip(),
                            type="text",
                            conversation_id=conversation_id,
                            metadata={"tool_calls": len(tool_calls)} if i == len(words) - 1 else {}
                        )
                        current_chunk = ""
            elif chunk.get("type") == "error":
                yield StreamChunk(
                    content=f"Error: {chunk.get('content', 'Unknown error')}",
                    type="error",
                    conversation_id=conversation_id
                )
    
    except Exception as e:
        logger.error(f"Eva streaming error: {e}")
        
        # Fallback to simple response
        response = await eva_response(message, user_id, conversation_id)
        words = response.split()
        current_chunk = ""
        
        for i, word in enumerate(words):
            current_chunk += word + " "
            
            if (i + 1) % 4 == 0 or i == len(words) - 1:
                yield StreamChunk(
                    content=current_chunk.strip(),
                    type="text",
                    conversation_id=conversation_id
                )
                current_chunk = ""


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check Eva's authentication status using new auth manager
        eva_auth = EvaAuthManager()
        eva_status_info = eva_auth.get_auth_status()
        eva_status = "authenticated" if eva_status_info["has_token_file"] and eva_status_info["credentials_valid"] else "not_authenticated"
        
        return HealthResponse(
            status="healthy",
            eva_status=eva_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Enhanced Chat with Eva - synchronous response with conversation history.
    
    Args:
        request: Chat request containing user message and optional conversation_id
        
    Returns:
        ChatResponse: Eva's response with conversation persistence
    """
    try:
        # Get conversation manager
        conversation_manager = getattr(app.state, 'conversation_manager', None)
        if not conversation_manager:
            logger.warning("ConversationManager not available, using basic response")
            conversation_id = request.conversation_id or generate_conversation_id()
            response = await eva_response(request.message, request.user_id, conversation_id)
            return ChatResponse(
                response=response,
                conversation_id=conversation_id,
                metadata={"user_id": request.user_id}
            )
        
        # Handle conversation ID
        conversation_id = request.conversation_id
        is_new_conversation = conversation_id is None
        
        if is_new_conversation:
            # Generate new conversation ID
            conversation_id = conversation_manager.generate_conversation_id()
            
            # Create new conversation
            conversation_manager.create_conversation(
                conversation_id=conversation_id,
                user_id=request.user_id,
                metadata={"created_via": "chat_api"}
            )
            logger.info(f"Created new conversation {conversation_id} for user {request.user_id}")
        else:
            # Verify conversation exists
            if not conversation_manager.conversation_exists(conversation_id):
                logger.warning(f"Conversation {conversation_id} not found, creating new one")
                conversation_manager.create_conversation(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    metadata={"created_via": "chat_api"}
                )
        
        # Get conversation history for context (if not a new conversation)
        conversation_history = []
        if not is_new_conversation:
            conversation_history = conversation_manager.get_conversation_messages_for_llm(conversation_id)
            logger.info(f"Loaded {len(conversation_history)} historical messages for conversation {conversation_id}")
        
        logger.info(f"Chat request from {request.user_id}: {request.message} (conversation: {conversation_id})")
        
        # Add user message to conversation
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
            metadata={"timestamp": datetime.utcnow().isoformat()}
        )
        
        # Use LangGraph agent for response with conversation history
        response = await eva_response(
            message=request.message, 
            user_id=request.user_id, 
            conversation_id=conversation_id,
            conversation_history=conversation_history
        )
        
        # Add assistant response to conversation
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
            metadata={"timestamp": datetime.utcnow().isoformat()}
        )
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            metadata={
                "user_id": request.user_id,
                "is_new_conversation": is_new_conversation,
                "historical_messages": len(conversation_history)
            }
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error",
                code="CHAT_ERROR"
            ).dict()
        )


@app.post("/stream")
async def stream_chat(request: ChatRequest):
    """
    Enhanced Chat with Eva - streaming response with conversation history.
    
    Args:
        request: Chat request containing user message and optional conversation_id
        
    Returns:
        StreamingResponse: Server-sent events with Eva's response chunks and conversation persistence
    """
    try:
        # Get conversation manager
        conversation_manager = getattr(app.state, 'conversation_manager', None)
        
        # Handle conversation ID
        conversation_id = request.conversation_id
        is_new_conversation = conversation_id is None
        
        if is_new_conversation:
            conversation_id = generate_conversation_id()
            if conversation_manager:
                conversation_manager.create_conversation(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    metadata={"created_via": "stream_api"}
                )
        
        # Get conversation history for context
        conversation_history = []
        if conversation_manager and not is_new_conversation:
            conversation_history = conversation_manager.get_conversation_messages_for_llm(conversation_id)
        
        logger.info(f"Stream request from {request.user_id}: {request.message} (conversation: {conversation_id}, history: {len(conversation_history)})")
        
        # Add user message to conversation if manager available
        if conversation_manager:
            conversation_manager.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata={"timestamp": datetime.utcnow().isoformat()}
            )
        
        async def generate_stream():
            assistant_response = ""
            try:
                # Use LangGraph agent for streaming with conversation history
                async for chunk in eva_stream(request.message, request.user_id, conversation_id, conversation_history):
                    # Collect assistant response for persistence
                    if chunk.type == "text":
                        assistant_response += chunk.content + " "
                    
                    yield f"data: {chunk.json()}\n\n"
                
                # Add assistant response to conversation if manager available
                if conversation_manager and assistant_response.strip():
                    conversation_manager.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=assistant_response.strip(),
                        metadata={"timestamp": datetime.utcnow().isoformat()}
                    )
                
                # Send end marker
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                error_chunk = StreamChunk(
                    content=f"Error: {str(e)}",
                    type="error",
                    conversation_id=conversation_id
                )
                yield f"data: {error_chunk.json()}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Stream error: {e}")
        raise HTTPException(status_code=500, detail="Stream generation failed")


@app.post("/calendar/connect", response_model=ConnectCalendarResponse)
async def connect_calendar(request: ConnectCalendarRequest):
    """
    Connect a user's calendar through OAuth.
    
    This endpoint initiates the OAuth flow for read-only calendar access.
    
    Args:
        request: Calendar connection request
        
    Returns:
        ConnectCalendarResponse: Connection result with user info
    """
    try:
        logger.info(f"Calendar connection request for user: {request.user_id}")
        
        # Use new user auth manager for calendar connection
        user_auth = UserAuthManager()
        user_info = await user_auth.connect_user_calendar(
            request.user_id, 
            auto_select_primary=request.auto_select_primary
        )
        
        return ConnectCalendarResponse(
            success=True,
            message=f"Successfully connected calendar for {request.user_id}",
            user_info=user_info,
            calendars=user_info.get("calendars", [])
        )
        
    except Exception as e:
        logger.error(f"Calendar connection error for {request.user_id}: {e}")
        return ConnectCalendarResponse(
            success=False,
            message=f"Failed to connect calendar: {str(e)}"
        )


@app.post("/calendar/disconnect", response_model=DisconnectCalendarResponse)
async def disconnect_calendar(request: DisconnectCalendarRequest):
    """
    Disconnect a user's calendar.
    
    This removes the user's calendar token and revokes access.
    
    Args:
        request: Calendar disconnection request
        
    Returns:
        DisconnectCalendarResponse: Disconnection result
    """
    try:
        logger.info(f"Calendar disconnection request for user: {request.user_id}")
        
        # Use new user auth manager for calendar disconnection
        user_auth = UserAuthManager()
        success = user_auth.disconnect_user_calendar(request.user_id)
        
        message = f"Successfully disconnected calendar for {request.user_id}" if success else f"No calendar connection found for {request.user_id}"
        
        return DisconnectCalendarResponse(
            success=success,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Calendar disconnection error for {request.user_id}: {e}")
        return DisconnectCalendarResponse(
            success=False,
            message=f"Failed to disconnect calendar: {str(e)}"
        )


@app.post("/calendar/status", response_model=UserStatusResponse)
async def get_user_status(request: UserStatusRequest):
    """
    Get user calendar authentication status.
    
    Args:
        request: User status request
        
    Returns:
        UserStatusResponse: User authentication status details
    """
    try:
        logger.info(f"Status request for user: {request.user_id}")
        
        user_auth = UserAuthManager()
        auth_status = user_auth.get_user_auth_status(request.user_id)
        connected = auth_status["has_valid_credentials"]
        
        # Get calendar count if connected
        calendars_count = None
        if connected:
            try:
                test_result = await user_auth.test_user_calendar_access(request.user_id)
                calendars_count = test_result.get("calendars_count", 0)
            except Exception as e:
                logger.warning(f"Could not get calendar count for {request.user_id}: {e}")
        
        return UserStatusResponse(
            user_id=request.user_id,
            connected=connected,
            auth_status=auth_status,
            calendars_count=calendars_count
        )
        
    except Exception as e:
        logger.error(f"Status check error for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user status: {str(e)}")


@app.get("/calendar/users", response_model=ListUsersResponse)
async def list_connected_users():
    """
    List all users who have connected their calendars.
    
    Returns:
        ListUsersResponse: List of connected user IDs
    """
    try:
        user_auth = UserAuthManager()
        connected_users = user_auth.list_connected_users()
        
        return ListUsersResponse(
            connected_users=connected_users,
            count=len(connected_users)
        )
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@app.post("/calendar/selection/update", response_model=UpdateCalendarSelectionResponse)
async def update_calendar_selection(request: UpdateCalendarSelectionRequest):
    """
    Update a user's calendar selection.
    
    This endpoint allows users to change which calendars Eva uses for availability checking.
    
    Args:
        request: Calendar selection update request
        
    Returns:
        UpdateCalendarSelectionResponse: Update result with selected calendars
    """
    try:
        logger.info(f"Calendar selection update request for user: {request.user_id}")
        
        user_auth = UserAuthManager()
        
        # Update calendar selection (this will prompt the user)
        result = await user_auth.update_user_calendar_selection(request.user_id)
        
        return UpdateCalendarSelectionResponse(
            success=True,
            message=f"Calendar selection updated for user {request.user_id}",
            selected_calendars=result.get('selected_calendars', []),
            total_calendars=result.get('total_calendars', 0),
            selected_count=result.get('selected_calendar_count', 0)
        )
    
    except Exception as e:
        logger.error(f"Failed to update calendar selection for {request.user_id}: {e}")
        return UpdateCalendarSelectionResponse(
            success=False,
            message=f"Failed to update calendar selection: {str(e)}",
            selected_calendars=None,
            total_calendars=None,
            selected_count=None
        )


@app.post("/calendar/info", response_model=GetCalendarInfoResponse)
async def get_calendar_info(request: GetCalendarInfoRequest):
    """
    Get information about a user's calendar connection and selection.
    
    Args:
        request: Calendar info request
        
    Returns:
        GetCalendarInfoResponse: Calendar connection and selection details
    """
    try:
        logger.info(f"Calendar info request for user: {request.user_id}")
        
        user_auth = UserAuthManager()
        info = user_auth.get_user_calendar_info(request.user_id)
        
        return GetCalendarInfoResponse(
            user_id=info['user_id'],
            connected=info['connected'],
            has_calendar_selection=info.get('has_calendar_selection', False),
            selected_calendar_count=info.get('selected_calendar_count', 0),
            selected_calendar_ids=info.get('selected_calendar_ids', []),
            message=info.get('message')
        )
    
    except Exception as e:
        logger.error(f"Failed to get calendar info for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get calendar info: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Eva Assistant API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "stream": "/stream",
            "connect_calendar": "/calendar/connect",
            "disconnect_calendar": "/calendar/disconnect",
            "user_status": "/calendar/status",
            "list_users": "/calendar/users",
            "update_calendar_selection": "/calendar/selection/update",
            "calendar_info": "/calendar/info",
            "docs": "/docs"
        }
    }


# Timezone Management Endpoints

@app.post("/user/timezone", response_model=TimezoneResponse)
async def set_user_timezone(request: SetTimezoneRequest) -> TimezoneResponse:
    """
    Set a user's timezone preference.
    
    Args:
        request: Set timezone request with user_id and timezone
        
    Returns:
        TimezoneResponse with success status and current time
    """
    try:
        user_auth = UserAuthManager()
        
        success = user_auth.set_user_timezone(request.user_id, request.timezone)
        
        if success:
            # Get current time in user's timezone
            import pytz
            from datetime import datetime
            
            try:
                zone = pytz.timezone(request.timezone)
                current_time = datetime.now(zone).strftime('%Y-%m-%d %H:%M:%S %Z')
            except Exception:
                current_time = None
            
            return TimezoneResponse(
                success=True,
                user_id=request.user_id,
                timezone=request.timezone,
                current_time=current_time,
                message=f"Timezone successfully set to {request.timezone}"
            )
        else:
            return TimezoneResponse(
                success=False,
                user_id=request.user_id,
                timezone=request.timezone,
                message="Failed to set timezone. Please check the timezone format."
            )
            
    except Exception as e:
        logger.error(f"Set timezone error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/timezone", response_model=TimezoneResponse)
async def get_user_timezone(user_id: str) -> TimezoneResponse:
    """
    Get a user's timezone preference.
    
    Args:
        user_id: User identifier
        
    Returns:
        TimezoneResponse with user's timezone and current time
    """
    try:
        user_auth = UserAuthManager()
        
        timezone = user_auth.get_user_timezone(user_id)
        
        # Get current time in user's timezone
        import pytz
        from datetime import datetime
        
        try:
            zone = pytz.timezone(timezone)
            current_time = datetime.now(zone).strftime('%Y-%m-%d %H:%M:%S %Z')
        except Exception:
            current_time = None
        
        return TimezoneResponse(
            success=True,
            user_id=user_id,
            timezone=timezone,
            current_time=current_time,
            message=f"User timezone: {timezone}"
        )
        
    except Exception as e:
        logger.error(f"Get timezone error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str) -> UserProfileResponse:
    """
    Get a user's complete profile including timezone.
    
    Args:
        user_id: User identifier
        
    Returns:
        UserProfileResponse with user's profile data
    """
    try:
        user_auth = UserAuthManager()
        
        profile = user_auth.get_user_profile(user_id)
        
        # Get current time in user's timezone
        import pytz
        from datetime import datetime
        
        try:
            zone = pytz.timezone(profile['timezone'])
            current_time = datetime.now(zone).strftime('%Y-%m-%d %H:%M:%S %Z')
        except Exception:
            current_time = None
        
        return UserProfileResponse(
            user_id=profile['user_id'],
            timezone=profile['timezone'],
            created_at=profile['created_at'],
            updated_at=profile['updated_at'],
            current_time=current_time
        )
        
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/timezones", response_model=AvailableTimezonesResponse)
async def get_available_timezones() -> AvailableTimezonesResponse:
    """
    Get list of available timezones with current times.
    
    Returns:
        AvailableTimezonesResponse with common timezones and total count
    """
    try:
        import pytz
        from datetime import datetime
        
        # Common timezones for easy selection
        common_timezone_list = [
            'UTC',
            'US/Eastern',
            'US/Central', 
            'US/Mountain',
            'US/Pacific',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Asia/Kolkata',
            'Australia/Sydney',
            'America/New_York',
            'America/Chicago',
            'America/Denver',
            'America/Los_Angeles',
            'America/Toronto',
            'America/Vancouver'
        ]
        
        common_timezones = []
        for tz_name in common_timezone_list:
            try:
                zone = pytz.timezone(tz_name)
                current_time = datetime.now(zone).strftime('%Y-%m-%d %H:%M:%S %Z')
                common_timezones.append({
                    'timezone': tz_name,
                    'current_time': current_time,
                    'display_name': tz_name.replace('_', ' ')
                })
            except Exception:
                continue
        
        return AvailableTimezonesResponse(
            common_timezones=common_timezones,
            total_available=len(pytz.all_timezones)
        )
        
    except Exception as e:
        logger.error(f"Get timezones error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Working Hours Management Endpoints

@app.get("/user/{user_id}/working-hours")
async def get_user_working_hours(user_id: str):
    """Get user's working hours configuration."""
    try:
        user_auth = UserAuthManager()
        working_hours = user_auth.get_user_working_hours(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "working_hours": working_hours,
            "timezone": user_auth.get_user_timezone(user_id)
        }
    except Exception as e:
        logger.error(f"Failed to get working hours for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/{user_id}/working-hours")
async def set_user_working_hours(user_id: str, working_hours: dict):
    """
    Set user's working hours configuration.
    
    Expected format:
    {
        "monday": {"enabled": true, "start": "09:00", "end": "17:00"},
        "tuesday": {"enabled": true, "start": "09:00", "end": "17:00"},
        "wednesday": {"enabled": true, "start": "09:00", "end": "17:00"},
        "thursday": {"enabled": true, "start": "09:00", "end": "17:00"},
        "friday": {"enabled": true, "start": "09:00", "end": "17:00"},
        "saturday": {"enabled": false, "start": "09:00", "end": "17:00"},
        "sunday": {"enabled": false, "start": "09:00", "end": "17:00"}
    }
    """
    try:
        # Validate working hours format
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day in days:
            if day not in working_hours:
                raise HTTPException(status_code=400, detail=f"Missing day: {day}")
            
            day_config = working_hours[day]
            if not isinstance(day_config, dict):
                raise HTTPException(status_code=400, detail=f"Invalid format for {day}")
            
            required_fields = ['enabled', 'start', 'end']
            for field in required_fields:
                if field not in day_config:
                    raise HTTPException(status_code=400, detail=f"Missing field '{field}' for {day}")
            
            # Validate time format (HH:MM)
            if day_config['enabled']:
                try:
                    from datetime import datetime
                    datetime.strptime(day_config['start'], '%H:%M')
                    datetime.strptime(day_config['end'], '%H:%M')
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid time format for {day}. Use HH:MM format.")
        
        user_auth = UserAuthManager()
        success = user_auth.set_user_working_hours(user_id, working_hours)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save working hours")
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "Working hours updated successfully",
            "working_hours": working_hours,
            "timezone": user_auth.get_user_timezone(user_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set working hours for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/availability/{date}")
async def get_user_availability_for_date(user_id: str, date: str):
    """
    Get user's availability for a specific date based on their working hours.
    
    Args:
        user_id: User identifier
        date: Date in YYYY-MM-DD format
    """
    try:
        # Validate date format
        from datetime import datetime
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")
        
        user_auth = UserAuthManager()
        availability = user_auth.get_user_availability_for_date(user_id, date)
        
        return {
            "success": True,
            "user_id": user_id,
            "availability": availability
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get availability for user {user_id} on {date}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/working-hours/examples")
async def get_working_hours_examples():
    """Get example working hours configurations for different scenarios."""
    return {
        "success": True,
        "examples": {
            "standard_business": {
                "name": "Standard Business Hours (9 AM - 5 PM, Mon-Fri)",
                "working_hours": {
                    "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "thursday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "friday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "saturday": {"enabled": False, "start": "09:00", "end": "17:00"},
                    "sunday": {"enabled": False, "start": "09:00", "end": "17:00"}
                }
            },
            "flexible_schedule": {
                "name": "Flexible Schedule (10 AM - 6 PM, Mon-Fri)",
                "working_hours": {
                    "monday": {"enabled": True, "start": "10:00", "end": "18:00"},
                    "tuesday": {"enabled": True, "start": "10:00", "end": "18:00"},
                    "wednesday": {"enabled": True, "start": "10:00", "end": "18:00"},
                    "thursday": {"enabled": True, "start": "10:00", "end": "18:00"},
                    "friday": {"enabled": True, "start": "10:00", "end": "18:00"},
                    "saturday": {"enabled": False, "start": "10:00", "end": "18:00"},
                    "sunday": {"enabled": False, "start": "10:00", "end": "18:00"}
                }
            },
            "six_day_week": {
                "name": "Six Day Week (9 AM - 5 PM, Mon-Sat)",
                "working_hours": {
                    "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "thursday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "friday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "saturday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "sunday": {"enabled": False, "start": "09:00", "end": "17:00"}
                }
            },
            "part_time": {
                "name": "Part Time (9 AM - 1 PM, Mon/Wed/Fri)",
                "working_hours": {
                    "monday": {"enabled": True, "start": "09:00", "end": "13:00"},
                    "tuesday": {"enabled": False, "start": "09:00", "end": "13:00"},
                    "wednesday": {"enabled": True, "start": "09:00", "end": "13:00"},
                    "thursday": {"enabled": False, "start": "09:00", "end": "13:00"},
                    "friday": {"enabled": True, "start": "09:00", "end": "13:00"},
                    "saturday": {"enabled": False, "start": "09:00", "end": "13:00"},
                    "sunday": {"enabled": False, "start": "09:00", "end": "13:00"}
                }
            }
        },
        "format_notes": {
            "time_format": "HH:MM (24-hour format)",
            "enabled": "Boolean - whether the user is available on this day",
            "start": "Start time of availability",
            "end": "End time of availability",
            "timezone": "All times are in the user's local timezone"
        }
    }


# Email Management Endpoints

@app.get("/user/{user_id}/emails")
async def get_user_emails(user_id: str):
    """Get all email addresses owned by a user."""
    try:
        user_auth = UserAuthManager()
        mapping = user_auth.get_user_email_mapping(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "primary_email": mapping.get("primary_email"),
            "owned_emails": mapping.get("owned_emails", []),
            "email_count": len(mapping.get("owned_emails", [])),
            "created_at": mapping.get("created_at"),
            "updated_at": mapping.get("updated_at")
        }
    except Exception as e:
        logger.error(f"Failed to get emails for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/{user_id}/emails/{email}/set-primary")
async def set_primary_email(user_id: str, email: str):
    """Set an email as the primary email for a user."""
    try:
        user_auth = UserAuthManager()
        success = user_auth.set_primary_email_for_user(user_id, email)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Cannot set {email} as primary - email not owned by user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "primary_email": email,
            "message": f"Primary email set to {email} for user {user_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set primary email {email} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/email/{email}/user")
async def find_user_for_email(email: str):
    """Find which user_id owns a specific email address."""
    try:
        user_auth = UserAuthManager()
        user_id = user_auth.find_user_id_for_email(email)
        
        if not user_id:
            return {
                "success": False,
                "email": email,
                "user_id": None,
                "connected": False,
                "message": f"Calendar not connected for email {email}"
            }
        
        # Get additional user info
        mapping = user_auth.get_user_email_mapping(user_id)
        is_primary = mapping.get("primary_email") == email
        
        return {
            "success": True,
            "email": email,
            "user_id": user_id,
            "connected": True,
            "is_primary": is_primary,
            "user_timezone": user_auth.get_user_timezone(user_id),
            "total_emails": len(mapping.get("owned_emails", []))
        }
    except Exception as e:
        logger.error(f"Failed to find user for email {email}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/emails/connected")
async def list_all_connected_emails():
    """List all connected email addresses across all users."""
    try:
        user_auth = UserAuthManager()
        connected_users = user_auth.list_connected_users()
        
        all_emails = []
        for user_id in connected_users:
            mapping = user_auth.get_user_email_mapping(user_id)
            owned_emails = mapping.get("owned_emails", [])
            primary_email = mapping.get("primary_email")
            user_timezone = user_auth.get_user_timezone(user_id)
            
            for email in owned_emails:
                all_emails.append({
                    "email": email,
                    "user_id": user_id,
                    "is_primary": email == primary_email,
                    "user_timezone": user_timezone,
                    "connected": user_auth.has_any_connected_calendars(user_id)
                })
        
        return {
            "success": True,
            "connected_emails": all_emails,
            "total_emails": len(all_emails),
            "total_users": len(connected_users)
        }
    except Exception as e:
        logger.error(f"Failed to list connected emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/user/{user_id}/emails/{email}")
async def remove_email_from_user(user_id: str, email: str):
    """Remove an email address from a user's owned emails."""
    try:
        user_auth = UserAuthManager()
        
        # Check if email is owned by this user
        mapping = user_auth.get_user_email_mapping(user_id)
        if email not in mapping.get("owned_emails", []):
            raise HTTPException(status_code=404, detail=f"Email {email} not owned by user {user_id}")
        
        success = user_auth.remove_email_from_user(user_id, email)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to remove email {email} from user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "removed_email": email,
            "message": f"Email {email} removed from user {user_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove email {email} from user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# NEW: Conversation Management Endpoints

@app.get("/conversations/stats")
async def get_conversation_stats():
    """Get conversation database statistics."""
    try:
        conversation_manager = getattr(app.state, 'conversation_manager', None)
        if not conversation_manager:
            raise HTTPException(status_code=503, detail="ConversationManager not available")
        
        stats = conversation_manager.get_conversation_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get conversation stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/user/{user_id}/conversations")
async def get_user_conversations(user_id: str, limit: int = 20):
    """Get all conversations for a user."""
    try:
        conversation_manager = getattr(app.state, 'conversation_manager', None)
        if not conversation_manager:
            raise HTTPException(status_code=503, detail="ConversationManager not available")
        
        conversations = conversation_manager.get_user_conversations(user_id, limit)
        return {
            "success": True,
            "user_id": user_id,
            "conversations": conversations,
            "count": len(conversations)
        }
    except Exception as e:
        logger.error(f"Failed to get conversations for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")


@app.get("/conversations/{conversation_id}")
async def get_conversation_details(conversation_id: str, include_messages: bool = True):
    """Get conversation details and optionally messages."""
    try:
        conversation_manager = getattr(app.state, 'conversation_manager', None)
        if not conversation_manager:
            raise HTTPException(status_code=503, detail="ConversationManager not available")
        
        # Get conversation info
        info = conversation_manager.get_conversation_info(conversation_id)
        if not info:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        result = {
            "success": True,
            "conversation": info
        }
        
        # Include messages if requested
        if include_messages:
            messages = conversation_manager.get_conversation_history(conversation_id)
            result["messages"] = messages
            result["message_count"] = len(messages)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    try:
        conversation_manager = getattr(app.state, 'conversation_manager', None)
        if not conversation_manager:
            raise HTTPException(status_code=503, detail="ConversationManager not available")
        
        success = conversation_manager.delete_conversation(conversation_id)
        
        if success:
            return {
                "success": True,
                "message": f"Conversation {conversation_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "eva_assistant.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True if settings.environment == "development" else False,
        log_level=settings.log_level.lower()
    ) 