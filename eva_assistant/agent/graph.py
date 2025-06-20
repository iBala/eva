"""
LangGraph implementation for Eva Assistant.

Creates and manages the conversation flow graph:
start -> plan -> act -> reflect -> end
"""

import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver

from eva_assistant.agent.state import EvaState, create_eva_state
from eva_assistant.agent.nodes import meeting_agent_node, reflect_node
from eva_assistant.config import settings

logger = logging.getLogger(__name__)


class EvaGraph:
    """
    Eva Assistant conversation graph manager.
    
    Implements the core reasoning flow:
    1. Plan - Analyze request and create execution plan
    2. Act - Execute planned actions using tools
    3. Reflect - Analyze results and prepare response
    """
    
    def __init__(self, checkpointer=None):
        """Initialize the graph with optional checkpointer for persistence."""
        self.checkpointer = checkpointer
        self.graph = None
        self.app = None
        self._build_graph()
    
    def _build_graph(self):
        """Build the simplified LangGraph workflow."""
        logger.info("Building Eva conversation graph")
        
        # Create the graph
        workflow = StateGraph(EvaState)
        
        # Add nodes - simplified to just meeting_agent and reflect
        workflow.add_node("meeting_agent", meeting_agent_node)
        workflow.add_node("reflect", reflect_node)
        
        # Define the flow
        workflow.add_edge(START, "meeting_agent")
        
        # Conditional edge from meeting_agent node
        workflow.add_conditional_edges(
            "meeting_agent",
            self._should_reflect,
            {
                "reflect": "reflect",         # Move to reflection
                "continue": "meeting_agent"   # Continue if more work needed
            }
        )
        
        # Conditional edge from reflect node
        workflow.add_conditional_edges(
            "reflect",
            self._should_end,
            {
                "end": END,                   # End if response is ready
                "continue": "meeting_agent"   # Back to meeting_agent if more work needed
            }
        )
        
        # Compile the graph
        self.graph = workflow
        self.app = workflow.compile(checkpointer=self.checkpointer)
        
        logger.info("Eva conversation graph built successfully")
    
    def _should_reflect(self, state: EvaState) -> Literal["continue", "reflect"]:
        """
        Determine if we should continue working or move to reflection.
        
        Move to reflection if:
        - Task appears complete
        - Waiting for confirmation
        - Need validation
        
        Args:
            state: Current conversation state
            
        Returns:
            "continue" to keep working, "reflect" to validate
        """
        # Move to reflection if task appears complete
        if state.get("response_ready", False):
            logger.info("Task complete, moving to reflection")
            return "reflect"
        
        # Move to reflection if waiting for confirmation
        if state.get("needs_confirmation", False):
            logger.info("Confirmation needed, moving to reflection")
            return "reflect"
        
        # Continue working if task is not complete
        logger.info("Task in progress, continuing meeting_agent work")
        return "continue"
    
    def _should_end(self, state: EvaState) -> Literal["end", "continue"]:
        """
        Determine if we should end the conversation or continue processing.
        
        End if:
        - Response is ready and no confirmation needed
        - Confirmation is needed (waiting for user)
        - Maximum iterations reached
        
        Args:
            state: Current conversation state
            
        Returns:
            "end" to finish, "continue" to keep processing
        """
        # End if response is ready
        if state["response_ready"]:
            logger.info("Response ready, ending conversation")
            return "end"
        
        # End if waiting for confirmation
        if state["needs_confirmation"]:
            logger.info("Waiting for user confirmation, ending conversation")
            return "end"
        
        # Continue if reflection determines more work is needed
        logger.info("Reflection determined more work needed, continuing")
        return "continue"
    
    async def process_message(
        self,
        user_message: str,
        user_id: str = "founder",
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the conversation graph.
        
        Args:
            user_message: The user's input message
            user_id: User identifier
            conversation_id: Conversation ID for thread management
            
        Returns:
            Dict containing Eva's response and metadata
        """
        logger.info(f"Processing message from {user_id}: {user_message}")
        
        try:
            # Create initial state using helper function
            initial_state = create_eva_state(
                user_id=user_id,
                conversation_id=conversation_id or f"conv_{user_id}",
                current_request=user_message
            )
            
            # Configure for thread management if we have a conversation_id
            config = {"configurable": {"thread_id": conversation_id}} if conversation_id else {}
            
            # Run the graph
            final_state = None
            async for state in self.app.astream(initial_state, config=config):
                final_state = state
                logger.debug(f"Graph step completed: {list(state.keys())}")
            
            if final_state is None:
                raise Exception("Graph execution failed - no final state")
            
            # Extract the final state - it should be the last node's output
            eva_state = None
            for node_name, node_state in final_state.items():
                if isinstance(node_state, dict) and "final_response" in node_state:
                    eva_state = node_state
                    break
            
            if eva_state is None:
                raise Exception("No EvaState found in final state")
            
            # Prepare response
            response = {
                "response": eva_state.get("final_response", "I processed your request but couldn't generate a response."),
                "conversation_id": conversation_id,
                "needs_confirmation": eva_state.get("needs_confirmation", False),
                "completed": eva_state.get("response_ready", True),
                "metadata": {
                    "tool_calls": len(eva_state.get("tool_results", [])),
                    "context": eva_state.get("context", {})
                }
            }
            
            logger.info(f"Message processed successfully: {eva_state.get('request_type', 'unknown')}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
            # Return error response
            return {
                "response": f"I apologize, but I encountered an error while processing your request. Could you please try again? Error: {str(e)}",
                "conversation_id": conversation_id,
                "needs_confirmation": False,
                "confirmation_message": "",
                "request_type": "error",
                "completed": True,
                "metadata": {"error": str(e)}
            }
    
    async def stream_message(
        self,
        user_message: str,
        user_id: str = "founder",
        conversation_id: str = None
    ):
        """
        Stream the processing of a user message through the conversation graph.
        
        Args:
            user_message: The user's input message
            user_id: User identifier
            conversation_id: Conversation ID for thread management
            
        Yields:
            Dict containing incremental updates and final response
        """
        logger.info(f"Streaming message from {user_id}: {user_message}")
        
        try:
            # Create initial state using helper function
            initial_state = create_eva_state(
                user_id=user_id,
                conversation_id=conversation_id or f"conv_{user_id}",
                current_request=user_message
            )
            
            # Configure for thread management if we have a conversation_id
            config = {"configurable": {"thread_id": conversation_id}} if conversation_id else {}
            
            # Stream the graph execution
            async for state in self.app.astream(initial_state, config=config):
                # Extract node information
                node_name = list(state.keys())[0] if state else "unknown"
                node_state = list(state.values())[0] if state else {}
                
                # Yield progress update
                yield {
                    "type": "progress",
                    "node": node_name,
                    "conversation_id": conversation_id,
                    "metadata": {
                        "step": getattr(node_state, 'current_step', 0) if hasattr(node_state, 'current_step') else 0,
                        "plan_length": len(getattr(node_state, 'plan', []))
                    }
                }
            
            # Get final state for response
            final_response = await self.process_message(user_message, user_id, conversation_id)
            
            # Yield final response
            yield {
                "type": "response",
                **final_response
            }
            
        except Exception as e:
            logger.error(f"Error streaming message: {e}")
            
            # Yield error
            yield {
                "type": "error",
                "error": str(e),
                "conversation_id": conversation_id
            }
    
    @classmethod
    def build(cls, with_persistence: bool = False) -> "EvaGraph":
        """
        Build and return a configured Eva conversation graph.
        
        Args:
            with_persistence: Whether to enable SQLite persistence
            
        Returns:
            Configured EvaGraph instance
        """
        checkpointer = None
        
        if with_persistence:
            try:
                # Set up SQLite checkpointer for conversation persistence
                db_path = settings.data_dir / "eva_conversations.db"
                settings.data_dir.mkdir(parents=True, exist_ok=True)
                
                checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
                logger.info(f"SQLite persistence enabled: {db_path}")
                
            except Exception as e:
                logger.warning(f"Failed to setup persistence: {e}, continuing without it")
                checkpointer = None
        
        return cls(checkpointer=checkpointer)


# Global graph instance
eva_graph = None


def get_eva_graph():
    """
    Get the Eva LangGraph application for LangSmith deployment.
    
    Returns:
        Compiled LangGraph application ready for execution
    """
    # Build Eva graph with persistence enabled for LangSmith
    eva_instance = EvaGraph.build(with_persistence=True)
    
    # Return the compiled LangGraph application
    return eva_instance.app 