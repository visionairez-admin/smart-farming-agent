"""
RAG (Retrieval-Augmented Generation) Module
Retrieves relevant agricultural knowledge from the local knowledge base
to augment LLM responses with accurate, domain-specific context.
"""
import json
import os
import re
from pathlib import Path
from typing import List, Tuple


# ============================================================
#  Knowledge Base Loader
# ============================================================
_KB_CACHE: dict = {}


def load_knowledge_base(kb_path: str = None) -> dict:
    """Load and cache the agricultural knowledge base from JSON."""
    global _KB_CACHE
    if _KB_CACHE:
        return _KB_CACHE

    if kb_path is None:
        kb_path = os.getenv(
            "KNOWLEDGE_BASE_PATH",
            str(Path(__file__).parent / "knowledge_base"),
        )

    kb_file = Path(kb_path) / "agricultural_knowledge.json"
    try:
        with open(kb_file, "r", encoding="utf-8") as f:
            _KB_CACHE = json.load(f)
    except FileNotFoundError:
        _KB_CACHE = {}

    return _KB_CACHE


# ============================================================
#  Text Chunker — splits KB into searchable passages
# ============================================================
def _build_passages(kb: dict) -> List[Tuple[str, str]]:
    """
    Returns list of (passage_text, category) tuples from the knowledge base.
    This flat list is searched via keyword scoring (no vector DB required at runtime).
    """
    passages = []

    # Crops
    for crop in kb.get("crops", []):
        text = (
            f"Crop: {crop['name']} | Season: {crop.get('season')} | "
            f"Soil: {', '.join(crop.get('soil_type', []))} | "
            f"Temperature: {crop.get('temperature_range')} | "
            f"Varieties: {', '.join(crop.get('varieties', []))} | "
            f"Fertilizer: basal={crop.get('fertilizer_schedule', {}).get('basal', 'N/A')} | "
            f"Irrigation: {crop.get('irrigation', 'N/A')} | "
            f"Pests: {', '.join(crop.get('pests', []))} | "
            f"Diseases: {', '.join(crop.get('diseases', []))} | "
            f"MSP 2024: ₹{crop.get('msp_2024', 'N/A')}/quintal | "
            f"Market Price: {crop.get('market_price_range', 'N/A')} | "
            f"Yield: {crop.get('yield_qtl_ha')} qtl/ha | "
            f"Harvesting: {crop.get('harvesting_tips', 'N/A')} | "
            f"Storage: {crop.get('storage', 'N/A')}"
        )
        passages.append((text, "crop"))

    # Soil types
    for soil in kb.get("soil_types", []):
        text = (
            f"Soil Type: {soil['type']} | "
            f"States: {', '.join(soil.get('states', []))} | "
            f"pH Range: {soil.get('ph_range')} | "
            f"Characteristics: {soil.get('characteristics')} | "
            f"Suitable Crops: {', '.join(soil.get('suitable_crops', []))} | "
            f"Deficiencies: {', '.join(soil.get('deficiencies', []))} | "
            f"Improvement: {soil.get('improvement')}"
        )
        passages.append((text, "soil"))

    # Pests and diseases
    for pd in kb.get("pests_diseases", []):
        text = (
            f"{pd['type'].title()}: {pd['name']} | "
            f"Crops Affected: {', '.join(pd.get('crops_affected', []))} | "
            f"Symptoms: {pd.get('symptoms')} | "
            f"Severity: {pd.get('severity', 'N/A')} | "
            f"Organic Control: {', '.join(pd.get('organic_control', []))} | "
            f"Chemical Control: {', '.join(pd.get('chemical_control', []))} | "
            f"Prevention: {pd.get('prevention', pd.get('ipm_strategy', 'N/A'))}"
        )
        passages.append((text, "pest_disease"))

    # Government schemes
    for scheme in kb.get("government_schemes", []):
        text = (
            f"Scheme: {scheme['name']} | "
            f"Type: {scheme.get('type')} | "
            f"Benefit: {scheme.get('benefit')} | "
            f"Eligibility: {scheme.get('eligibility', 'N/A')} | "
            f"Documents: {', '.join(scheme.get('documents', []))} | "
            f"How to Apply: {scheme.get('how_to_apply', 'N/A')} | "
            f"Helpline: {scheme.get('helpline', 'N/A')} | "
            f"Website: {scheme.get('website', 'N/A')}"
        )
        passages.append((text, "scheme"))

    # Seasonal calendar
    cal = kb.get("seasonal_calendar", {})
    for season, info in cal.items():
        text = (
            f"Season: {season} | Sowing: {info.get('sowing')} | "
            f"Harvesting: {info.get('harvesting')} | "
            f"Crops: {', '.join(info.get('crops', []))}"
        )
        passages.append((text, "calendar"))

    # Irrigation methods
    for irr in kb.get("irrigation_methods", []):
        text = (
            f"Irrigation: {irr['method']} | "
            f"Water Saving: {irr.get('water_saving')} | "
            f"Suitable Crops: {', '.join(irr.get('suitable_crops', []))} | "
            f"Cost per Ha: {irr.get('cost_per_ha', 'N/A')} | "
            f"Subsidy: {irr.get('subsidy', 'N/A')} | "
            f"Advantages: {', '.join(irr.get('advantages', []))}"
        )
        passages.append((text, "irrigation"))

    return passages


def _score_passage(passage: str, query_tokens: List[str]) -> float:
    """Simple TF-like relevance score using keyword overlap."""
    passage_lower = passage.lower()
    score = 0.0
    for token in query_tokens:
        if len(token) < 3:
            continue
        count = passage_lower.count(token)
        if count > 0:
            score += 1.0 + 0.2 * (count - 1)
    return score


# ============================================================
#  Public API
# ============================================================
def retrieve_context(
    query: str,
    agent_type: str = "general",
    top_k: int = 5,
    kb_path: str = None,
) -> str:
    """
    Retrieve top-k relevant passages from the knowledge base.

    Parameters
    ----------
    query       : The farmer's question / agent prompt.
    agent_type  : One of 'crop', 'weather', 'pest_disease', 'market',
                  'scheme', 'general'. Used to filter passage categories.
    top_k       : Number of passages to return.
    kb_path     : Override knowledge base directory path.

    Returns
    -------
    A formatted string of relevant passages to inject into the prompt.
    """
    kb = load_knowledge_base(kb_path)
    if not kb:
        return ""

    all_passages = _build_passages(kb)

    # Category filter by agent type
    category_map = {
        "crop": ["crop", "soil", "calendar"],
        "weather": ["crop", "irrigation", "calendar"],
        "pest": ["pest_disease", "crop"],
        "pest_disease": ["pest_disease", "crop"],
        "market": ["crop", "scheme"],
        "scheme": ["scheme"],
        "general": None,  # no filter
    }
    allowed_cats = category_map.get(agent_type)
    if allowed_cats:
        passages = [p for p in all_passages if p[1] in allowed_cats]
    else:
        passages = all_passages

    # Tokenise query
    tokens = re.findall(r"[a-zA-Z\u0900-\u097F]{3,}", query.lower())

    # Score passages
    scored = [(p[0], _score_passage(p[0], tokens)) for p in passages]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Filter zero-score
    top_passages = [p[0] for p in scored[:top_k] if p[1] > 0]

    if not top_passages:
        # Fallback: return top_k by category relevance alone
        top_passages = [p[0] for p in passages[:top_k]]

    return "\n---\n".join(top_passages)


def get_all_crops(kb_path: str = None) -> List[dict]:
    """Return all crop records from the knowledge base."""
    kb = load_knowledge_base(kb_path)
    return kb.get("crops", [])


def get_all_schemes(kb_path: str = None) -> List[dict]:
    """Return all government scheme records."""
    kb = load_knowledge_base(kb_path)
    return kb.get("government_schemes", [])


def get_seasonal_calendar(kb_path: str = None) -> dict:
    """Return the seasonal planting calendar."""
    kb = load_knowledge_base(kb_path)
    return kb.get("seasonal_calendar", {})
