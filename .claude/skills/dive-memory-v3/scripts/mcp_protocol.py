"""
Model Context Protocol (MCP) Implementation
JSON-RPC based protocol for AI agent communication
"""

import json
import sys
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod


@dataclass
class Tool:
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    handler: Callable


@dataclass
class Resource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mimeType: str
    handler: Callable


@dataclass
class Prompt:
    """MCP Prompt template"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]
    handler: Callable


class MCPServer(ABC):
    """Base MCP Server implementation"""
    
    def __init__(self, name: str, version: str, description: str):
        self.name = name
        self.version = version
        self.description = description
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.prompts: Dict[str, Prompt] = {}
    
    def add_tool(self, tool: Tool):
        """Register a tool"""
        self.tools[tool.name] = tool
    
    def add_resource(self, resource: Resource):
        """Register a resource"""
        self.resources[resource.uri] = resource
    
    def add_prompt(self, prompt: Prompt):
        """Register a prompt"""
        self.prompts[prompt.name] = prompt
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_tools_list()
            elif method == "tools/call":
                result = await self.handle_tools_call(params)
            elif method == "resources/list":
                result = await self.handle_resources_list()
            elif method == "resources/read":
                result = await self.handle_resources_read(params)
            elif method == "prompts/list":
                result = await self.handle_prompts_list()
            elif method == "prompts/get":
                result = await self.handle_prompts_get(params)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True}
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
    
    async def handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in self.tools.values()
            ]
        }
    
    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        result = await tool.handler(arguments)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }
    
    async def handle_resources_list(self) -> Dict[str, Any]:
        """Handle resources/list request"""
        return {
            "resources": [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description,
                    "mimeType": resource.mimeType
                }
                for resource in self.resources.values()
            ]
        }
    
    async def handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        
        if uri not in self.resources:
            raise ValueError(f"Unknown resource: {uri}")
        
        resource = self.resources[uri]
        content = await resource.handler()
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.mimeType,
                    "text": content
                }
            ]
        }
    
    async def handle_prompts_list(self) -> Dict[str, Any]:
        """Handle prompts/list request"""
        return {
            "prompts": [
                {
                    "name": prompt.name,
                    "description": prompt.description,
                    "arguments": prompt.arguments
                }
                for prompt in self.prompts.values()
            ]
        }
    
    async def handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if prompt_name not in self.prompts:
            raise ValueError(f"Unknown prompt: {prompt_name}")
        
        prompt = self.prompts[prompt_name]
        content = await prompt.handler(arguments)
        
        return {
            "description": prompt.description,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": content
                    }
                }
            ]
        }
    
    def run(self):
        """Run MCP server (stdio transport)"""
        import asyncio
        
        async def process_requests():
            while True:
                try:
                    # Read JSON-RPC request from stdin
                    line = sys.stdin.readline()
                    if not line:
                        break
                    
                    request = json.loads(line)
                    response = await self.handle_request(request)
                    
                    # Write JSON-RPC response to stdout
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    
                except Exception as e:
                    sys.stderr.write(f"Error: {e}\n")
                    sys.stderr.flush()
        
        asyncio.run(process_requests())
