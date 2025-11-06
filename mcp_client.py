"""
MCP Client utility supporting multiple transport types:
- SSE (Server-Sent Events)
- Stdio (Local process)
- HTTP (Streamable HTTP)
"""
import os
from typing import List, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


class MCPClientManager:
    """Manages MCP client connections and tool registration."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.tools: List = []
        self.exit_stack = AsyncExitStack()
        self.transport_type: Optional[str] = None
    
    async def initialize(self, connection_string: str):
        """
        Initialize MCP client based on connection string format.
        
        Supported formats:
        - SSE: https://server.com/sse or http://server.com/sse
        - Stdio: stdio://path/to/executable or just /path/to/executable
        - HTTP: Will use SSE by default for HTTP/HTTPS URLs
        """
        if not connection_string:
            raise ValueError("Connection string is required")
        
        try:
            # Determine transport type from connection string
            if connection_string.startswith('stdio://'):
                await self._initialize_stdio(connection_string.replace('stdio://', ''))
            elif connection_string.startswith('http://') or connection_string.startswith('https://'):
                await self._initialize_sse(connection_string)
            elif os.path.exists(connection_string):
                # Local file path - use stdio
                await self._initialize_stdio(connection_string)
            else:
                raise ValueError(
                    f"Unable to determine transport type for: {connection_string}\n"
                    "Supported formats: https://server.com/sse, stdio://path/to/exe, or /path/to/exe"
                )
            
            # Initialize session
            await self.session.initialize()
            
            # List and register tools
            tools_list = await self.session.list_tools()
            print(f"Connected via {self.transport_type}. Found {len(tools_list.tools)} MCP tools:")
            
            for tool in tools_list.tools:
                print(f"  - {tool.name}: {tool.description}")
                self.tools.append(self._create_tool_wrapper(tool))
            
            return self.tools
            
        except Exception as e:
            print(f"Error initializing MCP client: {e}")
            raise
    
    async def _initialize_sse(self, url: str):
        """Initialize SSE (Server-Sent Events) transport."""
        print(f"Initializing SSE transport to: {url}")
        self.transport_type = "SSE"
        
        read, write = await self.exit_stack.enter_async_context(
            sse_client(url)
        )
        
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
    
    async def _initialize_stdio(self, command_path: str, args: List[str] = None):
        """Initialize Stdio (local process) transport."""
        print(f"Initializing Stdio transport for: {command_path}")
        self.transport_type = "Stdio"
        
        server_params = StdioServerParameters(
            command=command_path,
            args=args or [],
            env=None
        )
        
        read, write = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
    
    def _create_tool_wrapper(self, tool_info):
        """Create a wrapper function for an MCP tool."""
        async def mcp_tool(**kwargs):
            """Execute MCP tool and return results."""
            try:
                result = await self.session.call_tool(
                    tool_info.name,
                    arguments=kwargs
                )
                
                # Handle different result content types
                if hasattr(result, 'content'):
                    if isinstance(result.content, list):
                        # Multiple content items
                        content = [
                            item.text if hasattr(item, 'text') else str(item)
                            for item in result.content
                        ]
                    else:
                        content = result.content
                else:
                    content = str(result)
                
                return {
                    "status": "success",
                    "tool": tool_info.name,
                    "result": content
                }
            except Exception as e:
                return {
                    "status": "error",
                    "tool": tool_info.name,
                    "error": str(e)
                }
        
        # Set function metadata for ADK
        mcp_tool.__name__ = tool_info.name
        mcp_tool.__doc__ = tool_info.description or f"MCP tool: {tool_info.name}"
        
        # Add input schema if available
        if hasattr(tool_info, 'inputSchema'):
            mcp_tool.__annotations__ = self._parse_input_schema(tool_info.inputSchema)
        
        return mcp_tool
    
    def _parse_input_schema(self, schema: dict) -> dict:
        """Parse JSON schema to Python type annotations."""
        annotations = {}
        if 'properties' in schema:
            for prop_name, prop_info in schema['properties'].items():
                # Simple type mapping
                type_map = {
                    'string': str,
                    'integer': int,
                    'number': float,
                    'boolean': bool,
                    'array': list,
                    'object': dict
                }
                prop_type = prop_info.get('type', 'string')
                annotations[prop_name] = type_map.get(prop_type, str)
        return annotations
    
    async def cleanup(self):
        """Cleanup MCP client connections."""
        print(f"Closing MCP {self.transport_type} connection...")
        await self.exit_stack.aclose()
        print("MCP connection closed")
    
    def get_tools(self) -> List:
        """Return list of registered MCP tools."""
        return self.tools
    
    def get_tool_info(self) -> List[dict]:
        """Return information about registered tools."""
        return [
            {
                "name": tool.__name__,
                "description": tool.__doc__,
                "transport": self.transport_type
            }
            for tool in self.tools
        ]