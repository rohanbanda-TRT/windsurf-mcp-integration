"""
Windsurf integration module for the MCP Server.
This module handles the integration between the MCP server and Windsurf.
"""

import logging
from typing import Dict, Any, Callable, Awaitable, List, Optional
import json

logger = logging.getLogger("windsurf-integration")

class WindsurfRequest:
    """
    Represents a request from Windsurf to the MCP server
    """
    def __init__(self, tool_name: str, parameters: Dict[str, Any], request_id: str = ""):
        self.tool_name = tool_name
        self.parameters = parameters
        self.request_id = request_id
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindsurfRequest':
        """Create a WindsurfRequest from a dictionary"""
        return cls(
            tool_name=data.get("tool_name", ""),
            parameters=data.get("parameters", {}),
            request_id=data.get("request_id", "")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "request_id": self.request_id
        }

class WindsurfResponse:
    """
    Represents a response from the MCP server to Windsurf
    """
    def __init__(self, request_id: str, result: Any = None, error: Optional[str] = None):
        self.request_id = request_id
        self.result = result
        self.error = error
    
    @property
    def status(self) -> str:
        """Get the status of the response"""
        return "error" if self.error else "success"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        response = {
            "request_id": self.request_id,
            "status": self.status,
        }
        
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
            
        return response

class WindsurfTool:
    """
    Represents a tool that can be used by Windsurf
    """
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
    
    def to_schema(self) -> Dict[str, Any]:
        """Convert to schema representation for Windsurf"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

class WindsurfIntegration:
    """
    Handles the integration between the MCP server and Windsurf
    """
    def __init__(self):
        self.tools: Dict[str, WindsurfTool] = {}
        logger.info("Windsurf integration initialized")
    
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        """
        Register a tool with the Windsurf integration
        
        Args:
            name: Name of the tool
            description: Description of the tool
            parameters: Parameters schema for the tool
            handler: Function that handles the tool execution
        """
        self.tools[name] = WindsurfTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )
        logger.info(f"Registered tool with Windsurf integration: {name}")
    
    def get_tool(self, name: str) -> Optional[WindsurfTool]:
        """
        Get a tool by name
        
        Args:
            name: Name of the tool
            
        Returns:
            The tool if found, None otherwise
        """
        return self.tools.get(name)
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Get the schema for all registered tools
        
        Returns:
            List of tool schemas
        """
        return [tool.to_schema() for tool in self.tools.values()]
    
    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with the provided parameters
        
        Args:
            name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Result of the tool execution
            
        Raises:
            ValueError: If the tool is not found
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        
        logger.info(f"Executing tool: {name}")
        try:
            result = await tool.handler(parameters)
            logger.info(f"Tool {name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            raise
    
    async def handle_request(self, request: WindsurfRequest) -> WindsurfResponse:
        """
        Handle a request from Windsurf
        
        Args:
            request: The request to handle
            
        Returns:
            Response to the request
        """
        try:
            if not request.tool_name:
                return WindsurfResponse(
                    request_id=request.request_id,
                    error="No tool specified"
                )
            
            logger.info(f"Handling request for tool: {request.tool_name}")
            
            result = await self.execute_tool(
                name=request.tool_name,
                parameters=request.parameters
            )
            
            return WindsurfResponse(
                request_id=request.request_id,
                result=result
            )
        
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return WindsurfResponse(
                request_id=request.request_id,
                error=str(e)
            )