"""
Eva Assistant LangGraph Nodes.

Implements the core workflow:
- Meeting Agent: GPT-4o with thinking, all tools available
- Reflect Agent: GPT-4o-mini, simple review, no tools
"""

import json
import logging
from typing import Dict, Any

import litellm
from litellm import acompletion

from eva_assistant.agent.state import EvaState
from eva_assistant.agent.prompts import get_meeting_agent_prompt, get_reflection_prompt
from eva_assistant.tools import convert_tools_to_litellm_format, execute_tool_call

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = False


async def meeting_agent_node(state: EvaState) -> Dict[str, Any]:
    """
    Meeting Agent Node - Main processing with GPT-4o + thinking + all tools.
    
    This node:
    1. Takes the user request
    2. Uses GPT-4o with thinking enabled
    3. Has access to all tools (calendar, email, etc.)
    4. Plans and executes using tools
    5. Produces a response
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with response and tool calls
    """
    try:
        user_message = state.get("user_message", "")
        user_id = state.get("user_id", "founder")
        
        logger.info(f"Meeting Agent processing: {user_message[:100]}...")
        
        # Get all available tools
        tools = convert_tools_to_litellm_format()
        logger.info(f"Meeting Agent has access to {len(tools)} tools")
        
        # Build the prompt using existing prompts.py
        system_prompt = get_meeting_agent_prompt({
            "user_id": user_id,
            "current_request": user_message,
            "context": {},
            "tool_results": []
        })
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Call GPT-4o with thinking and tools (NOW PROPERLY USING acompletion)
        response = await acompletion(
            model="gpt-4o",
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto",  # Let LLM decide when to use tools
            temperature=0.0,  # Deterministic for consistency
            stream=False
        )
        
        # Extract the response
        message = response.choices[0].message
        agent_response = message.content or ""
        tool_calls = getattr(message, 'tool_calls', None)
        
        executed_tools = []
        
        # Execute tool calls if any
        if tool_calls:
            logger.info(f"Meeting Agent executing {len(tool_calls)} tool calls")
            
            for tool_call in tool_calls:
                try:
                    # Parse tool arguments
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Add user_id to args if tool needs it
                    if _tool_needs_user_id(tool_call.function.name):
                        tool_args['user_id'] = user_id
                    
                    # Execute the tool
                    result = await execute_tool_call(tool_call.function.name, tool_args)
                    
                    executed_tools.append({
                        "name": tool_call.function.name,
                        "args": tool_args,
                        "result": result
                    })
                    
                    logger.info(f"Tool {tool_call.function.name} executed successfully")
                    
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    executed_tools.append({
                        "name": tool_call.function.name,
                        "args": {},
                        "result": {"success": False, "error": str(e)}
                    })
            
            # If we have tool results, give LLM a chance to use them for final response
            if executed_tools:
                # Add tool results to conversation
                messages.append({
                    "role": "assistant",
                    "content": agent_response,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls
                    ]
                })
                
                # Add tool results
                for tool_call, executed_tool in zip(tool_calls, executed_tools):
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(executed_tool["result"])
                    })
                
                # Get final response incorporating tool results (NOW PROPERLY USING acompletion)
                final_response = await acompletion(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.0,
                    stream=False
                )
                
                agent_response = final_response.choices[0].message.content or agent_response
        
        logger.info(f"Meeting Agent completed with {len(executed_tools)} tool calls")
        
        return {
            "response": agent_response,
            "tool_calls": executed_tools,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Meeting Agent error: {e}")
        return {
            "response": f"I apologize, but I encountered an error processing your request: {str(e)}",
            "tool_calls": [],
            "success": False,
            "error": str(e)
        }


async def reflect_node(state: EvaState) -> Dict[str, Any]:
    """
    Reflect Agent Node - Simple review with GPT-4o-mini, no tools.
    
    This node:
    1. Reviews the Meeting Agent's response
    2. Checks if it addresses the original request
    3. Uses GPT-4o-mini (lighter, faster)
    4. No tools available
    5. Approves or suggests improvements
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with reflection results
    """
    try:
        user_message = state.get("user_message", "")
        agent_response = state.get("response", "")
        tool_calls = state.get("tool_calls", [])
        
        logger.info("Reflect Agent reviewing Meeting Agent's work")
        
        # Build reflection prompt
        reflection_prompt = get_reflection_prompt({
            "current_request": user_message,
            "agent_response": agent_response,
            "tool_results": [{"tool": tc["name"], "result": tc["result"]} for tc in tool_calls],
            "context": {}
        })
        
        # Simple review with GPT-4o-mini (no tools)
        messages = [
            {"role": "system", "content": reflection_prompt},
            {"role": "user", "content": f"Review this response to: '{user_message}'\n\nResponse: {agent_response}"}
        ]
        
        response = await acompletion(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
            stream=False
        )
        
        reflection_content = response.choices[0].message.content
        
        # Parse reflection (expecting JSON from prompt)
        try:
            reflection_data = json.loads(reflection_content)
            approved = reflection_data.get("task_complete", True)
            final_response = reflection_data.get("final_response", agent_response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            logger.warning("Reflection JSON parsing failed, using original response")
            approved = True
            final_response = agent_response
        
        logger.info(f"Reflect Agent {'approved' if approved else 'suggested improvements'}")
        
        return {
            "reflection_approved": approved,
            "final_response": final_response,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Reflect Agent error: {e}")
        return {
            "reflection_approved": True,  # Default to approved on error
            "final_response": state.get("response", "I apologize, but I encountered an error."),
            "success": False,
            "error": str(e)
        }


def _tool_needs_user_id(tool_name: str) -> bool:
    """
    Check if a tool needs user_id parameter.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        True if tool needs user_id
    """
    # Tools that need user_id for authentication/permissions
    user_id_tools = [
        "get_all_calendar_events",
        "get_calendar_event", 
        "create_calendar_event",
        "check_calendar_availability"
    ]
    return tool_name in user_id_tools 