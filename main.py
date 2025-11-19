import os
import sys
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.tools import load_memory
from google.genai.types import Content, Part

# --- Base setup ---
AGENT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(AGENT_DIR)

# Load environment variables
load_dotenv()

APP_NAME = "first_agent"  # Must match the agent directory name
USER_ID = "default_user"  # In production, use actual user IDs

# --- Define tools ---
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": "10:30 AM"}

# --- Create agent directly here ---
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

# --- Initialize Services ---
# These services manage short-term (session) and long-term (memory) storage
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()  # Use InMemoryMemoryService for prototyping

# --- Initialize Runner ---
# Runner orchestrates the agent with session and memory services
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
    memory_service=memory_service
)

# --- Initialize FastAPI app ---
app: FastAPI = get_fast_api_app(
    allow_origins=["*"],  # CORS settings
    web=True,  # Enables web-friendly mode
    agents_dir=AGENT_DIR,
)

# --- Pydantic Models for API ---
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = USER_ID

class ChatResponse(BaseModel):
    response: str
    session_id: str
    
class SessionInfo(BaseModel):
    session_id: str
    app_name: str
    user_id: str
    events_count: int

# --- Custom endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/agent-info")
async def agent_info():
    """Provide agent information"""
    return {
        "agent_name": root_agent.name,
        "description": root_agent.description,
        "model": root_agent.model,
        "tools": [t.__name__ if hasattr(t, '__name__') else str(t) for t in root_agent.tools],
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with short-term memory (session tracking).
    
    - If session_id is provided, continues existing conversation
    - If not provided, creates a new session
    """
    try:
        # Generate or use provided session ID
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
        print(f""" session id : {session_id} """)
        user_id = request.user_id
        
        # Check if session exists, if not create it
        try:
            existing_session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
        except:
            # Session doesn't exist, create it
            await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
        
        # Create user message content
        user_message = Content(
            parts=[Part(text=request.message)],
            role="user"
        )
        
        # Run the agent and collect the response
        final_response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            # Capture the final response
            if event.is_final_response() and event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
        
        return ChatResponse(
            response=final_response_text or "I'm sorry, I couldn't generate a response.",
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.post("/sessions/{session_id}/save-to-memory")
async def save_session_to_memory(session_id: str, user_id: str = USER_ID):
    """
    Manually save a session to long-term memory.
    Call this when a conversation is complete.
    """
    try:
        # Get the session
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        # Add to long-term memory
        await memory_service.add_session_to_memory(session)
        
        return {
            "status": "success",
            "message": f"Session {session_id} saved to long-term memory"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to memory: {str(e)}")

@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str, user_id: str = USER_ID):
    """Get information about a specific session"""
    try:
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        return SessionInfo(
            session_id=session.session_id,
            app_name=session.app_name,
            user_id=session.user_id,
            events_count=len(session.events)
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")

@app.post("/memory/search")
async def search_memory(query: str, user_id: str = USER_ID):
    """
    Search long-term memory for relevant information.
    This is what the agent does internally when using the load_memory tool.
    """
    try:
        results = await memory_service.search_memory(
            app_name=APP_NAME,
            user_id=user_id,
            query=query
        )
        
        # Extract text from results
        memories = []
        for memory_result in results.memories:
            if memory_result.content and memory_result.content.parts:
                for part in memory_result.content.parts:
                    if hasattr(part, 'text'):
                        memories.append(part.text)
        
        return {
            "query": query,
            "results": memories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching memory: {str(e)}")

# --- Entry point ---
if __name__ == "__main__":
    print("Starting FastAPI server with memory capabilities...")
    print(f"App Name: {APP_NAME}")
    print(f"Session Service: {type(session_service).__name__}")
    print(f"Memory Service: {type(memory_service).__name__}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )