import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.tools import load_memory
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner

# Application constants
APP_NAME = "first_agent"
USER_ID = "default_user"

# Mock tool implementation
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": "10:30 AM"}

# Load environment variables from .env file in parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
print(f"Loaded environment variables from .env file: {os.listdir('../')}")

# Get API key from environment variable
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not set. "
        "Please set it with: export GOOGLE_API_KEY='your-api-key-here'"
    )

# Define the root agent with memory capabilities
root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description="A helpful assistant that can tell the current time and remember past conversations.",
    instruction="""You are a helpful assistant that can:
    1. Tell the current time in cities using the 'get_current_time' tool
    2. Remember information from past conversations using the 'load_memory' tool
    
    When a user asks about something you discussed before, use the load_memory tool to search past conversations.
    Be conversational and remember context from the current session naturally.""",
    tools=[get_current_time, load_memory],
)

# Initialize Services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# Initialize Runner
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
    memory_service=memory_service
)

# Optional: Callback to auto-save sessions to long-term memory
async def auto_save_session_to_memory_callback(callback_context):
    """Automatically save completed sessions to long-term memory."""
    try:
        await callback_context._invocation_context.memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )
        print(f"Session saved to long-term memory")
    except Exception as e:
        print(f"Error saving session to memory: {e}")

# Agent with auto-save callback
root_agent.after_agent_callback = auto_save_session_to_memory_callback