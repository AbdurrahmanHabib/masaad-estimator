#!/usr/bin/env python3
"""
Dive-Memory v3 MCP Server
Model Context Protocol server for persistent memory management
"""

import json
import sys
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dive_memory import DiveMemory
from mcp_protocol import MCPServer, Tool, Resource, Prompt


class DiveMemoryMCPServer(MCPServer):
    """MCP Server for Dive-Memory v3"""
    
    def __init__(self):
        super().__init__(
            name="dive-memory",
            version="3.0.0",
            description="Persistent memory system for AI agents"
        )
        
        # Initialize memory system
        self.memory = DiveMemory()
        
        # Register tools
        self.register_tools()
        self.register_resources()
        self.register_prompts()
    
    def register_tools(self):
        """Register MCP tools"""
        
        # Memory Add Tool
        self.add_tool(Tool(
            name="memory_add",
            description="Add a new memory with metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content"},
                    "section": {"type": "string", "description": "Memory section"},
                    "subsection": {"type": "string", "description": "Memory subsection (optional)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Importance score"},
                    "metadata": {"type": "object", "description": "Additional metadata"}
                },
                "required": ["content", "section"]
            },
            handler=self.handle_memory_add
        ))
        
        # Memory Search Tool
        self.add_tool(Tool(
            name="memory_search",
            description="Search memories using semantic + keyword search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "section": {"type": "string", "description": "Filter by section"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    "top_k": {"type": "integer", "default": 10, "description": "Number of results"}
                },
                "required": ["query"]
            },
            handler=self.handle_memory_search
        ))
        
        # Memory Update Tool
        self.add_tool(Tool(
            name="memory_update",
            description="Update existing memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Memory ID"},
                    "content": {"type": "string", "description": "New content"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 10},
                    "metadata": {"type": "object"}
                },
                "required": ["memory_id"]
            },
            handler=self.handle_memory_update
        ))
        
        # Memory Delete Tool
        self.add_tool(Tool(
            name="memory_delete",
            description="Delete memory by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Memory ID"}
                },
                "required": ["memory_id"]
            },
            handler=self.handle_memory_delete
        ))
        
        # Memory Graph Tool
        self.add_tool(Tool(
            name="memory_graph",
            description="Get knowledge graph for section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {"type": "string", "description": "Section to visualize"},
                    "max_depth": {"type": "integer", "default": 2, "description": "Graph depth"}
                }
            },
            handler=self.handle_memory_graph
        ))
        
        # Memory Related Tool
        self.add_tool(Tool(
            name="memory_related",
            description="Find related memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Memory ID"},
                    "max_depth": {"type": "integer", "default": 2, "description": "Relationship depth"}
                },
                "required": ["memory_id"]
            },
            handler=self.handle_memory_related
        ))
        
        # Memory Stats Tool
        self.add_tool(Tool(
            name="memory_stats",
            description="Get memory statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {"type": "string", "description": "Filter by section"}
                }
            },
            handler=self.handle_memory_stats
        ))
    
    def register_resources(self):
        """Register MCP resources"""
        
        # Memory sections resource
        self.add_resource(Resource(
            uri="dive-memory://sections",
            name="Memory Sections",
            description="List of all memory sections",
            mimeType="application/json",
            handler=self.handle_sections_resource
        ))
        
        # Knowledge graph resource
        self.add_resource(Resource(
            uri="dive-memory://graph",
            name="Knowledge Graph",
            description="Complete knowledge graph",
            mimeType="application/json",
            handler=self.handle_graph_resource
        ))
    
    def register_prompts(self):
        """Register MCP prompts"""
        
        # Context injection prompt
        self.add_prompt(Prompt(
            name="context_for_task",
            description="Get relevant context for a task",
            arguments=[
                {"name": "task", "description": "Task description", "required": True}
            ],
            handler=self.handle_context_prompt
        ))
    
    # Tool Handlers
    
    async def handle_memory_add(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_add tool"""
        try:
            memory_id = self.memory.add(
                content=arguments["content"],
                section=arguments["section"],
                subsection=arguments.get("subsection"),
                tags=arguments.get("tags", []),
                importance=arguments.get("importance", 5),
                metadata=arguments.get("metadata", {})
            )
            return {
                "success": True,
                "memory_id": memory_id,
                "message": f"Memory added successfully: {memory_id}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_memory_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_search tool"""
        try:
            results = self.memory.search(
                query=arguments["query"],
                section=arguments.get("section"),
                tags=arguments.get("tags"),
                top_k=arguments.get("top_k", 10)
            )
            return {
                "success": True,
                "count": len(results),
                "results": [
                    {
                        "id": r.id,
                        "content": r.content,
                        "section": r.section,
                        "tags": r.tags,
                        "importance": r.importance,
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in results
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_memory_update(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_update tool"""
        try:
            self.memory.update(
                memory_id=arguments["memory_id"],
                content=arguments.get("content"),
                tags=arguments.get("tags"),
                importance=arguments.get("importance"),
                metadata=arguments.get("metadata")
            )
            return {
                "success": True,
                "message": f"Memory updated: {arguments['memory_id']}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_memory_delete(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_delete tool"""
        try:
            self.memory.delete(arguments["memory_id"])
            return {
                "success": True,
                "message": f"Memory deleted: {arguments['memory_id']}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_memory_graph(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_graph tool"""
        try:
            graph = self.memory.get_graph(
                section=arguments.get("section"),
                max_depth=arguments.get("max_depth", 2)
            )
            return {
                "success": True,
                "graph": graph
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_memory_related(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_related tool"""
        try:
            related = self.memory.get_related(
                memory_id=arguments["memory_id"],
                max_depth=arguments.get("max_depth", 2)
            )
            return {
                "success": True,
                "count": len(related),
                "related": [
                    {
                        "id": r.id,
                        "content": r.content,
                        "relationship": r.relationship,
                        "strength": r.strength
                    }
                    for r in related
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_memory_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_stats tool"""
        try:
            stats = self.memory.get_stats(section=arguments.get("section"))
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Resource Handlers
    
    async def handle_sections_resource(self) -> str:
        """Handle sections resource"""
        sections = self.memory.get_sections()
        return json.dumps(sections, indent=2)
    
    async def handle_graph_resource(self) -> str:
        """Handle graph resource"""
        graph = self.memory.get_graph()
        return json.dumps(graph, indent=2)
    
    # Prompt Handlers
    
    async def handle_context_prompt(self, arguments: Dict[str, Any]) -> str:
        """Handle context_for_task prompt"""
        context = self.memory.get_context_for_task(arguments["task"])
        return context


def main():
    """Main entry point"""
    server = DiveMemoryMCPServer()
    server.run()


if __name__ == "__main__":
    main()
