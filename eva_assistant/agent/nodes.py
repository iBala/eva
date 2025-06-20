"""
Eva Assistant LangGraph nodes.

Simplified structure with meeting_agent (with tools) and reflect (validation) nodes.
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from eva_assistant.agent.state import EvaState, add_tool_result, update_context, set_response
from eva_assistant.agent.prompts import get_meeting_agent_prompt, get_reflection_prompt

logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


async def meeting_agent_node(state: EvaState) -> EvaState:
    """
    Meeting agent node - handles the main logic with access to tools.
    
    This node is Eva's main brain that:
    - Analyzes the user's request
    - Plans and executes tasks using available tools
    - Handles calendar and email operations
    - Prepares responses for confirmation
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with results and response preparation
    """
    logger.info(f"Meeting agent node: Processing request '{state.get('current_request', '')}'")
    
    try:
        # Get the meeting agent prompt
        prompt = get_meeting_agent_prompt(state)
        
        # Create messages for the LLM
        messages = [
            HumanMessage(content=prompt),
        ]
        
        # Add conversation history if available
        if state.get("messages"):
            messages = state.get("messages", []) + messages
        
        # Call the LLM
        response = await llm.ainvoke(messages)
        
        # Parse the response and determine next actions
        response_text = response.content
        
        # For now, simulate tool execution (mock implementation)
        # In production, this would integrate with real tools
        await _execute_mock_tools(state, response_text)
        
        # Update state with the agent's work
        state["final_response"] = response_text
        
        # Determine if we need confirmation or if task is complete
        needs_confirmation = "proceed?" in response_text.lower() or "okay to send?" in response_text.lower()
        state["needs_confirmation"] = needs_confirmation
        
        if needs_confirmation:
            state["confirmation_message"] = response_text
            logger.info("Meeting agent requesting confirmation from user")
        else:
            state["response_ready"] = True
            logger.info("Meeting agent completed task without confirmation needed")
        
        # Update messages
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append(HumanMessage(content=state.get("current_request", "")))
        state["messages"].append(AIMessage(content=response_text))
        
        return state
        
    except Exception as e:
        logger.error(f"Error in meeting agent node: {e}")
        
        # Fallback response
        fallback_response = f"I apologize, but I encountered an issue while processing your request: {state.get('current_request', '')}. Could you please try rephrasing your request?"
        
        state["final_response"] = fallback_response
        state["response_ready"] = True
        state["request_type"] = "error"
        
        return state


async def _execute_mock_tools(state: EvaState, response_text: str):
    """
    Mock tool execution for demonstration.
    
    In production, this would integrate with real calendar and email tools.
    """
    request = state.get("current_request", "").lower()
    
    # Simulate different tool calls based on request type
    if "schedule" in request or "meeting" in request or "book" in request:
        # Mock calendar operations
        logger.info("Mock: Checking calendar availability")
        add_tool_result(state, "calendar_check", {
            "available_slots": ["Tomorrow 2:00-2:30 PM", "Tomorrow 3:00-3:30 PM"],
            "conflicts": []
        })
        
        logger.info("Mock: Creating calendar event")
        add_tool_result(state, "calendar_create", {
            "event_id": "mock_event_123",
            "title": "Meeting",
            "time": "Tomorrow 2:00-2:30 PM",
            "link": "https://meet.google.com/mock-link"
        })
        
        # Update context
        update_context(state, "meeting_title", "Meeting")
        update_context(state, "meeting_time", "Tomorrow 2:00-2:30 PM")
        update_context(state, "meeting_status", "pending_confirmation")
        
    elif "email" in request or "send" in request:
        # Mock email operations
        logger.info("Mock: Sending email")
        add_tool_result(state, "email_send", {
            "message_id": "mock_email_456",
            "to": "contact@example.com",
            "subject": "Meeting Request",
            "status": "sent"
        })
        
        # Update context
        update_context(state, "email_sent", True)
        update_context(state, "email_recipient", "contact@example.com")


async def reflect_node(state: EvaState) -> EvaState:
    """
    Reflection node - validates the meeting agent's work.
    
    This node:
    - Reviews what the meeting agent accomplished
    - Validates that the task was completed correctly
    - Determines if more work is needed
    - Finalizes the response
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with validation results
    """
    logger.info("Reflection node: Analyzing results and preparing response")
    
    try:
        # Get reflection prompt
        prompt = get_reflection_prompt(state)
        
        # Create messages for reflection
        messages = [HumanMessage(content=prompt)]
        
        # Call the LLM for reflection
        response = await llm.ainvoke(messages)
        reflection_text = response.content
        
        # Try to parse as JSON for structured reflection
        try:
            reflection_data = json.loads(reflection_text)
            
            # Update state based on reflection
            state["response_ready"] = not reflection_data.get("needs_more_work", False)
            
            if reflection_data.get("needs_more_work", False):
                logger.info("Reflection determined more work is needed")
                # Clear response_ready to continue working
                state["response_ready"] = False
                state["needs_confirmation"] = False
            else:
                logger.info("Reflection confirmed task is complete")
                state["response_ready"] = True
                
                # Use refined response if provided
                if reflection_data.get("final_response"):
                    state["final_response"] = reflection_data["final_response"]
                    
        except json.JSONDecodeError:
            # Fallback: simple text-based reflection
            logger.info("Using text-based reflection analysis")
            
            if "incomplete" in reflection_text.lower() or "more work" in reflection_text.lower():
                state["response_ready"] = False
                state["needs_confirmation"] = False
                logger.info("Text reflection: More work needed")
            else:
                state["response_ready"] = True
                logger.info("Text reflection: Task complete")
        
        logger.info(f"Reflection complete: response_ready={state.get('response_ready', False)}")
        return state
        
    except Exception as e:
        logger.error(f"Error in reflection node: {e}")
        
        # Default to completing the task if reflection fails
        state["response_ready"] = True
        logger.info("Reflection failed, defaulting to task complete")
        
        return state 