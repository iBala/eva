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
    DisconnectCalendarRequest, DisconnectCalendarResponse
)
from eva_assistant.auth.oauth_manager import oauth_manager
from eva_assistant.config import settings
from eva_assistant.agent.graph import get_eva_graph

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


async def eva_response(message: str, user_id: str, conversation_id: str) -> str:
    """
    Get Eva's response using the LangGraph agent.
    
    Args:
        message: User message
        user_id: User identifier
        conversation_id: Conversation ID
        
    Returns:
        Eva's response
    """
    try:
        # Use the LangGraph agent
        eva_graph = get_eva_graph()
        result = await eva_graph.process_message(message, user_id, conversation_id)
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


async def eva_stream(message: str, user_id: str, conversation_id: str) -> AsyncGenerator[StreamChunk, None]:
    """
    Stream Eva's response using the LangGraph agent.
    
    Args:
        message: User message
        user_id: User identifier
        conversation_id: Conversation ID
        
    Yields:
        StreamChunk: Individual response chunks
    """
    try:
        # Use the LangGraph agent streaming
        eva_graph = get_eva_graph()
        
        async for chunk in eva_graph.stream_message(message, user_id, conversation_id):
            if chunk.get("type") == "progress":
                # Send progress updates
                yield StreamChunk(
                    content=f"Processing: {chunk.get('node', 'unknown')}",
                    type="progress",
                    conversation_id=conversation_id,
                    metadata=chunk.get("metadata", {})
                )
            elif chunk.get("type") == "response":
                # Send final response in chunks
                response = chunk.get("response", "")
                words = response.split()
                current_chunk = ""
                
                for i, word in enumerate(words):
                    current_chunk += word + " "
                    
                    # Send chunk every 4 words or at the end
                    if (i + 1) % 4 == 0 or i == len(words) - 1:
                        yield StreamChunk(
                            content=current_chunk.strip(),
                            type="text",
                            conversation_id=conversation_id
                        )
                        current_chunk = ""
            elif chunk.get("type") == "error":
                yield StreamChunk(
                    content=f"Error: {chunk.get('error', 'Unknown error')}",
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
        # Test Eva's authentication
        eva_test = oauth_manager.test_eva_authentication()
        eva_status = "authenticated" if eva_test.get("success") else "not_authenticated"
        
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
    Chat with Eva - synchronous response.
    
    Args:
        request: Chat request containing user message and metadata
        
    Returns:
        ChatResponse: Eva's response
    """
    try:
        conversation_id = request.conversation_id or generate_conversation_id()
        
        logger.info(f"Chat request from {request.user_id}: {request.message}")
        
        # Use LangGraph agent for response
        response = await eva_response(request.message, request.user_id, conversation_id)
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            metadata={"user_id": request.user_id}
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
    Chat with Eva - streaming response.
    
    Args:
        request: Chat request containing user message and metadata
        
    Returns:
        StreamingResponse: Server-sent events with Eva's response chunks
    """
    try:
        conversation_id = request.conversation_id or generate_conversation_id()
        
        logger.info(f"Stream request from {request.user_id}: {request.message}")
        
        async def generate_stream():
            try:
                # Use LangGraph agent for streaming
                async for chunk in eva_stream(request.message, request.user_id, conversation_id):
                    yield f"data: {chunk.json()}\n\n"
                
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
    
    Args:
        request: Calendar connection request
        
    Returns:
        ConnectCalendarResponse: Connection result with user info
    """
    try:
        logger.info(f"Calendar connection request for user: {request.user_id}")
        
        # Connect user calendar
        user_info = oauth_manager.connect_user_calendar(request.user_id)
        
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
    
    Args:
        request: Calendar disconnection request
        
    Returns:
        DisconnectCalendarResponse: Disconnection result
    """
    try:
        logger.info(f"Calendar disconnection request for user: {request.user_id}")
        
        # Disconnect user calendar
        success = oauth_manager.disconnect_user_calendar(request.user_id)
        
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
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "eva_assistant.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True if settings.environment == "development" else False,
        log_level=settings.log_level.lower()
    ) 