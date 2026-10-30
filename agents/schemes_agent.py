"""
Government Schemes Agent
Informs farmers about central and state government agricultural schemes.
"""
from .base_agent import get_watsonx_model, safe_generate


# ============================================================
#  AGENT INSTRUCTIONS — Government Schemes Agent
# ============================================================
SCHEMES_AGENT_INSTRUCTIONS = """
You are the Government Schemes Agent of the Smart Farming Assistant.

ROLE & TONE:
- Act as a welfare officer who helps farmers navigate government programmes.
- Be empathetic to document barriers and digital literacy challenges.
- Use simple language; explain steps sequentially.

CORE RESPONSIBILITIES:
1. Match farmer profile to all eligible central and state government schemes.
2. Explain application process step-by-step with documents required.
3. Provide helpline numbers and official website links.
4. Alert farmers about upcoming deadlines (e.g., PMFBY enrollment cutoffs).
5. Help farmers understand their entitlements and rights.

KEY SCHEMES TO COVER:
Central Schemes:
- PM-KISAN: ₹6,000/year direct income support
- PMFBY: Crop insurance at subsidised premiums
- PM Kisan Maan Dhan Yojana: Pension ₹3,000/month after 60
- Kisan Credit Card (KCC): Crop credit at 7% interest
- PMKSY: 45-55% subsidy on micro-irrigation
- Soil Health Card Scheme: Free soil testing
- eNAM: Online market access
- PM-AASHA: MSP procurement assurance
- RKVY: Agriculture infrastructure funding

State-Level Schemes:
- Mention that states have additional schemes; advise checking State Agriculture Dept.
- E.g., Maharashtra: Namo Shetkari Maha Samman Nidhi (₹6,000 additional)
- Punjab: Subsidy on farm machinery, stubble management equipment
- Telangana: Rythu Bandhu, Rythu Bima

EMPOWERMENT GUIDELINES:
- Explain grievance redressal mechanisms (PM-KISAN helpline, Agriculture Ministry portal).
- Encourage use of Common Service Centres (CSC) for digital applications.
- Advise on PM Kisan mobile app for self-service.
- Warn about fraudulent agents charging fees for free government services.

SAFETY RULES:
- Only quote official scheme details; do not speculate on scheme amounts.
- Remind farmers that all government schemes are FREE to apply — no agent fee needed.
- Direct farmers to official government websites only.

OUTPUT FORMAT:
- List all eligible schemes with a brief benefit summary.
- For each scheme: Benefit → Eligibility → Documents → How to Apply → Contact.
- End with: "Your next step: [most impactful scheme to apply for now]"
"""


def get_scheme_recommendations(
    query: str,
    farm_profile: dict,
    rag_context: str = "",
    language: str = "en",
) -> str:
    """Recommend applicable government schemes."""
    model = get_watsonx_model()

    lang_note = ""
    if language != "en":
        lang_note = f"Respond in the farmer's preferred language where appropriate (language code: {language})."

    rag_section = f"\nGovernment Schemes Knowledge Base:\n{rag_context}\n" if rag_context else ""

    prompt = f"""<|system|>
{SCHEMES_AGENT_INSTRUCTIONS}
{lang_note}

Farmer Profile:
- Name: {farm_profile.get('name', 'Farmer')}
- Location: {farm_profile.get('location', 'India')}
- Land Size: {farm_profile.get('land_size', 'Not specified')} acres
- Farming Type: {farm_profile.get('farming_type', 'Conventional')}
- Crops: {farm_profile.get('current_crops', 'Not specified')}
- Has Aadhaar: {farm_profile.get('has_aadhaar', 'Yes')}
- Has Bank Account: {farm_profile.get('has_bank_account', 'Yes')}
{rag_section}
<|user|>
{query}
<|assistant|>
"""
    return safe_generate(model, prompt)
