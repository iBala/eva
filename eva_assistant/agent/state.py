"""
Simplified LangGraph State definition for Eva Assistant.

Minimal state structure for meeting_agent + reflect workflow.
"""

from typing import Dict, Any, Optional
from typing_extensions import TypedDict


class EvaState(TypedDict):
    """
    Simplified Eva Assistant conversation state.
    
    Essential fields for the meeting_agent + reflect workflow.
    """
    
    # Core input
    user_message: str
    user_id: str
    
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
    conversation_id: str = "",
    current_request: str = ""
) -> EvaState:
    """Create a new simplified EvaState with default values."""
    return EvaState(
        user_message="",
        user_id=user_id,
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