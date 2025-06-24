"""
Tool base system for Eva Assistant.

Implements the ToolABC pattern with automatic registration via metaclass.
All tools inherit from ToolABC and are automatically discovered.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, List
from pydantic import BaseModel

# Global tool registry
_REGISTRY: Dict[str, "ToolABC"] = {}


class ToolMeta(type(ABC)):
    """Metaclass for automatic tool registration, compatible with ABC."""
    
    def __new__(mcls, name, bases, attrs):
        cls = super().__new__(mcls, name, bases, attrs)
        
        # Only register concrete tools (not the abstract base)
        if not attrs.get("abstract", False) and hasattr(cls, 'name') and not cls.__abstractmethods__:
            _REGISTRY[cls.name] = cls()
            
        return cls


class ToolABC(ABC, metaclass=ToolMeta):
    """
    Abstract base class for all Eva tools.
    
    All tools inherit from this and are automatically registered
    via the metaclass. Each tool must define:
    - name: Unique tool identifier
    - description: What the tool does
    - schema: Pydantic model for arguments
    - returns: Function to serialize results for LLM
    - run: Async method that executes the tool
    """
    
    abstract = True  # Keeps ABC itself out of registry
    
    name: str
    description: str
    schema: type[BaseModel]
    returns: Callable[[Any], str]
    
    @abstractmethod
    async def run(self, args: BaseModel) -> Any:
        """Execute the tool with validated arguments."""
        pass


def get_all_tools() -> Dict[str, "ToolABC"]:
    """Get all registered tools."""
    return _REGISTRY.copy()


def get_tool(name: str) -> "ToolABC":
    """Get a specific tool by name."""
    if name not in _REGISTRY:
        raise KeyError(f"Tool '{name}' not found. Available tools: {list(_REGISTRY.keys())}")
    return _REGISTRY[name]


def list_tool_names() -> list[str]:
    """Get list of all available tool names."""
    return list(_REGISTRY.keys())


def get_tool_schemas() -> Dict[str, Dict[str, Any]]:
    """Get schemas for all tools (useful for LLM tool calling)."""
    return {
        name: {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.schema.model_json_schema()
        }
        for name, tool in _REGISTRY.items()
    }


def convert_tools_to_litellm_format() -> List[Dict[str, Any]]:
    """
    Convert Eva's tools to LiteLLM/OpenAI tool calling format.
    
    Returns:
        List of tool definitions in OpenAI format for LiteLLM
    """
    tools = []
    
    for name, tool in _REGISTRY.items():
        # Convert to OpenAI tool calling format
        tool_def = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema.model_json_schema()
            }
        }
        tools.append(tool_def)
    
    return tools


async def execute_tool_call(tool_name: str, tool_args: Dict[str, Any], 
                          primary_user_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute a tool call with the given arguments and optional primary user context.
    
    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments to pass to the tool
        primary_user_context: Optional context about the primary user (timezone, email, etc.)
        
    Returns:
        Tool execution result
    """
    if tool_name not in _REGISTRY:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' not found. Available tools: {list(_REGISTRY.keys())}"
        }
    
    try:
        tool = _REGISTRY[tool_name]
        
        # Validate arguments using the tool's schema
        validated_args = tool.schema(**tool_args)
        
        # Execute the tool with optional context
        if primary_user_context and hasattr(tool, 'run_with_context'):
            # Tool supports context - pass it along
            result = await tool.run_with_context(validated_args, primary_user_context)
        else:
            # Standard tool execution
            result = await tool.run(validated_args)
        
        # Ensure result is serializable
        if not isinstance(result, dict):
            result = {"result": str(result)}
            
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "tool_name": tool_name,
            "args": tool_args
        } 