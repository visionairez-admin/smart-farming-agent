"""
Base Agent - Shared IBM watsonx.ai client and utilities for all agents.
"""
import os
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams


# Valid IBM Cloud watsonx.ai regional URLs
VALID_WATSONX_URLS = {
    "us-south": "https://us-south.ml.cloud.ibm.com",
    "eu-de":    "https://eu-de.ml.cloud.ibm.com",
    "eu-gb":    "https://eu-gb.ml.cloud.ibm.com",
    "jp-tok":   "https://jp-tok.ml.cloud.ibm.com",
    "au-syd":   "https://au-syd.ml.cloud.ibm.com",
}


def get_watsonx_model(model_id: str = "ibm/granite-3-3-8b-instruct") -> ModelInference:
    """Initialise and return a watsonx ModelInference object."""
    api_key = os.getenv("IBM_API_KEY", "").strip()
    project_id = os.getenv("IBM_PROJECT_ID", "").strip()
    url = os.getenv("IBM_WATSONX_URL", "https://au-syd.ml.cloud.ibm.com").strip()

    if not api_key:
        raise ValueError("IBM_API_KEY is not set in your .env file.")
    if not project_id:
        raise ValueError("IBM_PROJECT_ID is not set in your .env file.")

    # Ensure URL is a known IBM Cloud SaaS endpoint
    if not any(url.startswith(v) for v in VALID_WATSONX_URLS.values()):
        raise ValueError(
            f"IBM_WATSONX_URL '{url}' does not look like a valid IBM Cloud watsonx.ai URL. "
            f"Valid options: {list(VALID_WATSONX_URLS.values())}"
        )

    credentials = Credentials(url=url, api_key=api_key)

    parameters = {
        GenParams.DECODING_METHOD: "greedy",
        GenParams.MAX_NEW_TOKENS: 1024,
        GenParams.MIN_NEW_TOKENS: 1,
        GenParams.TEMPERATURE: 0.7,
        GenParams.TOP_P: 0.9,
        GenParams.REPETITION_PENALTY: 1.1,
    }

    model = ModelInference(
        model_id=model_id,
        params=parameters,
        credentials=credentials,
        project_id=project_id,
    )
    return model


def test_connection() -> dict:
    """
    Attempt a minimal live call to watsonx.ai.
    Returns {"ok": True/False, "project_id": ..., "error": ...}
    """
    try:
        model = get_watsonx_model()
        result = model.generate_text(prompt="Hi")
        return {
            "ok": True,
            "project_id": os.getenv("IBM_PROJECT_ID", "").strip(),
            "model": "ibm/granite-3-3-8b-instruct",
            "sample_response": str(result)[:80],
        }
    except Exception as exc:
        raw = str(exc)
        # Friendly diagnosis
        if "not_found" in raw or "missing" in raw or "404" in raw:
            hint = (
                "Project ID not found. Go to dataplatform.cloud.ibm.com/wx "
                "→ your project → Manage → General → copy the Project ID."
            )
        elif "401" in raw or "403" in raw or "Unauthorized" in raw:
            hint = (
                "API Key rejected. Regenerate it at "
                "cloud.ibm.com → Manage → Access (IAM) → API Keys."
            )
        elif "Cannot set Project" in raw:
            hint = "Project ID is wrong or belongs to a different IBM Cloud account/region."
        else:
            hint = raw
        return {
            "ok": False,
            "project_id": os.getenv("IBM_PROJECT_ID", "").strip(),
            "error": hint,
            "raw_error": raw,
        }


def safe_generate(model: ModelInference, prompt: str) -> str:
    """Call model.generate_text and extract the result safely."""
    try:
        response = model.generate_text(prompt=prompt)
        if isinstance(response, str):
            return response.strip()
        if isinstance(response, dict):
            results = response.get("results", [])
            if results:
                return results[0].get("generated_text", "").strip()
        return str(response).strip()
    except Exception as exc:  # pylint: disable=broad-except
        return f"[Model error: {exc}]"
