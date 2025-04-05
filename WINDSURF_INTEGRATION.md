# Integrating MCP Server with Windsurf

This guide explains how to integrate the MCP (Master Control Program) server with Windsurf to access additional tools that aren't built into Windsurf.

## Prerequisites

1. MCP server running (on port 8089 by default)
2. Windsurf IDE

## Integration Steps

### 1. Start the MCP Server

Make sure the MCP server is running:

```bash
cd /path/to/MCP_servers
source venv/bin/activate
python main.py
```

### 2. Import the Windsurf Client in Your Windsurf Project

Copy the `windsurf_client.py` file to your Windsurf project or import it directly from the MCP server directory.

### 3. Use the MCP Tools in Your Windsurf Project

Here's an example of how to use the MCP tools in your Windsurf project:

```python
import asyncio
from windsurf_client import execute_tool_from_windsurf

# Example: Use the file_search tool
async def search_files():
    try:
        result = await execute_tool_from_windsurf(
            "file_search",
            {
                "directory": "/path/to/search",
                "pattern": "*.py"
            },
            server_url="ws://localhost:8089/ws"
        )
        
        print(f"Found {result.get('count', 0)} files")
        for file in result.get("files", []):
            print(f"- {file['path']}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

# Run the async function
asyncio.run(search_files())
```

### 4. Available Tools

The MCP server provides the following tools:

1. **file_search**: Search for files in a directory
   - Parameters:
     - `directory`: Directory to search in
     - `pattern`: Search pattern (glob format)

2. **code_analysis**: Analyze code in a file or directory
   - Parameters:
     - `path`: Path to file or directory to analyze
     - `analysis_type`: Type of analysis (syntax, complexity, dependencies)

3. **web_request**: Make HTTP requests to external APIs
   - Parameters:
     - `url`: URL to send the request to
     - `method`: HTTP method (GET, POST, PUT, DELETE)
     - `headers`: HTTP headers (optional)
     - `data`: Request body data (optional)

## Adding Custom Tools

You can add custom tools to the MCP server by modifying the `tools.py` file. See the README.md for more information.

## Troubleshooting

1. **Connection Issues**: Make sure the MCP server is running and accessible from Windsurf
2. **Tool Errors**: Check the MCP server logs for error messages
3. **WebSocket Errors**: Verify that the WebSocket URL is correct (ws://localhost:8089/ws)