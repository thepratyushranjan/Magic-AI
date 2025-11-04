# Magic-AI

## Overview
Simple FastAPI service that exposes an agent powered by Google GenAI. It requires a `GOOGLE_API_KEY` and runs a server on port `8000`.

## Prerequisites
- **Python**: 3.12+
- **pip**: bundled with Python 3.12
- **Google API Key**: for Gemini (`GOOGLE_API_KEY`)

## 1) Clone the repository
```bash
git clone https://github.com/thepratyushranjan/Magic-AI.git
cd Magic-AI
```

## 2) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
# On Windows (PowerShell): .venv\Scripts\Activate.ps1
```

## 3) Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Set your environment variables
Create a `.env` file in the project root with your Google API key:
```bash
echo "GOOGLE_API_KEY=your-api-key-here" > .env
```
Alternatively, export it in your shell:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## 5) Run the server
```bash
uv run main.py
```
The server starts at `http://0.0.0.0:8000`.

## 6) Verify the service
- Health check:
```bash
curl http://localhost:8000/health
```
- Agent info:
```bash
curl http://localhost:8000/agent-info
```

## Notes
- CORS is enabled for all origins by default.
- If you see an error about `GOOGLE_API_KEY` not set, ensure your `.env` exists in the project root or the variable is exported in your shell.
- To change the port, edit `port=8000` in `main.py`.

## Project Structure (simplified)
```
Magic-AI/
  main.py                # Starts FastAPI (uvicorn) server on port 8000
  first_agent/
    agent.py             # Defines the root agent and loads GOOGLE_API_KEY
  requirements.txt
  README.md
```
