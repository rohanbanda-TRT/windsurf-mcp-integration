# MCP Server for Windsurf

Master Control Program (MCP) server that provides additional tools for the Windsurf agentic IDE.

## Overview

This MCP server is designed to extend Windsurf's capabilities by providing additional tools that aren't built into Windsurf. It uses FastAPI to create a robust API server with WebSocket support for real-time communication with Windsurf.

## Features

- **FastAPI Backend**: High-performance, easy-to-use framework
- **WebSocket Support**: Real-time bidirectional communication
- **Extensible Tool System**: Easily add new tools to extend Windsurf
- **RESTful API**: HTTP endpoints for tool execution
- **Windsurf Integration**: Seamless integration with Windsurf IDE

## Project Structure

```
MCP_servers/
├── main.py                 # Main FastAPI application
├── tools.py                # Custom tool implementations
├── windsurf_integration.py # Windsurf integration module
├── requirements.txt        # Project dependencies
└── README.md               # Documentation
```

## Built-in Tools

The MCP server comes with several built-in tools:

1. **File Search**: Search for files in a directory with pattern matching
2. **Code Analysis**: Analyze code files for syntax, complexity, and dependencies
3. **Web Request**: Make HTTP requests to external APIs

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start the MCP server:
   ```
   python main.py
   ```
   This will start the server on http://localhost:8089

2. Connect Windsurf to the MCP server by configuring the WebSocket connection to:
   ```
   ws://localhost:8089/ws
   ```

3. Access the API documentation at http://localhost:8089/docs

## Adding Custom Tools

To add a new tool to the MCP server:

1. Open `tools.py`
2. Use the `@register_tool` decorator to register your tool:

```python
@register_tool(
    name="my_custom_tool",
    description="Description of what the tool does",
    parameters={
        "param1": {"type": "string", "description": "Description of parameter 1"},
        "param2": {"type": "integer", "description": "Description of parameter 2"}
    }
)
async def my_custom_tool_handler(params: Dict[str, Any]) -> Any:
    # Tool implementation
    param1 = params.get("param1", "")
    param2 = params.get("param2", 0)
    
    # Do something with the parameters
    result = f"Processed {param1} with value {param2}"
    
    return {"output": result}
```

## API Endpoints

- `GET /`: Server information
- `GET /tools`: List all available tools
- `POST /tools/{tool_name}`: Execute a specific tool
- `WebSocket /ws`: WebSocket endpoint for real-time communication

## License

MIT