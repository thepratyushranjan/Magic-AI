import os
import asyncio
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.genai import Client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack

# Mock tool implementation
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": "10:30 AM"}

# Load environment variables from .env file in parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


# Get API key from environment variable
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not set. "
        "Please set it with: export GOOGLE_API_KEY='your-api-key-here'"
    )

# MCP Server Configuration
RAG_MCP_CONNECTION_STRING = os.getenv('RAG_MCP_CONNECTION_STRING')

# Global MCP session and tools
mcp_session = None
mcp_tools = []
exit_stack = AsyncExitStack()


async def initialize_mcp_client():
    """Initialize MCP client and retrieve available tools."""
    global mcp_session, mcp_tools, exit_stack
    
    if not RAG_MCP_CONNECTION_STRING:
        print("Warning: RAG_MCP_CONNECTION_STRING not set. Skipping MCP initialization.")
        return []
    
    try:
        # Connect to SSE MCP server
        print(f"Connecting to MCP server at: {RAG_MCP_CONNECTION_STRING}")
        
        # Use SSE client for Server-Sent Events transport
        read, write = await exit_stack.enter_async_context(
            sse_client(RAG_MCP_CONNECTION_STRING)
        )
        
        mcp_session = await exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        
        # Initialize the session
        await mcp_session.initialize()
        
        # List available tools from MCP server
        tools_list = await mcp_session.list_tools()
        print(f"Available MCP tools: {[tool.name for tool in tools_list.tools]}")
        
        # Create wrapper functions for each MCP tool
        for tool in tools_list.tools:
            mcp_tools.append(create_mcp_tool_wrapper(tool))
        
        return mcp_tools
        
    except Exception as e:
        print(f"Error initializing MCP client: {e}")
        return []


def create_mcp_tool_wrapper(tool_info):
    """Create a wrapper function for an MCP tool."""
    async def mcp_tool_wrapper(**kwargs):
        """Wrapper for MCP tool execution."""
        try:
            result = await mcp_session.call_tool(tool_info.name, arguments=kwargs)
            return {
                "status": "success",
                "tool": tool_info.name,
                "result": result.content
            }
        except Exception as e:
            return {
                "status": "error",
                "tool": tool_info.name,
                "error": str(e)
            }
    
    # Set function metadata
    mcp_tool_wrapper.__name__ = tool_info.name
    mcp_tool_wrapper.__doc__ = tool_info.description or f"MCP tool: {tool_info.name}"
    
    return mcp_tool_wrapper


async def cleanup_mcp_client():
    """Cleanup MCP client connections."""
    global exit_stack
    await exit_stack.aclose()


# Initialize MCP tools synchronously for agent creation
# Note: This is a workaround - ideally you'd initialize async at app startup
try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    mcp_tools = loop.run_until_complete(initialize_mcp_client())
except Exception as e:
    print(f"Failed to initialize MCP tools: {e}")
    mcp_tools = []

# Combine local tools with MCP tools
all_tools = [get_current_time] + mcp_tools

root_agent = Agent(
    model='gemini-2.5-pro',
    name='root_agent',
    description="Tells the current time in a specified city and provides access to MCP server tools.",
    instruction="""You are a helpful assistant that:
    1. Tells the current time in cities using the 'get_current_time' tool
    2. Has access to additional tools from the MCP server for enhanced capabilities
    
    Use the appropriate tool based on the user's request.""",
    tools=all_tools,
)