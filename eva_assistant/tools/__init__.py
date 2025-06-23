"""
Eva Assistant Tools Package.

Auto-discovers and exposes all tools via the ToolABC registry system.
Import this module to register all available tools.
"""

from eva_assistant.tools.base import (
    get_all_tools, 
    get_tool, 
    list_tool_names, 
    get_tool_schemas,
    convert_tools_to_litellm_format,
    execute_tool_call
)

# Import all tool modules to trigger auto-registration
try:
    from eva_assistant.tools import calendar
except ImportError:
    pass

try:
    from eva_assistant.tools import email
except ImportError:
    pass

try:
    from eva_assistant.tools import mcp_http
except ImportError:
    pass

# Export the registry functions
__all__ = [
    "get_all_tools",
    "get_tool", 
    "list_tool_names",
    "get_tool_schemas",
    "convert_tools_to_litellm_format",
    "execute_tool_call"
] 