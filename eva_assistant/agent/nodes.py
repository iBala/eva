"""
LangGraph node implementations for Eva Assistant.

Contains the core reasoning nodes: plan, act, reflect that form Eva's decision-making process.
"""

import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from eva_assistant.agent.state import EvaState, create_eva_state, complete_tool_call, update_context, set_confirmation_needed, set_final_response
from eva_assistant.agent.prompts import (
    get_planning_prompt, 
    get_tool_execution_prompt, 
    get_reflection_prompt,
    EVA_PERSONALITY
)
from eva_assistant.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
    api_key=settings.openai_api_key
)


async def plan_node(state: EvaState) -> EvaState:
    """
    Planning node - Analyzes user request and creates execution plan.
    
    This node:
    1. Analyzes the user's current request
    2. Determines what type of request it is
    3. Creates a step-by-step plan to fulfill the request
    4. Identifies if confirmation will be needed
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with plan and request analysis
    """
    logger.info(f"Planning node: Analyzing request '{state['current_request']}'")
    
    try:
        # Get the planning prompt with current context
        planning_prompt = get_planning_prompt(state)
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=EVA_PERSONALITY),
            HumanMessage(content=planning_prompt)
        ]
        
        # Get plan from LLM
        response = await llm.ainvoke(messages)
        
        # Parse the JSON response
        try:
            plan_data = json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse planning response as JSON: {e}")
            # Fallback to simple plan
            plan_data = {
                "request_type": "other",
                "plan": [{"step": 1, "action": "respond_directly", "description": "Provide direct response"}],
                "needs_confirmation": False,
                "confidence": 0.5
            }
        
        # Update state with plan
        state["request_type"] = plan_data.get("request_type", "other")
        state["eva_plan"] = plan_data.get("plan", [])
        state["current_step"] = 0
        
        # Set confirmation if needed
        if plan_data.get("needs_confirmation", False):
            state["needs_confirmation"] = True
        
        logger.info(f"Plan created: {len(state['eva_plan'])} steps, type: {state['request_type']}")
        
        return state
        
    except Exception as e:
        logger.error(f"Planning node error: {e}")
        # Fallback plan
        state["eva_plan"] = [{"step": 1, "action": "respond_directly", "description": "Provide direct response"}]
        state["request_type"] = "error"
        state["current_step"] = 0
        
        return state


async def act_node(state: EvaState) -> EvaState:
    """
    Action node - Executes tools based on the current plan step.
    
    This node:
    1. Takes the current step from the plan
    2. Identifies which tools need to be called
    3. Executes the tool calls
    4. Stores results in state
    5. Moves to next step or signals completion
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with tool results and progress
    """
    logger.info(f"Action node: Executing step {state['current_step']}")
    
    if state["current_step"] >= len(state["eva_plan"]):
        logger.info("All plan steps completed")
        return state
    
    current_step_info = state["eva_plan"][state["current_step"]]
    action = current_step_info.get("action", "")
    
    try:
        # Execute different actions based on the plan
        if action == "check_calendar_availability":
            result = await _mock_check_calendar_availability(state)
        elif action == "get_user_calendar_events":
            result = await _mock_get_calendar_events(state)
        elif action == "create_calendar_event":
            result = await _mock_create_calendar_event(state)
        elif action == "send_email":
            result = await _mock_send_email(state)
        elif action == "get_contact_info":
            result = await _mock_get_contact_info(state)
        elif action == "respond_directly":
            result = await _generate_direct_response(state)
        else:
            logger.warning(f"Unknown action: {action}")
            result = {"success": False, "error": f"Unknown action: {action}"}
        
        # Store the tool result
        call_id = f"{action}_{state['current_step']}"
        complete_tool_call(state, call_id, result, result.get("success", True))
        
        # Move to next step
        state["current_step"] += 1
        
        logger.info(f"Action completed: {action}, moving to step {state['current_step']}")
        
        return state
        
    except Exception as e:
        logger.error(f"Action node error: {e}")
        
        # Record the error
        call_id = f"{action}_{state['current_step']}"
        complete_tool_call(state, call_id, {"error": str(e)}, False, str(e))
        state["current_step"] += 1
        
        return state


async def reflect_node(state: EvaState) -> EvaState:
    """
    Reflection node - Analyzes results and prepares final response.
    
    This node:
    1. Reviews all completed tool calls and results
    2. Determines if the request has been fulfilled
    3. Checks if confirmation is needed
    4. Prepares Eva's final response to the user
    5. Decides if more actions are needed
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with final response and completion status
    """
    logger.info("Reflection node: Analyzing results and preparing response")
    
    try:
        # Get reflection prompt with current context
        reflection_prompt = get_reflection_prompt(state)
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=EVA_PERSONALITY),
            HumanMessage(content=reflection_prompt)
        ]
        
        # Get reflection from LLM
        response = await llm.ainvoke(messages)
        
        # Parse the JSON response
        try:
            reflection_data = json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reflection response as JSON: {e}")
            # Fallback reflection
            reflection_data = {
                "success": True,
                "needs_more_actions": False,
                "needs_confirmation": False,
                "final_response": "I've processed your request. How else can I help you?",
                "confidence": 0.5
            }
        
        # Update state based on reflection
        if reflection_data.get("needs_confirmation", False):
            set_confirmation_needed(state, reflection_data.get("confirmation_message", ""))
        
        if reflection_data.get("final_response"):
            set_final_response(state, reflection_data["final_response"])
        
        # Determine if we're done
        needs_more_actions = reflection_data.get("needs_more_actions", False)
        
        logger.info(f"Reflection complete: needs_more_actions={needs_more_actions}")
        
        return state
        
    except Exception as e:
        logger.error(f"Reflection node error: {e}")
        
        # Fallback response
        fallback_response = f"I apologize, but I encountered an issue while processing your request: {state['current_request']}. Could you please try rephrasing your request?"
        set_final_response(state, fallback_response)
        
        return state


# Mock tool implementations (will be replaced with real tools later)

async def _mock_check_calendar_availability(state: EvaState) -> Dict[str, Any]:
    """Mock calendar availability check."""
    logger.info("Mock: Checking calendar availability")
    
    # Simulate checking availability
    availability = {
        "available_slots": [
            {"start": "2024-01-15T14:00:00Z", "end": "2024-01-15T15:00:00Z"},
            {"start": "2024-01-16T10:00:00Z", "end": "2024-01-16T11:00:00Z"},
            {"start": "2024-01-17T13:00:00Z", "end": "2024-01-17T14:00:00Z"}
        ],
        "busy_times": [],
        "timezone": "UTC"
    }
    
    update_context(state, "calendar", availability)
    
    return {
        "success": True,
        "availability": availability,
        "message": "Calendar availability checked successfully"
    }


async def _mock_get_calendar_events(state: EvaState) -> Dict[str, Any]:
    """Mock getting calendar events."""
    logger.info("Mock: Getting calendar events")
    
    events = [
        {
            "id": "event1",
            "title": "Team Meeting",
            "start": "2024-01-15T09:00:00Z",
            "end": "2024-01-15T10:00:00Z"
        },
        {
            "id": "event2",
            "title": "Client Call",
            "start": "2024-01-15T15:00:00Z",
            "end": "2024-01-15T16:00:00Z"
        }
    ]
    
    update_context(state, "calendar", {"events": events})
    
    return {
        "success": True,
        "events": events,
        "message": "Calendar events retrieved successfully"
    }


async def _mock_create_calendar_event(state: EvaState) -> Dict[str, Any]:
    """Mock creating a calendar event."""
    logger.info("Mock: Creating calendar event")
    
    meeting_context = state["meeting_context"]
    
    event = {
        "id": "new_event_123",
        "title": meeting_context.get("title", "New Meeting"),
        "start": meeting_context.get("start_time", "2024-01-15T14:00:00Z"),
        "end": meeting_context.get("end_time", "2024-01-15T15:00:00Z"),
        "attendees": meeting_context.get("attendees", [])
    }
    
    return {
        "success": True,
        "event": event,
        "message": "Calendar event created successfully",
        "event_id": event["id"]
    }


async def _mock_send_email(state: EvaState) -> Dict[str, Any]:
    """Mock sending an email."""
    logger.info("Mock: Sending email")
    
    email_context = state["email_context"]
    
    return {
        "success": True,
        "message": "Email sent successfully",
        "recipients": email_context.get("recipients", []),
        "subject": email_context.get("subject", "Meeting Request")
    }


async def _mock_get_contact_info(state: EvaState) -> Dict[str, Any]:
    """Mock getting contact information."""
    logger.info("Mock: Getting contact info")
    
    return {
        "success": True,
        "contacts": [
            {"name": "John Smith", "email": "john@example.com"},
            {"name": "Jane Doe", "email": "jane@example.com"}
        ],
        "message": "Contact information retrieved"
    }


async def _generate_direct_response(state: EvaState) -> Dict[str, Any]:
    """Generate a direct response using LLM."""
    logger.info("Generating direct response")
    
    try:
        messages = [
            SystemMessage(content=EVA_PERSONALITY),
            HumanMessage(content=f"""
                         Provide a helpful response to this request: {state['current_request']}
             
             Context:
             - User: {state['user_id']}
             - Calendar context: {state['calendar_context']}
             - Meeting context: {state['meeting_context']}
            
            Be professional, direct, and helpful. Provide clear next steps if applicable.
            """)
        ]
        
        response = await llm.ainvoke(messages)
        
        return {
            "success": True,
            "response": response.content,
            "message": "Direct response generated"
        }
        
    except Exception as e:
        logger.error(f"Error generating direct response: {e}")
        return {
            "success": False,
            "response": "I apologize, but I'm having trouble processing your request right now. Could you please try again?",
            "error": str(e)
        } 