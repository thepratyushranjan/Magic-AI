import os
import sys
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from first_agent import root_agent


# --- Base setup ---
AGENT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(AGENT_DIR)  # Ensure your local agent.py can be imported


# --- Initialize FastAPI app ---
app: FastAPI = get_fast_api_app(
    allow_origins=["*"],  # CORS settings
    web=True,  # Enables web-friendly mode
    agents_dir=AGENT_DIR,
)


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
        "tools": [t.__name__ for t in root_agent.tools],
    }


# --- Entry point ---
if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )
