"""
Simplified LangGraph State definition for Eva Assistant.

Minimal state structure for meeting_agent + reflect workflow.
"""

from typing import Dict, Any, Optional
from typing_extensions import TypedDict


class EvaState(TypedDict):
    """
    Enhanced Eva Assistant conversation state with conversation history support.
    
    Essential fields for the meeting_agent + reflect workflow plus conversation persistence.
    """
    
    # Core input
    user_message: str
    user_id: str
    
    # Conversation context - NEW: Added for conversation history support
    conversation_id: Optional[str]
    messages: Optional[list]  # Historical messages in LLM format for context
    is_new_conversation: Optional[bool]  # Flag to indicate if this is a new conversation
    
    # Meeting agent output
    response: Optional[str]
    tool_calls: Optional[list]
    
    # Reflect agent output
    reflection_approved: Optional[bool]
    final_response: Optional[str]
    
    # Metadata
    success: Optional[bool]
    error: Optional[str]


# Helper functions for working with simplified EvaState

def create_eva_state(
    user_id: str = "founder",
    conversation_id: Optional[str] = None,
    user_message: str = "",
    messages: Optional[list] = None,
    is_new_conversation: bool = True
) -> EvaState:
    """Create a new enhanced EvaState with conversation support."""
    return EvaState(
        user_message=user_message,
        user_id=user_id,
        conversation_id=conversation_id,
        messages=messages or [],
        is_new_conversation=is_new_conversation,
        response=None,
        tool_calls=None,
        reflection_approved=None,
        final_response=None,
        success=None,
        error=None
    )


def add_tool_result(state: EvaState, tool_name: str, result: Any, success: bool = True):
    """Add a tool result to the state."""
    if "tool_results" not in state:
        state["tool_results"] = []
        
    tool_result = {
        "tool": tool_name,
        "result": result,
        "success": success
    }
    state["tool_results"].append(tool_result)


def update_context(state: EvaState, key: str, value: Any):
    """Update context data."""
    if "context" not in state:
        state["context"] = {}
    state["context"][key] = value


def set_response(state: EvaState, response: str, needs_confirmation: bool = False):
    """Set the final response and confirmation status."""
    state["final_response"] = response
    state["needs_confirmation"] = needs_confirmation
    state["response_ready"] = not needs_confirmation 