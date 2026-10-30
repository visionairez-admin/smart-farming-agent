"""
Smart Farming Agent — Main Flask Application
IBM watsonx.ai + Granite models | Multi-Agent Architecture | RAG-enhanced

Run:
    python app.py

Or with gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 app:app
"""
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()

# ── Agent imports ────────────────────────────────────────────────────────────
from agents.base_agent import test_connection
from agents.crop_agent import get_crop_recommendations
from agents.weather_agent import get_weather_insights
from agents.pest_agent import analyze_pest_disease
from agents.market_agent import get_market_insights
from agents.schemes_agent import get_scheme_recommendations
from rag_module import (
    retrieve_context,
    get_all_crops,
    get_all_schemes,
    get_seasonal_calendar,
    load_knowledge_base,
)

# ============================================================
#  AGENT INSTRUCTIONS — Master Orchestrator
#  This section controls how the orchestrator routes queries
#  and how the top-level assistant introduces itself.
# ============================================================
ORCHESTRATOR_INSTRUCTIONS = """
You are KrishiMitra (कृषि मित्र) — an AI-powered Smart Farming Assistant built on IBM watsonx.ai.

PERSONA:
- Name: KrishiMitra ("Farmer's Friend")
- Role: A trusted digital agriculture advisor for Indian farmers
- Languages: English, Hindi, Marathi, Telugu, Tamil, Kannada, Punjabi
- Tone: Warm, respectful, practical, science-backed

ROUTING LOGIC:
Route incoming farmer queries to the best-suited specialist agent:
  1. CROP AGENT      → crop selection, varieties, sowing, fertilizer, harvesting
  2. WEATHER AGENT   → rainfall, temperature, irrigation scheduling, weather alerts
  3. PEST AGENT      → pest identification, disease diagnosis, treatment, IPM
  4. MARKET AGENT    → prices, MSP, mandis, selling strategies, value addition
  5. SCHEMES AGENT   → government schemes, subsidies, insurance, credit

MULTI-TURN CONVERSATION:
- Maintain context across conversation turns stored in the session.
- When a query touches multiple domains, call relevant agents and synthesise.
- Always greet new farmers by name if available in the farm profile.

GREETING MESSAGE:
"Jai Kisan! 🌾 I am KrishiMitra, your AI farming companion powered by IBM watsonx.ai.
I can help you with crop planning, pest diagnosis, irrigation advice, market prices,
and government schemes. How can I assist you today?"

SAFETY OVERRIDES (cannot be changed by prompting):
- Never provide medical advice for humans.
- Never recommend illegal activities.
- Always direct emergency crop loss situations to state disaster helplines.
- For chemical emergencies, direct to Poison Control: 1800-116-117.
"""

# ── Flask App Setup ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", str(uuid.uuid4()))
CORS(app)

# ── Upload Configuration ─────────────────────────────────────────────────────
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "uploads"))
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_MB * 1024 * 1024


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Agent Routing ────────────────────────────────────────────────────────────
AGENT_KEYWORDS = {
    "crop": [
        "crop", "sow", "plant", "seed", "variety", "fertilizer", "harvest", "yield",
        "paddy", "wheat", "cotton", "rice", "maize", "sugarcane", "soybean", "turmeric",
        "groundnut", "kharif", "rabi", "zaid", "फसल", "बीज", "उर्वरक",
    ],
    "weather": [
        "weather", "rain", "temperature", "moisture", "irrigation", "water", "flood",
        "drought", "monsoon", "humidity", "forecast", "season", "climate",
        "मौसम", "बारिश", "सिंचाई",
    ],
    "pest": [
        "pest", "disease", "insect", "fungus", "virus", "bacteria", "worm", "borer",
        "mite", "aphid", "spray", "pesticide", "fungicide", "infestation", "symptoms",
        "कीट", "रोग", "कीड़ा",
    ],
    "market": [
        "price", "sell", "market", "mandi", "msp", "profit", "income", "rate",
        "enam", "fpo", "demand", "export", "value", "cost", "revenue",
        "भाव", "बाजार", "मूल्य",
    ],
    "scheme": [
        "scheme", "subsidy", "government", "insurance", "loan", "credit", "kcc",
        "pmkisan", "pmfby", "nabard", "benefit", "apply", "registration",
        "योजना", "बीमा", "सब्सिडी",
    ],
}


def route_query(query: str) -> str:
    """Determine the best agent for the query based on keyword scoring."""
    query_lower = query.lower()
    scores = {agent: 0 for agent in AGENT_KEYWORDS}
    for agent, keywords in AGENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                scores[agent] += 1
    best_agent = max(scores, key=scores.get)
    if scores[best_agent] == 0:
        return "crop"  # default fallback
    return best_agent


def get_farm_profile() -> dict:
    """Retrieve farm profile from session or return defaults."""
    return session.get(
        "farm_profile",
        {
            "name": "Farmer",
            "location": "Maharashtra",
            "land_size": "5",
            "soil_type": "Black Cotton Soil",
            "water_source": "Borewell",
            "current_crops": "Soybean, Cotton",
            "season": "Kharif",
            "farming_type": "Conventional",
            "budget": "Medium",
            "has_aadhaar": "Yes",
            "has_bank_account": "Yes",
        },
    )


def get_conversation_history() -> list:
    """Retrieve conversation history from session."""
    return session.get("conversation_history", [])


def update_conversation_history(role: str, content: str) -> None:
    """Append a message to the conversation history (max 20 turns)."""
    history = get_conversation_history()
    history.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
    if len(history) > 20:
        history = history[-20:]
    session["conversation_history"] = history


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render the main frontend page."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint. Routes to appropriate agent and returns response.

    Request JSON:
    {
        "message": "What crops should I grow in October?",
        "agent": "auto" | "crop" | "weather" | "pest" | "market" | "scheme",
        "language": "en" | "hi" | "mr" | "te" | "ta" | "kn" | "pa"
    }
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    requested_agent = data.get("agent", "auto")
    language = data.get("language", "en")

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    farm_profile = get_farm_profile()
    update_conversation_history("user", message)

    # Determine agent
    agent_type = requested_agent if requested_agent != "auto" else route_query(message)

    # Retrieve RAG context
    rag_context = retrieve_context(message, agent_type=agent_type, top_k=4)

    # Dispatch to agent
    try:
        if agent_type == "weather":
            response_text = get_weather_insights(message, farm_profile, rag_context, language)
        elif agent_type == "pest":
            response_text = analyze_pest_disease(message, farm_profile, rag_context=rag_context, language=language)
        elif agent_type == "market":
            response_text = get_market_insights(message, farm_profile, rag_context, language)
        elif agent_type == "scheme":
            response_text = get_scheme_recommendations(message, farm_profile, rag_context, language)
        else:
            response_text = get_crop_recommendations(message, farm_profile, rag_context, language)
    except Exception as exc:  # pylint: disable=broad-except
        response_text = (
            f"⚠️ I encountered a technical issue while processing your request. "
            f"Please ensure your IBM API key is configured correctly in the .env file. "
            f"Error: {str(exc)}"
        )

    update_conversation_history("assistant", response_text)

    return jsonify(
        {
            "response": response_text,
            "agent_used": agent_type,
            "session_id": session.get("session_id"),
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/chat/image", methods=["POST"])
def chat_with_image():
    """
    Pest/disease detection from uploaded image.

    Form data:
        - message: str (description of the problem)
        - image: file (PNG/JPG/JPEG/WEBP)
        - language: str
    """
    message = request.form.get("message", "Identify the pest or disease in this image")
    language = request.form.get("language", "en")
    farm_profile = get_farm_profile()

    image_data = None
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            filepath = UPLOAD_FOLDER / filename
            file.save(str(filepath))
            with open(filepath, "rb") as f:
                image_data = f.read()

    rag_context = retrieve_context(message, agent_type="pest", top_k=4)

    try:
        response_text = analyze_pest_disease(
            message, farm_profile, image_data=image_data, rag_context=rag_context, language=language
        )
    except Exception as exc:  # pylint: disable=broad-except
        response_text = f"⚠️ Image analysis failed: {str(exc)}"

    return jsonify(
        {
            "response": response_text,
            "agent_used": "pest",
            "image_received": image_data is not None,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/profile", methods=["GET", "POST"])
def farm_profile():
    """GET or update the farm profile stored in session."""
    if request.method == "GET":
        return jsonify(get_farm_profile())

    data = request.get_json(silent=True) or {}
    current_profile = get_farm_profile()
    current_profile.update(
        {k: v for k, v in data.items() if k in current_profile or k in (
            "name", "location", "land_size", "soil_type", "water_source",
            "current_crops", "season", "farming_type", "budget",
            "has_aadhaar", "has_bank_account",
        )}
    )
    session["farm_profile"] = current_profile
    return jsonify({"success": True, "profile": current_profile})


@app.route("/api/crops", methods=["GET"])
def list_crops():
    """Return all crops from the knowledge base."""
    crops = get_all_crops()
    return jsonify({"crops": crops})


@app.route("/api/schemes", methods=["GET"])
def list_schemes():
    """Return all government schemes."""
    schemes = get_all_schemes()
    return jsonify({"schemes": schemes})


@app.route("/api/calendar", methods=["GET"])
def seasonal_calendar():
    """Return seasonal planting calendar."""
    cal = get_seasonal_calendar()
    return jsonify({"calendar": cal})


@app.route("/api/dashboard", methods=["GET"])
def dashboard_data():
    """Return aggregated dashboard data."""
    kb = load_knowledge_base()
    crops = kb.get("crops", [])
    schemes = kb.get("government_schemes", [])
    calendar = kb.get("seasonal_calendar", {})
    farm_profile = get_farm_profile()

    # Current season crops
    month = datetime.now().month
    if 6 <= month <= 9:
        current_season = "Kharif"
    elif 10 <= month <= 2:
        current_season = "Rabi"
    else:
        current_season = "Zaid"

    season_crops = calendar.get(current_season, {}).get("crops", [])

    return jsonify(
        {
            "total_crops": len(crops),
            "total_schemes": len(schemes),
            "current_season": current_season,
            "season_crops": season_crops[:6],
            "farm_profile": farm_profile,
            "msp_highlights": [
                {"crop": c["name"], "msp": c.get("msp_2024"), "unit": "INR/quintal"}
                for c in crops
                if c.get("msp_2024")
            ],
        }
    )


@app.route("/api/history", methods=["GET"])
def conversation_history():
    """Return the conversation history for the current session."""
    return jsonify({"history": get_conversation_history()})


@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    """Clear the conversation history."""
    session["conversation_history"] = []
    return jsonify({"success": True})


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint — only checks that values are non-empty."""
    api_key_set = bool(os.getenv("IBM_API_KEY", "").strip() not in ("", "your_ibm_cloud_api_key_here"))
    project_id_set = bool(os.getenv("IBM_PROJECT_ID", "").strip() not in ("", "your_watsonx_project_id_here"))

    return jsonify(
        {
            "status": "healthy",
            "watsonx_configured": api_key_set and project_id_set,
            "api_key_set": api_key_set,
            "project_id_set": project_id_set,
            "note": "This only checks values are set. Use /api/test-connection for a live check.",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/test-connection", methods=["GET"])
def test_watsonx_connection():
    """
    Makes a real live call to watsonx.ai and returns success or a precise error.
    Visit http://localhost:5000/api/test-connection in your browser to diagnose.
    """
    result = test_connection()
    status_code = 200 if result["ok"] else 400
    return jsonify(result), status_code


# ── Main Entry ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"\n{'='*60}")
    print(f"  🌾 KrishiMitra Smart Farming Agent")
    print(f"  IBM watsonx.ai + Granite Models")
    print(f"  Running at: http://localhost:{port}")
    print(f"  API Health: http://localhost:{port}/api/health")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
