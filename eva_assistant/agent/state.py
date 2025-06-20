"""
Simplified LangGraph State definition for Eva Assistant.

Minimal state structure for meeting_agent + reflect workflow.
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class EvaState(TypedDict):
    """
    Simplified Eva Assistant conversation state.
    
    Only contains essential fields for the meeting_agent + reflect workflow.
    """
    
    # Core conversation
    messages: List[BaseMessage]
    user_id: str
    current_request: str
    
    # Response handling
    final_response: Optional[str]
    needs_confirmation: Optional[bool]
    response_ready: Optional[bool]
    
    # Tool and context data
    tool_results: Optional[List[Dict[str, Any]]]
    context: Optional[Dict[str, Any]]


# Helper functions for working with simplified EvaState

def create_eva_state(
    user_id: str = "founder",
    conversation_id: str = "",
    current_request: str = ""
) -> EvaState:
    """Create a new simplified EvaState with default values."""
    return EvaState(
        messages=[],
        user_id=user_id,
        current_request=current_request,
        final_response=None,
        needs_confirmation=False,
        response_ready=False,
        tool_results=[],
        context={}
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