"""
MCP HTTP tool for Eva Assistant.

Generic tool for calling remote MCP (Model Context Protocol) endpoints
and other HTTP services. Useful for integrating with external APIs.
"""

import json
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
import httpx

from eva_assistant.tools.base import ToolABC

logger = logging.getLogger(__name__)


# Pydantic schema for MCP HTTP arguments

class MCPArgs(BaseModel):
    """Arguments for calling remote MCP endpoints."""
    endpoint: str = Field(..., description="HTTP endpoint URL to call")
    payload: Dict[str, Any] = Field(..., description="JSON payload to send")
    method: str = Field(default="POST", description="HTTP method (GET, POST, PUT, DELETE)")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers")
    timeout: int = Field(default=20, description="Request timeout in seconds")


# MCP Tool Implementation

class MCPTool(ToolABC):
    """Generic tool for calling remote MCP endpoints and HTTP services."""
    
    name = "mcp_call"
    description = "Call a remote MCP endpoint and return JSON response"
    schema = MCPArgs
    returns = lambda r: json.dumps(r) if isinstance(r, dict) else str(r)
    
    async def run(self, args: MCPArgs) -> Dict[str, Any]:
        """Make HTTP request to remote endpoint."""
        try:
            # Set default headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Eva-Assistant/1.0",
                **args.headers
            }
            
            async with httpx.AsyncClient() as client:
                # Make the HTTP request
                if args.method.upper() == "GET":
                    response = await client.get(
                        args.endpoint,
                        headers=headers,
                        timeout=args.timeout
                    )
                elif args.method.upper() == "POST":
                    response = await client.post(
                        args.endpoint,
                        json=args.payload,
                        headers=headers,
                        timeout=args.timeout
                    )
                elif args.method.upper() == "PUT":
                    response = await client.put(
                        args.endpoint,
                        json=args.payload,
                        headers=headers,
                        timeout=args.timeout
                    )
                elif args.method.upper() == "DELETE":
                    response = await client.delete(
                        args.endpoint,
                        headers=headers,
                        timeout=args.timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {args.method}")
                
                # Check response status
                response.raise_for_status()
                
                # Parse response
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    result = response.text
                
                logger.info(f"MCP call successful: {args.endpoint} -> {response.status_code}")
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'data': result,
                    'endpoint': args.endpoint,
                    'method': args.method.upper()
                }
                
        except httpx.TimeoutException:
            logger.error(f"MCP call timeout: {args.endpoint}")
            return {
                'success': False,
                'error': f"Request timeout after {args.timeout} seconds",
                'endpoint': args.endpoint,
                'method': args.method.upper()
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP call HTTP error: {args.endpoint} -> {e.response.status_code}")
            return {
                'success': False,
                'error': f"HTTP {e.response.status_code}: {e.response.text}",
                'status_code': e.response.status_code,
                'endpoint': args.endpoint,
                'method': args.method.upper()
            }
            
        except Exception as e:
            logger.error(f"MCP call failed: {args.endpoint} -> {e}")
            return {
                'success': False,
                'error': str(e),
                'endpoint': args.endpoint,
                'method': args.method.upper()
            } 