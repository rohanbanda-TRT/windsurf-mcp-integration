from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import logging
import uuid
from typing import Dict, List, Any, Optional
import asyncio

# Import our custom modules
from tools import tool_registry, get_all_tools, get_tool_handler
from windsurf_integration import WindsurfIntegration, WindsurfRequest, WindsurfResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-server")

# Initialize FastAPI app
app = FastAPI(
    title="MCP Server for Windsurf",
    description="Master Control Program server that provides additional tools for Windsurf IDE",
    version="0.1.0",
)

# Add CORS middleware to allow requests from Windsurf
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active connections
active_connections: Dict[str, WebSocket] = {}

# Initialize Windsurf integration
windsurf = WindsurfIntegration()

# Models
class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    request_id: str = ""

class ToolResponse(BaseModel):
    request_id: str
    status: str
    result: Any
    error: Optional[str] = None

# Register tools with Windsurf integration
@app.on_event("startup")
async def startup_event():
    # Register all tools from the tool registry with Windsurf integration
    for name, tool_info in tool_registry.items():
        try:
            handler = get_tool_handler(name)
            windsurf.register_tool(
                name=tool_info["name"],
                description=tool_info["description"],
                parameters=tool_info["parameters"],
                handler=handler
            )
        except Exception as e:
            logger.error(f"Error registering tool {name}: {str(e)}")
    
    logger.info(f"MCP Server started with {len(tool_registry)} tools registered")

# Routes
@app.get("/")
async def root():
    """Root endpoint that returns basic server information"""
    return {
        "name": "MCP Server for Windsurf",
        "status": "running",
        "version": "0.1.0",
        "tools_count": len(tool_registry)
    }

@app.get("/tools")
async def get_tools():
    """Get a list of all registered tools"""
    return {
        "tools": get_all_tools()
    }

@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: Dict[str, Any]):
    """Execute a tool by name with the provided parameters"""
    if tool_name not in tool_registry:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        handler = get_tool_handler(tool_name)
        result = await handler(request)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing tool: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication with Windsurf"""
    await websocket.accept()
    
    # Generate a unique client ID
    client_id = str(uuid.uuid4())
    active_connections[client_id] = websocket
    
    logger.info(f"Client connected: {client_id}")
    
    try:
        # Send available tools to the client upon connection
        await websocket.send_json({
            "type": "tools_list",
            "data": {
                "tools": windsurf.get_tools_schema()
            }
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.info(f"Received message from client {client_id}: {message.get('type', 'unknown')}")
                
                if message.get("type") == "tool_request":
                    request_data = message.get("data", {})
                    request_id = request_data.get("request_id")
                    tool_name = request_data.get("tool_name")
                    params = request_data.get("parameters", {})
                    
                    if not tool_name:
                        await websocket.send_json({
                            "type": "tool_response",
                            "data": {
                                "request_id": request_id,
                                "error": "No tool specified"
                            }
                        })
                        continue
                    
                    logger.info(f"Tool request from client {client_id}: {tool_name}")
                    
                    # Execute the tool
                    try:
                        result = await windsurf.execute_tool(tool_name, params)
                        logger.info(f"Tool {tool_name} executed successfully")
                        
                        # Send the result back to the client
                        await websocket.send_json({
                            "type": "tool_response",
                            "data": {
                                "request_id": request_id,
                                "result": result
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {str(e)}")
                        await websocket.send_json({
                            "type": "tool_response",
                            "data": {
                                "request_id": request_id,
                                "error": f"Error executing tool: {str(e)}"
                            }
                        })
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {str(e)}")
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
        del active_connections[client_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8089, reload=True)