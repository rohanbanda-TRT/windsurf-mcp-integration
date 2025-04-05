"""
Windsurf client for connecting to the MCP server.
This module provides a client for connecting to the MCP server from Windsurf.
"""

import logging
import json
import asyncio
import websockets
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Awaitable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("windsurf-client")

class WindsurfMCPClient:
    """
    Client for connecting to the MCP server from Windsurf
    """
    def __init__(self, server_url: str = "ws://localhost:8089/ws"):
        """
        Initialize the client
        
        Args:
            server_url: URL of the MCP server WebSocket endpoint
        """
        self.server_url = server_url
        self.websocket = None
        self.tools = []
        self.connected = False
        self.request_callbacks: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        logger.info(f"Initialized Windsurf MCP client for server: {server_url}")
    
    async def connect(self) -> bool:
        """
        Connect to the MCP server
        
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MCP server at {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            
            # Wait for the tools list message
            tools_message = await self.websocket.recv()
            tools_data = json.loads(tools_message)
            
            if tools_data.get("type") != "tools_list":
                logger.error(f"Expected tools_list message, got {tools_data.get('type')}")
                await self.disconnect()
                return False
            
            self.tools = tools_data.get("data", {}).get("tools", [])
            logger.info(f"Connected to MCP server, received {len(self.tools)} tools")
            
            # Start the message listener
            asyncio.create_task(self._message_listener())
            
            self.connected = True
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {str(e)}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.connected = False
            logger.info("Disconnected from MCP server")
    
    async def _message_listener(self) -> None:
        """Listen for messages from the MCP server"""
        try:
            while self.websocket and not self.websocket.closed:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                message_type = data.get("type")
                logger.info(f"Received message of type: {message_type}")
                
                if message_type == "tool_response":
                    response_data = data.get("data", {})
                    request_id = response_data.get("request_id")
                    
                    if request_id in self.request_callbacks:
                        callback = self.request_callbacks.pop(request_id)
                        await callback(response_data)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.connected = False
        
        except Exception as e:
            logger.error(f"Error in message listener: {str(e)}")
            self.connected = False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get the list of available tools from the MCP server
        
        Returns:
            List of tools with their metadata
        """
        return self.tools
    
    def get_tool_names(self) -> List[str]:
        """
        Get the names of available tools
        
        Returns:
            List of tool names
        """
        return [tool.get("name") for tool in self.tools]
    
    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a tool by name
        
        Args:
            name: Name of the tool
            
        Returns:
            Tool metadata if found, None otherwise
        """
        for tool in self.tools:
            if tool.get("name") == name:
                return tool
        return None
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server
        
        Args:
            tool_name: Name of the tool to call
            parameters: Parameters to pass to the tool
            
        Returns:
            Result from the tool execution
            
        Raises:
            ValueError: If the tool is not found
            ConnectionError: If not connected to the MCP server
        """
        if not self.connected or not self.websocket:
            raise ConnectionError("Not connected to MCP server")
        
        # Check if the tool exists
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Create a future to wait for the response
        response_future = asyncio.Future()
        
        # Register a callback for this request
        async def response_callback(response_data: Dict[str, Any]) -> None:
            if "error" in response_data:
                response_future.set_exception(Exception(response_data["error"]))
            else:
                response_future.set_result(response_data.get("result"))
        
        self.request_callbacks[request_id] = response_callback
        
        # Create the request message
        request = {
            "type": "tool_request",
            "data": {
                "request_id": request_id,
                "tool_name": tool_name,
                "parameters": parameters
            }
        }
        
        # Send the request
        await self.websocket.send(json.dumps(request))
        logger.info(f"Sent tool request: {tool_name}")
        
        # Wait for the response with timeout
        try:
            result = await asyncio.wait_for(response_future, timeout=30.0)
            logger.info(f"Received response for tool: {tool_name}")
            return result
        
        except asyncio.TimeoutError:
            # Remove the callback if we time out
            self.request_callbacks.pop(request_id, None)
            raise TimeoutError(f"Timeout waiting for response from tool '{tool_name}'")

async def get_mcp_client(server_url: str = "ws://localhost:8089/ws") -> WindsurfMCPClient:
    """
    Get a connected MCP client
    
    Args:
        server_url: URL of the MCP Server
        
    Returns:
        Connected MCP client
        
    Raises:
        ConnectionError: If connection fails
    """
    client = WindsurfMCPClient(server_url)
    if not await client.connect():
        raise ConnectionError(f"Failed to connect to MCP Server at {server_url}")
    
    return client

async def execute_tool_from_windsurf(tool_name: str, params: Dict[str, Any], server_url: str = "ws://localhost:8089/ws") -> Any:
    """
    Execute a tool from Windsurf via the MCP server
    
    This function handles the entire lifecycle of a tool execution:
    1. Connects to the MCP server
    2. Gets the list of available tools
    3. Executes the requested tool
    4. Returns the result
    5. Disconnects from the server
    
    Args:
        tool_name: Name of the tool to execute
        params: Parameters to pass to the tool
        server_url: URL of the MCP Server
        
    Returns:
        Result from the tool execution
    """
    # Create a new WebSocket connection for this request
    websocket_connection = None
    try:
        # Connect to the MCP server
        websocket_connection = await websockets.connect(server_url)
        logger.info(f"Connected to MCP Server at {server_url}")
        
        # Wait for the tools list
        tools_message = await websocket_connection.recv()
        tools_data = json.loads(tools_message)
        
        if tools_data.get("type") != "tools_list":
            raise Exception(f"Expected tools_list message, got {tools_data.get('type')}")
        
        tools = tools_data.get("data", {}).get("tools", [])
        logger.info(f"Received {len(tools)} tools from MCP Server")
        
        # Check if the requested tool exists
        tool_exists = False
        for tool in tools:
            if tool.get("name") == tool_name:
                tool_exists = True
                break
                
        if not tool_exists:
            raise Exception(f"Tool '{tool_name}' not found in MCP Server")
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Create the request message
        request = {
            "type": "tool_request",
            "data": {
                "request_id": request_id,
                "tool_name": tool_name,
                "parameters": params
            }
        }
        
        # Send the request
        await websocket_connection.send(json.dumps(request))
        logger.info(f"Sent tool request: {tool_name}")
        
        # Set a timeout for the response
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        # Wait for the response with timeout
        while time.time() - start_time < timeout:
            try:
                # Set a timeout for each receive operation
                response_message = await asyncio.wait_for(
                    websocket_connection.recv(), 
                    timeout=5.0
                )
                
                response_data = json.loads(response_message)
                logger.info(f"Received response type: {response_data.get('type')}")
                
                if response_data.get("type") == "tool_response" and response_data.get("data", {}).get("request_id") == request_id:
                    # Check for error
                    if "error" in response_data.get("data", {}):
                        error_msg = response_data.get("data", {}).get("error")
                        logger.error(f"Tool execution error: {error_msg}")
                        return {"error": error_msg}
                    
                    # Return the result
                    return response_data.get("data", {}).get("result")
            
            except asyncio.TimeoutError:
                # Continue the loop if we haven't exceeded the total timeout
                continue
        
        # If we get here, we've timed out
        raise Exception(f"Timeout waiting for response from tool '{tool_name}'")
    
    except Exception as e:
        logger.error(f"Error executing tool '{tool_name}': {str(e)}")
        return {"error": str(e)}
    
    finally:
        # Always close the WebSocket connection
        if websocket_connection:
            await websocket_connection.close()
            logger.info("Disconnected from MCP Server")

# Example usage in Windsurf
async def windsurf_example():
    """Example of how to use the MCP client from Windsurf"""
    try:
        # Connect to the MCP Server
        client = await get_mcp_client()
        
        # Get available tools
        tools = client.get_available_tools()
        print(f"Available tools: {', '.join(client.get_tool_names())}")
        
        # Call the file_search tool
        result = await client.call_tool("file_search", {
            "directory": "/path/to/project",
            "pattern": "*.py"
        })
        
        print(f"Found {result.get('count', 0)} files")
        
        # Disconnect from the MCP Server
        await client.disconnect()
    
    except Exception as e:
        print(f"Error: {str(e)}")

# For testing outside of Windsurf
if __name__ == "__main__":
    asyncio.run(windsurf_example())