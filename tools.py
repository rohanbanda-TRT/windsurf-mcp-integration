"""
Custom tools for the MCP Server that can be integrated with Windsurf.
Add your custom tool implementations here.
"""

import logging
from typing import Dict, Any, Callable, Awaitable, List
import httpx
import asyncio
import json
import os
from pathlib import Path

logger = logging.getLogger("mcp-tools")

# Type definition for tool handlers
ToolHandler = Callable[[Dict[str, Any]], Awaitable[Any]]

# Registry of tool handlers
tool_registry: Dict[str, Dict[str, Any]] = {}

def register_tool(name: str, description: str, parameters: Dict[str, Any]) -> Callable:
    """
    Decorator to register a new tool with the MCP server
    
    Example:
    @register_tool(
        name="file_search",
        description="Search for files in a directory",
        parameters={
            "directory": {"type": "string", "description": "Directory to search in"},
            "pattern": {"type": "string", "description": "Search pattern"}
        }
    )
    async def file_search_handler(params: Dict[str, Any]) -> Any:
        # Implementation
        pass
    """
    def decorator(func: ToolHandler) -> ToolHandler:
        tool_registry[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": func.__name__
        }
        logger.info(f"Registered tool: {name}")
        return func
    return decorator

# Example tool implementations

@register_tool(
    name="file_search",
    description="Search for files in a directory",
    parameters={
        "directory": {"type": "string", "description": "Directory to search in"},
        "pattern": {"type": "string", "description": "Search pattern (glob format)"}
    }
)
async def file_search_handler(params: Dict[str, Any]) -> Any:
    """Search for files matching a pattern in a directory"""
    directory = params.get("directory", ".")
    pattern = params.get("pattern", "*")
    
    try:
        # Use pathlib for cross-platform compatibility
        path = Path(directory)
        if not path.exists():
            return {"error": f"Directory '{directory}' does not exist"}
        
        # Find files matching the pattern
        files = list(path.glob(pattern))
        
        # Convert Path objects to strings and include file info
        result = []
        for file in files:
            try:
                stat = file.stat()
                result.append({
                    "path": str(file),
                    "name": file.name,
                    "is_dir": file.is_dir(),
                    "size": stat.st_size if file.is_file() else None,
                    "modified": stat.st_mtime
                })
            except Exception as e:
                logger.error(f"Error getting file info for {file}: {str(e)}")
        
        return {"files": result, "count": len(result)}
    
    except Exception as e:
        logger.error(f"Error in file_search: {str(e)}")
        return {"error": str(e)}

@register_tool(
    name="code_analysis",
    description="Analyze code in a file or directory",
    parameters={
        "path": {"type": "string", "description": "Path to file or directory to analyze"},
        "analysis_type": {"type": "string", "description": "Type of analysis to perform (syntax, complexity, dependencies)"}
    }
)
async def code_analysis_handler(params: Dict[str, Any]) -> Any:
    """Analyze code in a file or directory"""
    path = params.get("path", "")
    analysis_type = params.get("analysis_type", "syntax")
    
    if not path:
        return {"error": "No path provided"}
    
    try:
        file_path = Path(path)
        if not file_path.exists():
            return {"error": f"Path '{path}' does not exist"}
        
        # Simple file info analysis
        if file_path.is_file():
            extension = file_path.suffix.lower()
            
            # Read file content for analysis
            try:
                content = file_path.read_text(errors='replace')
                lines = content.splitlines()
                
                result = {
                    "file": str(file_path),
                    "size": file_path.stat().st_size,
                    "lines": len(lines),
                    "extension": extension,
                }
                
                # Perform specific analysis based on type
                if analysis_type == "syntax":
                    # Basic syntax analysis (just counting for now)
                    result.update({
                        "empty_lines": sum(1 for line in lines if not line.strip()),
                        "comment_lines": sum(1 for line in lines if line.strip().startswith(('#', '//', '/*', '*', '*/')) if line.strip()),
                        "code_lines": sum(1 for line in lines if line.strip() and not line.strip().startswith(('#', '//', '/*', '*', '*/')))
                    })
                
                elif analysis_type == "complexity":
                    # Simple complexity metrics
                    result.update({
                        "avg_line_length": sum(len(line) for line in lines) / max(len(lines), 1),
                        "max_line_length": max((len(line) for line in lines), default=0),
                        "function_count": sum(1 for line in lines if "def " in line or "function " in line)
                    })
                
                elif analysis_type == "dependencies":
                    # Simple dependency extraction for Python
                    if extension == ".py":
                        imports = [line.strip() for line in lines if line.strip().startswith(("import ", "from "))]
                        result["imports"] = imports
                    # For JavaScript/TypeScript
                    elif extension in [".js", ".ts", ".jsx", ".tsx"]:
                        imports = [line.strip() for line in lines if "import " in line or "require(" in line]
                        result["imports"] = imports
                
                return result
            
            except Exception as e:
                logger.error(f"Error reading or analyzing file {path}: {str(e)}")
                return {"error": f"Error analyzing file: {str(e)}"}
        
        # Directory analysis
        elif file_path.is_dir():
            # Count files by type
            file_types = {}
            total_size = 0
            file_count = 0
            
            for child in file_path.glob("**/*"):
                if child.is_file():
                    file_count += 1
                    total_size += child.stat().st_size
                    ext = child.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                "directory": str(file_path),
                "file_count": file_count,
                "total_size": total_size,
                "file_types": file_types
            }
        
        return {"error": "Unknown path type"}
    
    except Exception as e:
        logger.error(f"Error in code_analysis: {str(e)}")
        return {"error": str(e)}

@register_tool(
    name="web_request",
    description="Make HTTP requests to external APIs",
    parameters={
        "url": {"type": "string", "description": "URL to send the request to"},
        "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE)"},
        "headers": {"type": "object", "description": "HTTP headers to include"},
        "data": {"type": "object", "description": "Data to send in the request body"}
    }
)
async def web_request_handler(params: Dict[str, Any]) -> Any:
    """Make HTTP requests to external APIs"""
    url = params.get("url")
    method = params.get("method", "GET").upper()
    headers = params.get("headers", {})
    data = params.get("data")
    
    if not url:
        return {"error": "No URL provided"}
    
    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data, timeout=30.0)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, timeout=30.0)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
            
            # Try to parse JSON response
            try:
                json_response = response.json()
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "json": json_response
                }
            except:
                # Return text response if not JSON
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "text": response.text
                }
    
    except Exception as e:
        logger.error(f"Error in web_request: {str(e)}")
        return {"error": str(e)}

@register_tool(
    name="github_list_repos",
    description="List repositories for a GitHub user",
    parameters={
        "username": {"type": "string", "description": "GitHub username (optional, uses default if not provided)"},
        "per_page": {"type": "integer", "description": "Number of repositories per page (default: 30)"},
        "page": {"type": "integer", "description": "Page number (default: 1)"}
    }
)
async def github_list_repos_handler(params: Dict[str, Any]) -> Any:
    """List repositories for a GitHub user"""
    # Get username from parameters or use environment variable as default
    username = params.get("username")
    if not username:
        username = os.environ.get("GITHUB_USERNAME")
        logger.info(f"Using default GitHub username from environment: {username}")
    
    per_page = params.get("per_page", 30)
    page = params.get("page", 1)
    
    logger.info(f"Fetching GitHub repositories for user: {username}")
    
    if not username:
        logger.error("No username provided for github_list_repos and no default username in environment")
        return {"error": "No username provided and no default username configured"}
    
    try:
        # GitHub API endpoint for user repositories
        url = f"https://api.github.com/users/{username}/repos"
        logger.info(f"Making request to GitHub API: {url}")
        
        # Make the request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params={
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated"
                },
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "MCP-Server-Windsurf"
                },
                timeout=30.0
            )
            
            logger.info(f"GitHub API response status code: {response.status_code}")
            
            if response.status_code == 200:
                repos = response.json()
                logger.info(f"Found {len(repos)} repositories for user {username}")
                
                # Extract relevant information
                result = []
                for repo in repos:
                    result.append({
                        "name": repo.get("name"),
                        "full_name": repo.get("full_name"),
                        "description": repo.get("description"),
                        "html_url": repo.get("html_url"),
                        "language": repo.get("language"),
                        "stars": repo.get("stargazers_count"),
                        "forks": repo.get("forks_count"),
                        "updated_at": repo.get("updated_at"),
                        "private": repo.get("private")
                    })
                
                return {
                    "repositories": result,
                    "count": len(result),
                    "page": page,
                    "per_page": per_page
                }
            else:
                error_message = response.json().get("message", "Unknown error")
                logger.error(f"GitHub API error: {error_message}")
                return {
                    "error": f"GitHub API returned status code {response.status_code}",
                    "message": error_message
                }
    
    except Exception as e:
        logger.error(f"Error in github_list_repos: {str(e)}")
        return {"error": str(e)}

# Get all registered tools
def get_all_tools() -> List[Dict[str, Any]]:
    """Get all registered tools with their metadata"""
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"]
        }
        for tool in tool_registry.values()
    ]

# Get a specific tool handler by name
def get_tool_handler(name: str) -> ToolHandler:
    """Get a tool handler function by name"""
    if name not in tool_registry:
        raise ValueError(f"Tool '{name}' not registered")
    
    handler_name = tool_registry[name]["handler"]
    # Get the handler function from the current module's globals
    handler = globals().get(handler_name)
    if not handler:
        raise ValueError(f"Handler function '{handler_name}' not found")
    
    return handler