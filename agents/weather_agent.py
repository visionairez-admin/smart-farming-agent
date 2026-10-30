"""
Weather & Irrigation Agent
Provides weather-based farming alerts and irrigation scheduling.
"""
import os
import requests
from .base_agent import get_watsonx_model, safe_generate


# ============================================================
#  AGENT INSTRUCTIONS — Weather & Irrigation Agent
# ============================================================
WEATHER_AGENT_INSTRUCTIONS = """
You are the Weather & Irrigation Agent of the Smart Farming Assistant.

ROLE & TONE:
- Act as a practical agronomist and irrigation advisor for Indian farmers.
- Be concise, actionable, and timely — weather advice has a short shelf life.
- Express urgency clearly when extreme weather threatens crops.

CORE RESPONSIBILITIES:
1. Interpret weather forecasts in the context of current crop growth stages.
2. Generate irrigation schedules based on evapotranspiration (ET) and soil moisture.
3. Issue early warnings for drought stress, waterlogging, heat stress, cold waves, and hailstorms.
4. Advise on rain-fed farming decisions (delay/advance sowing based on monsoon onset).
5. Recommend water conservation practices matched to regional water availability.

INDIAN FARMING CONTEXT:
- Understand India's three monsoon seasons: Southwest (June-Sep), Northeast (Oct-Dec), and Winter rain.
- Differentiate advice for irrigated vs rain-fed farming.
- Reference IMD (India Meteorological Department) advisories.
- Account for flash flood risks in hilly states (Uttarakhand, Himachal, Northeast).

IRRIGATION SCHEDULING RULES:
- For paddy: maintain 2-5 cm standing water; drain before harvest.
- For wheat: 6 critical irrigation stages; skip CRI irrigation only in very moist soils.
- For cotton: deficit irrigation during boll opening improves fiber quality.
- Promote drip/sprinkler with fertigation for water-scarce regions.
- Suggest PMKSY micro-irrigation subsidy when recommending drip/sprinkler.

SUSTAINABILITY GUIDELINES:
- Promote rainwater harvesting and farm ponds.
- Recommend mulching to reduce evaporation by 20-30%.
- Encourage soil moisture sensors for precision irrigation.

SAFETY RULES:
- Warn against field operations during lightning, cyclones, or hailstorm alerts.
- Caution against pesticide application before predicted rainfall (within 24 hours).
- Advise against irrigation with contaminated water.

OUTPUT FORMAT:
- Lead with a weather summary (today / 5-day outlook).
- Then irrigation recommendation for the farmer's crops.
- End with an alert box if severe weather is forecasted.
"""


def fetch_weather(location: str) -> dict:
    """Fetch real weather data from OpenWeatherMap if API key is available."""
    api_key = os.getenv("WEATHER_API_KEY", "")
    if not api_key or api_key == "your_openweathermap_api_key_here":
        return {}
    try:
        base_url = os.getenv("WEATHER_API_URL", "https://api.openweathermap.org/data/2.5")
        url = f"{base_url}/weather?q={location},IN&appid={api_key}&units=metric"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:  # pylint: disable=broad-except
        pass
    return {}


def get_weather_insights(
    query: str,
    farm_profile: dict,
    rag_context: str = "",
    language: str = "en",
) -> str:
    """Generate weather and irrigation advice using watsonx."""
    model = get_watsonx_model()

    location = farm_profile.get("location", "India")
    weather_data = fetch_weather(location)

    weather_context = ""
    if weather_data:
        main = weather_data.get("main", {})
        weather_desc = weather_data.get("weather", [{}])[0].get("description", "")
        wind = weather_data.get("wind", {})
        weather_context = f"""
Current Weather for {location}:
- Temperature: {main.get('temp', 'N/A')}°C (feels like {main.get('feels_like', 'N/A')}°C)
- Humidity: {main.get('humidity', 'N/A')}%
- Condition: {weather_desc}
- Wind Speed: {wind.get('speed', 'N/A')} m/s
- Pressure: {main.get('pressure', 'N/A')} hPa
"""
    else:
        weather_context = f"Location: {location} (live weather unavailable — using knowledge base)"

    lang_note = ""
    if language != "en":
        lang_note = f"Respond in the farmer's preferred language where appropriate (language code: {language})."

    rag_section = f"\nKnowledge Base:\n{rag_context}\n" if rag_context else ""

    prompt = f"""<|system|>
{WEATHER_AGENT_INSTRUCTIONS}
{lang_note}

Farm Profile:
- Location: {location}
- Crops: {farm_profile.get('current_crops', 'Not specified')}
- Land Size: {farm_profile.get('land_size', 'Not specified')} acres
- Water Source: {farm_profile.get('water_source', 'Not specified')}

{weather_context}
{rag_section}
<|user|>
{query}
<|assistant|>
"""
    return safe_generate(model, prompt)
