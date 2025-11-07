from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

FIRECRAWL_API_KEY = "fc-e8ece6efc78f440fb6df0fdff2f2c52d"

root_agent = Agent(
    model="gemini-2.5-pro",
    name="firecrawl_agent",
    description="A helpful assistant for scraping websites with Firecrawl",
    instruction="Help the user search for website content",
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPServerParams(
                url=f"https://mcp.firecrawl.dev/{FIRECRAWL_API_KEY}/v2/mcp",
            ),
        )
    ],
)