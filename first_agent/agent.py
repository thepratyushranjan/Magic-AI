import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.genai import Client
import json
import uuid
import google.genai.types as types
from google.adk.tools import FunctionTool
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.agents import LlmAgent

# Mock tool implementation
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": f"(AI will determine the time in {city})"}

async def generic_visualization_tool(tool_context, input_json: str) -> str:
    try:
        data = json.loads(input_json)
    except Exception:
        return "Error: Invalid JSON input."

    if not isinstance(data, (list, dict)) or not data:
        return "Error: Input must be a non-empty JSON object or array."

    return f" html: Ai will generate the html"

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

artifact_instructions = """
The assistant can create and reference artifacts during conversations.

  - Visualize by Default: All results must be shown with a modern visual artifact (charts, KPI cards, or tables).
  - Design Style: Use a clean aesthetic: white/neutral backgrounds, rounded corners, soft shadows, and the 'Inter' Google Font for all text.
  - Technology: Generate visualizations using only HTML, CSS (Tailwind), and vanilla JavaScript.
  - Layout: Use Flexbox/Grid for responsive layouts suitable for A4-sized PDFs.
  - Header & Footer:
    - Add Logo URL: "https://motointel-socialmedia.s3.ap-south-1.amazonaws.com/maigic_logo.png" on the top right.
    - Add footer text: "Powered by Maigic.Ai".
  - UI Elements & Charting:
    - Prefer charts over tables. Use KPI cards with Lucide icons for key metrics.
    - Prioritize ApexCharts for all visualizations.
  - Key Chart Styling Rules:
    - Line Charts: Use smooth curves (curve: 'smooth') and a line thickness of 3 (stroke: { width: 3 }).
    - Aesthetics: Use a transparent chart background, light gray or hidden grid lines, and a professional color palette (e.g., indigo, emerald, amber).
    - Fonts: Ensure all chart text (labels, tooltips) also uses the 'Inter' font.
    - Use intuitive colors for alerts/trends (green for positive, red for negative).
  - Required CDNs:
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lucide@latest"></script>
  <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>

"""

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description="generate artifacts for data visualization.",
    instruction=(
        "1. Generate visual artifacts (HTML visualizations) for any provided data.\n"
        "2.Please generate a complete and self-contained HTML page (including <html>, <head>, <body>) that presents this data (table + possible chart if applicable) and is ready to be saved as an artifact.\n\n"
        "3. artifact_instructions: " + artifact_instructions + "\n\n"
        "Use 'generic_visualization_tool' for visualization artifacts."
    ),
    tools=[generic_visualization_tool],
)
  