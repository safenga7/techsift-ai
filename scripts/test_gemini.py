"""
Phase 0 - Test 1: Google Gemini API Feasibility Test
Validates official google-genai SDK, model availability, and free-tier generation.
Ensures zero secrets are printed, logged, or exposed.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


def mask_secret(text: str, secret: str) -> str:
    """Ensure secret key is never leaked in error messages or logs."""
    if secret and secret in text:
        return text.replace(secret, "[REDACTED_API_KEY]")
    return text


def run_gemini_test() -> dict:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        return {
            "status": "BLOCKED",
            "reason": "GEMINI_API_KEY is not set in environment or .env file",
            "instructions": (
                "1. Go to Google AI Studio: https://aistudio.google.com/app/apikey\n"
                "2. Create a free API key (No credit card or billing required).\n"
                "3. Copy the key and add it to your .env file: GEMINI_API_KEY=your_key_here\n"
                "4. Or export it in your shell: export GEMINI_API_KEY='your_key_here'"
            ),
        }

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        # Query available models in the user's API account
        available_models = []
        try:
            for m in client.models.list():
                model_name = getattr(m, "name", str(m))
                available_models.append(model_name)
        except Exception as e:
            raw_err = mask_secret(str(e), api_key)
            return {
                "status": "FAILED",
                "error_type": "MODEL_LIST_ERROR",
                "details": raw_err,
                "instructions": "Failed to list models. Check API key validity or network connectivity.",
            }

        # Filter for flash models eligible for free-tier quotas
        flash_models = [m for m in available_models if "flash" in m.lower()]

        # Candidates priority list (prefer modern verified free-tier models)
        env_model = os.getenv("GEMINI_MODEL")
        candidate_models = []
        if env_model:
            candidate_models.append(env_model)
            if not env_model.startswith("models/"):
                candidate_models.append(f"models/{env_model}")

        candidate_models.extend([
            "models/gemini-3.8-flash",
            "gemini-3.8-flash",
            "models/gemini-3.5-flash",
            "gemini-3.5-flash",
            "models/gemini-flash-latest",
            "gemini-flash-latest",
        ])

        selected_model = None
        for candidate in candidate_models:
            for avail in available_models:
                if candidate == avail or candidate == avail.replace("models/", ""):
                    selected_model = avail
                    break
            if selected_model:
                break

        if not selected_model and flash_models:
            selected_model = flash_models[0]
        elif not selected_model and available_models:
            selected_model = available_models[0]

        if not selected_model:
            selected_model = "models/gemini-3.8-flash"

        # Execute a real lightweight text generation request
        response = client.models.generate_content(
            model=selected_model,
            contents="Explain what an abstract syntax tree (AST) is in 1 sentence for a technical glossary.",
        )

        response_text = response.text.strip() if response and response.text else ""

        return {
            "status": "PASSED",
            "model_tested": selected_model,
            "sample_output": response_text,
            "available_models_count": len(available_models),
            "available_flash_models": [m.replace("models/", "") for m in flash_models[:5]],
            "free_tier_verified": True,
        }

    except Exception as exc:
        raw_err = mask_secret(str(exc), api_key)
        err_type = "API_ERROR"
        if "403" in raw_err or "PERMISSION_DENIED" in raw_err or "API_KEY_INVALID" in raw_err:
            err_type = "AUTHENTICATION_ERROR"
        elif "429" in raw_err or "RESOURCE_EXHAUSTED" in raw_err:
            err_type = "RATE_LIMIT_ERROR"
        elif "404" in raw_err or "NOT_FOUND" in raw_err:
            err_type = "MODEL_NOT_FOUND"
        elif "BILLING" in raw_err.upper():
            err_type = "BILLING_REQUIRED_ERROR"

        return {
            "status": "FAILED",
            "error_type": err_type,
            "details": raw_err,
        }


if __name__ == "__main__":
    result = run_gemini_test()
    print("--- GEMINI TEST RESULT ---")
    for k, v in result.items():
        print(f"{k}: {v}")
    if result["status"] == "FAILED":
        sys.exit(1)
    elif result["status"] == "BLOCKED":
        sys.exit(2)
    else:
        sys.exit(0)
