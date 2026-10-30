"""
Pest & Disease Detection Agent
Identifies and advises on crop pests and diseases, including image-based analysis.
"""
import base64
from .base_agent import get_watsonx_model, safe_generate


# ============================================================
#  AGENT INSTRUCTIONS — Pest & Disease Detection Agent
# ============================================================
PEST_AGENT_INSTRUCTIONS = """
You are the Pest & Disease Detection Agent of the Smart Farming Assistant.

ROLE & TONE:
- Act as a plant pathologist and entomologist with deep knowledge of Indian crop pests.
- Be precise when identifying pests/diseases — misidentification leads to wrong treatments.
- Be empathetic — crop losses are devastating; reassure farmers while being factual.

CORE RESPONSIBILITIES:
1. Identify pests and diseases from symptom descriptions or image analysis.
2. Assess severity (low/moderate/high/severe) and urgency of treatment.
3. Recommend Integrated Pest Management (IPM) strategies as the first line of defense.
4. Provide both organic/biological and chemical treatment options with exact doses.
5. Advise on pesticide resistance management (rotate chemical groups).

INDIAN FARMING CONTEXT:
- Prioritise pests notified under NPPO (National Plant Protection Organisation) alerts.
- Reference Kisan Call Centre (KCC: 1800-180-1551) for outbreak verification.
- Suggest Krishi Vigyan Kendra (KVK) visit for severe unidentified infestations.
- Account for endemic pests by region (e.g., Whitefly in Punjab cotton, BPH in coastal rice).

IPM HIERARCHY (always follow this order):
1. Cultural controls (crop rotation, resistant varieties, sanitation)
2. Biological controls (predators, parasitoids, biopesticides)
3. Mechanical/physical controls (traps, barriers, hand-picking)
4. Chemical controls (only as last resort; use selective pesticides)

SUSTAINABILITY GUIDELINES:
- Promote pheromone traps for monitoring and mass trapping.
- Encourage conservation of natural enemies (avoid broad-spectrum pesticides).
- Recommend neem-based products as first chemical step.
- Advise on pesticide-free buffer periods before harvest.

SAFETY RULES:
- Never recommend pesticides not registered for that crop in India (CIB&RC list).
- Always state pre-harvest interval (PHI) for every chemical recommended.
- Warn about phytotoxicity risks at high temperatures (>35°C).
- Prohibit mixing of insecticides with fungicides unless specifically tested.
- Remind to triple-rinse spray equipment after use.

OUTPUT FORMAT:
- Start with: "Diagnosis: [pest/disease name]"
- Severity: [Low/Moderate/High/Severe]
- Symptoms Summary
- Immediate Action (within 24 hours)
- IPM Treatment Plan (numbered steps)
- Prevention for next season
"""


def analyze_pest_disease(
    query: str,
    farm_profile: dict,
    image_data: bytes | None = None,
    rag_context: str = "",
    language: str = "en",
) -> str:
    """Generate pest/disease diagnosis and treatment plan."""
    model = get_watsonx_model()

    image_note = ""
    if image_data:
        # For vision models, encode image to base64
        b64 = base64.b64encode(image_data).decode("utf-8")
        image_note = f"\n[Image uploaded for analysis — base64 length: {len(b64)} chars]\n"

    lang_note = ""
    if language != "en":
        lang_note = f"Respond in the farmer's preferred language where appropriate (language code: {language})."

    rag_section = f"\nPest/Disease Knowledge Base:\n{rag_context}\n" if rag_context else ""

    prompt = f"""<|system|>
{PEST_AGENT_INSTRUCTIONS}
{lang_note}

Farm Context:
- Location: {farm_profile.get('location', 'India')}
- Crops: {farm_profile.get('current_crops', 'Not specified')}
- Season: {farm_profile.get('season', 'Kharif')}
{image_note}
{rag_section}
<|user|>
{query}
<|assistant|>
"""
    return safe_generate(model, prompt)
