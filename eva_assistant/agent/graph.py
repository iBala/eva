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
from eva_assistant.agent.nodes import plan_node, act_node, reflect_node
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
        """Build the LangGraph workflow."""
        logger.info("Building Eva conversation graph")
        
        # Create the graph
        workflow = StateGraph(EvaState)
        
        # Add nodes
        workflow.add_node("plan", plan_node)
        workflow.add_node("act", act_node)
        workflow.add_node("reflect", reflect_node)
        
        # Define the flow
        workflow.add_edge(START, "plan")
        workflow.add_edge("plan", "act")
        
        # Conditional edge from act node
        workflow.add_conditional_edges(
            "act",
            self._should_continue_acting,
            {
                "continue": "act",    # Loop back to act if more steps
                "reflect": "reflect"  # Move to reflect when done
            }
        )
        
        # Conditional edge from reflect node
        workflow.add_conditional_edges(
            "reflect",
            self._should_end,
            {
                "end": END,          # End if response is ready
                "continue": "act"    # Back to act if more actions needed
            }
        )
        
        # Compile the graph
        self.graph = workflow
        self.app = workflow.compile(checkpointer=self.checkpointer)
        
        logger.info("Eva conversation graph built successfully")
    
    def _should_continue_acting(self, state: EvaState) -> Literal["continue", "reflect"]:
        """
        Determine if we should continue acting or move to reflection.
        
        Continue acting if:
        - There are more steps in the plan
        - We haven't hit the step limit
        
        Args:
            state: Current conversation state
            
        Returns:
            "continue" to keep acting, "reflect" to move to reflection
        """
        # Check if there are more steps in the plan
        if state["current_step"] < len(state["eva_plan"]):
            logger.info(f"Continuing to act: step {state['current_step']} of {len(state['eva_plan'])}")
            return "continue"
        
        # All steps completed, move to reflection
        logger.info("All plan steps completed, moving to reflection")
        return "reflect"
    
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
        
        # Continue if more actions are explicitly needed
        # This is rare but can happen if reflection determines more work is needed
        logger.info("Continuing processing based on reflection")
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
                "conversation_id": eva_state.get("conversation_id", conversation_id),
                "needs_confirmation": eva_state.get("needs_confirmation", False),
                "confirmation_message": eva_state.get("confirmation_message", ""),
                "request_type": eva_state.get("request_type", "unknown"),
                "completed": eva_state.get("response_ready", True),
                "metadata": {
                    "plan_steps": len(eva_state.get("eva_plan", [])),
                    "completed_steps": eva_state.get("current_step", 0),
                    "tool_calls": len(eva_state.get("completed_tool_calls", []))
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