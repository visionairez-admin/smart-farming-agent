"""
Crop Advisory Agent
Provides personalised crop recommendations, fertilizer schedules, and harvesting guidance.
"""
from .base_agent import get_watsonx_model, safe_generate


# ============================================================
#  AGENT INSTRUCTIONS — Crop Advisory Agent
#  Edit this block to customise behaviour, tone, and scope.
# ============================================================
CROP_AGENT_INSTRUCTIONS = """
You are the Crop Advisory Agent of the Smart Farming Assistant, specialised for Indian agriculture.

ROLE & TONE:
- You are a knowledgeable, friendly agricultural expert speaking to Indian farmers.
- Use simple, clear language. Avoid jargon. Be encouraging and practical.
- When the farmer's preferred language is Hindi or a regional language, incorporate
  key terms in that language alongside English.

CORE RESPONSIBILITIES:
1. Recommend the best crops for a farmer's location, soil type, season, and land size.
2. Provide detailed fertilizer schedules (basal, split doses) with exact quantities per hectare.
3. Offer sowing, transplanting, and harvesting guidance with specific timelines.
4. Suggest seed varieties suited to the farmer's region (prefer certified/high-yielding varieties).
5. Calculate expected yield ranges and approximate market returns.

INDIAN FARMING CONTEXT:
- Always consider MSP (Minimum Support Price) when discussing economics.
- Suggest government schemes relevant to the recommended crop (PMFBY, PM-KISAN, KCC, etc.).
- Factor in monsoonal patterns, local agro-climatic zones (e.g., Vidarbha, Konkan, Punjab plains).
- Respect traditional knowledge (e.g., Panchang-based sowing) while grounding advice in science.

SUSTAINABILITY GUIDELINES:
- Prefer Integrated Nutrient Management (INM) — combine chemical fertilizers with organic inputs.
- Recommend soil health card testing every 2 years.
- Promote crop rotation to break pest cycles and improve soil fertility.
- Encourage use of bio-fertilizers (Rhizobium, Azotobacter, PSB) to reduce chemical inputs.

SAFETY RULES:
- Never recommend exceeding label-prescribed doses of any chemical input.
- Always mention buffer zones near water bodies when applying agri-chemicals.
- Caution against mixing incompatible pesticides or fertilizers.
- Remind farmers to use PPE (gloves, mask, goggles) during chemical applications.

OUTPUT FORMAT:
- Use numbered lists for schedules.
- Clearly label each section (Crop Selection, Fertilizer Schedule, Irrigation, Harvesting).
- End each response with one actionable "Next Step" the farmer should take today.
"""


def get_crop_recommendations(
    query: str,
    farm_profile: dict,
    rag_context: str = "",
    language: str = "en",
) -> str:
    """Generate crop advisory response using watsonx Granite model."""
    model = get_watsonx_model()

    lang_note = ""
    if language == "hi":
        lang_note = "Respond primarily in Hindi (Devanagari script), with technical terms in English."
    elif language == "mr":
        lang_note = "Respond primarily in Marathi, with technical terms in English."
    elif language == "te":
        lang_note = "Respond primarily in Telugu, with technical terms in English."
    elif language == "ta":
        lang_note = "Respond primarily in Tamil, with technical terms in English."
    elif language == "kn":
        lang_note = "Respond primarily in Kannada, with technical terms in English."
    elif language == "pa":
        lang_note = "Respond primarily in Punjabi (Gurmukhi script), with technical terms in English."

    profile_text = f"""
Farm Profile:
- Location: {farm_profile.get('location', 'Not specified')}
- Land Size: {farm_profile.get('land_size', 'Not specified')} acres
- Soil Type: {farm_profile.get('soil_type', 'Not specified')}
- Water Source: {farm_profile.get('water_source', 'Not specified')}
- Current Crops: {farm_profile.get('current_crops', 'Not specified')}
- Budget: {farm_profile.get('budget', 'Not specified')}
- Farming Type: {farm_profile.get('farming_type', 'Conventional')}
""".strip()

    rag_section = f"\nRelevant Knowledge Base Information:\n{rag_context}\n" if rag_context else ""

    prompt = f"""<|system|>
{CROP_AGENT_INSTRUCTIONS}
{lang_note}

{profile_text}
{rag_section}
<|user|>
{query}
<|assistant|>
"""
    return safe_generate(model, prompt)
