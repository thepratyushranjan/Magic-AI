import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
print(f"Loaded environment variables from .env file: {os.listdir('../')}")

# Get API key from environment variable
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not set. "
        "Please set it with: export GOOGLE_API_KEY='your-api-key-here'"
    )

# --- Define the MCP Server URL ---
MCP_SERVER_URL = 'http://localhost:8888/mcp'

# --- Instantiate the Remote MCP Tool Registry ---
# The Agent will connect to this URL and discover the tools (like get_current_time)
# provided by the 'web_search_mcp' server.
# mcp_tool_registry = ToolRegistry(url=MCP_SERVER_URL)


root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description="Tells the current time in a specified city by calling a remote MCP service.",
    instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool provided by the remote MCP server for this purpose.",
    tools=[MCPToolset(connection_params=StreamableHTTPServerParams(url=MCP_SERVER_URL))],
)

print(f"Agent '{root_agent.name}' is now configured to use the MCP tool registry at: {MCP_SERVER_URL}")