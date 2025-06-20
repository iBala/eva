"""
LangGraph State definition for Eva Assistant.

Defines the state structure that flows through the graph nodes.
"""

from typing import List, Dict, Any, Optional, Annotated
from datetime import datetime
from dataclasses import dataclass, field
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


@dataclass
class ToolCall:
    """Represents a tool call to be executed."""
    tool_name: str
    args: Dict[str, Any]
    call_id: str


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""
    call_id: str
    result: Any
    success: bool
    error: Optional[str] = None


class EvaState(TypedDict):
    """
    Eva Assistant conversation state.
    
    Custom state for Eva's conversation flow with all necessary fields
    for planning, execution, and response generation.
    """
    
    # Messages (replaces MessagesState)
    messages: List[BaseMessage]
    
    # User context
    user_id: str
    conversation_id: Optional[str]
    
    # Current request processing
    current_request: Optional[str]
    request_type: Optional[str]  # "schedule_meeting", "check_availability", "send_email", etc.
    
    # Planning and execution
    eva_plan: List[Dict[str, Any]]  # Renamed from 'plan' to avoid conflicts
    current_step: Optional[int]
    
    # Tool execution
    pending_tool_calls: Optional[List[Dict[str, Any]]]
    completed_tool_calls: Optional[List[Dict[str, Any]]]
    
    # Context and memory
    calendar_context: Optional[Dict[str, Any]]  # User's calendar info
    meeting_context: Optional[Dict[str, Any]]   # Current meeting being planned
    email_context: Optional[Dict[str, Any]]     # Email thread context
    
    # Decision state
    needs_confirmation: Optional[bool]
    confirmation_message: Optional[str]
    awaiting_response: Optional[bool]
    
    # Final response
    final_response: Optional[str]
    response_ready: Optional[bool]
    
    # Metadata
    started_at: Optional[str]  # ISO string instead of datetime
    updated_at: Optional[str]


# Helper functions for working with EvaState

def create_eva_state(
    user_id: str = "founder",
    conversation_id: str = "",
    current_request: str = ""
) -> EvaState:
    """Create a new EvaState with default values."""
    from datetime import datetime
    
    return EvaState(
        messages=[],
        user_id=user_id,
        conversation_id=conversation_id,
        current_request=current_request,
        request_type="",
        eva_plan=[],
        current_step=0,
        pending_tool_calls=[],
        completed_tool_calls=[],
        calendar_context={},
        meeting_context={},
        email_context={},
        needs_confirmation=False,
        confirmation_message="",
        awaiting_response=False,
        final_response="",
        response_ready=False,
        started_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )


def add_tool_call(state: EvaState, tool_name: str, args: Dict[str, Any], call_id: str = None) -> str:
    """Add a tool call to the pending list."""
    # Ensure pending_tool_calls exists
    if "pending_tool_calls" not in state:
        state["pending_tool_calls"] = []
        
    if call_id is None:
        call_id = f"{tool_name}_{len(state['pending_tool_calls'])}"
    
    tool_call = {
        "tool_name": tool_name,
        "args": args,
        "call_id": call_id
    }
    state["pending_tool_calls"].append(tool_call)
    return call_id


def complete_tool_call(state: EvaState, call_id: str, result: Any, success: bool = True, error: str = None):
    """Mark a tool call as completed and store the result."""
    tool_result = {
        "call_id": call_id,
        "result": result,
        "success": success,
        "error": error
    }
    
    # Ensure completed_tool_calls exists
    if "completed_tool_calls" not in state:
        state["completed_tool_calls"] = []
    state["completed_tool_calls"].append(tool_result)
    
    # Ensure pending_tool_calls exists and remove from pending
    if "pending_tool_calls" not in state:
        state["pending_tool_calls"] = []
    state["pending_tool_calls"] = [tc for tc in state["pending_tool_calls"] if tc["call_id"] != call_id]


def update_context(state: EvaState, context_type: str, data: Dict[str, Any]):
    """Update specific context data."""
    if context_type == "calendar":
        if "calendar_context" not in state:
            state["calendar_context"] = {}
        state["calendar_context"].update(data)
    elif context_type == "meeting":
        if "meeting_context" not in state:
            state["meeting_context"] = {}
        state["meeting_context"].update(data)
    elif context_type == "email":
        if "email_context" not in state:
            state["email_context"] = {}
        state["email_context"].update(data)


def set_confirmation_needed(state: EvaState, message: str):
    """Set that confirmation is needed from the user."""
    state["needs_confirmation"] = True
    state["confirmation_message"] = message
    state["awaiting_response"] = True


def set_final_response(state: EvaState, response: str):
    """Set the final response and mark as ready."""
    from datetime import datetime
    state["final_response"] = response
    state["response_ready"] = True
    state["updated_at"] = datetime.utcnow().isoformat() 