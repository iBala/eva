"""
Eva Assistant Graph - Meeting Agent + Reflect Architecture.

Implements the correct workflow:
Start -> Meeting_Agent -> Reflect -> End

- Meeting_Agent: GPT-4o with thinking + all tools
- Reflect: GPT-4o-mini review, no tools
"""

import logging
from typing import Dict, Any, Optional, List

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from eva_assistant.agent.state import EvaState
from eva_assistant.agent.nodes import meeting_agent_node, reflect_node

logger = logging.getLogger(__name__)


class EvaGraph:
    """
    Eva Assistant Graph with Meeting Agent + Reflect workflow.
    
    Architecture:
    Start -> Meeting_Agent (GPT-4o + tools + thinking) -> Reflect (GPT-4o-mini review) -> End
    """
    
    def __init__(self):
        """Initialize the Eva graph."""
        self.graph = None
        
    def build(self, with_persistence: bool = False) -> CompiledStateGraph:
        """
        Build the Eva assistant graph.
        
        Args:
            with_persistence: Whether to enable state persistence (disabled for now)
            
        Returns:
            Compiled LangGraph state graph
        """
        # Create the graph
        workflow = StateGraph(EvaState)
        
        # Add nodes
        workflow.add_node("meeting_agent", meeting_agent_node)
        workflow.add_node("reflect", reflect_node)
        
        # Define the flow: Start -> Meeting_Agent -> Reflect -> End
        workflow.add_edge(START, "meeting_agent")
        workflow.add_edge("meeting_agent", "reflect")
        workflow.add_edge("reflect", END)
        
        # Compile the graph
        if with_persistence:
            # TODO: Add proper async context management for persistence
            logger.warning("Persistence disabled - requires async context management")
            
        self.graph = workflow.compile()
        logger.info("Eva graph compiled successfully")
        return self.graph
    
    async def process_message(self, user_message: str, user_id: str = "founder",
                            conversation_id: Optional[str] = None,
                            conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Process a user message through the graph with conversation history.
        
        Args:
            user_message: The user's message
            user_id: User identifier
            conversation_id: Conversation identifier for context
            conversation_history: Previous conversation messages for context
            
        Returns:
            Processing result with response and metadata
        """
        if not self.graph:
            self.build()
        
        # Create initial state with conversation context
        initial_state = {
            "user_message": user_message,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "messages": conversation_history or [],
            "is_new_conversation": conversation_history is None or len(conversation_history) == 0,
            "response": None,
            "tool_calls": None,
            "reflection_approved": None,
            "final_response": None,
            "success": None,
            "error": None
        }
        
        # Run the graph
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "response": result.get("final_response", result.get("response", "")),
            "tool_calls": result.get("tool_calls", []),
            "success": result.get("success", False),
            "error": result.get("error"),
            "reflection_approved": result.get("reflection_approved", False)
        }
    
    async def stream_message(self, user_message: str, user_id: str = "founder",
                           conversation_id: Optional[str] = None,
                           conversation_history: Optional[List[Dict[str, str]]] = None):
        """
        Stream a response to user message with conversation history.
        
        Args:
            user_message: The user's message
            user_id: User identifier
            conversation_id: Conversation identifier for context
            conversation_history: Previous conversation messages for context
            
        Yields:
            Streaming response chunks
        """
        if not self.graph:
            self.build()
        
        # Create initial state with conversation context
        initial_state = {
            "user_message": user_message,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "messages": conversation_history or [],
            "is_new_conversation": conversation_history is None or len(conversation_history) == 0,
            "response": None,
            "tool_calls": None,
            "reflection_approved": None,
            "final_response": None,
            "success": None,
            "error": None
        }
        
        # Stream the graph execution
        try:
            async for chunk in self.graph.astream(initial_state):
                node_name = list(chunk.keys())[0] if chunk else "unknown"
                node_output = list(chunk.values())[0] if chunk else {}
                
                if node_name == "meeting_agent":
                    # Send progress update for meeting agent
                    yield {
                        "type": "progress",
                        "content": "Meeting Agent processing...",
                        "metadata": {
                            "node": node_name,
                            "tool_calls": len(node_output.get("tool_calls", []))
                        }
                    }
                    
                    # If there's a response, stream it
                    if node_output.get("response"):
                        response = node_output["response"]
                        words = response.split()
                        current_chunk = ""
                        
                        for i, word in enumerate(words):
                            current_chunk += word + " "
                            
                            # Send chunk every 4 words or at the end
                            if (i + 1) % 4 == 0 or i == len(words) - 1:
                                yield {
                                    "type": "content",
                                    "content": current_chunk.strip()
                                }
                                current_chunk = ""
                
                elif node_name == "reflect":
                    # Send reflection progress
                    yield {
                        "type": "progress", 
                        "content": "Reflect Agent reviewing...",
                        "metadata": {"node": node_name}
                    }
                    
                    # Send final response if different from meeting agent
                    final_response = node_output.get("final_response", "")
                    if final_response:
                        yield {
                            "type": "final_response",
                            "content": final_response,
                            "metadata": {
                                "reflection_approved": node_output.get("reflection_approved", False)
                            }
                        }
                        
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield {
                "type": "error",
                "content": f"Error: {str(e)}"
            }


# Global instance for FastAPI
_eva_graph_instance = None


def get_eva_graph() -> EvaGraph:
    """
    Get the global Eva graph instance.
    
    Returns:
        EvaGraph instance for FastAPI usage
    """
    global _eva_graph_instance
    if _eva_graph_instance is None:
        _eva_graph_instance = EvaGraph()
    return _eva_graph_instance


def get_eva_app() -> CompiledStateGraph:
    """
    Get compiled Eva graph for LangSmith deployment.
    
    Returns:
        Compiled graph for deployment
    """
    eva_graph = EvaGraph()
    return eva_graph.build(with_persistence=False) 