"""
System-level diagnostics — currently just AI provider health.

Added because a misconfigured or expired GROQ_API_KEY / GEMINI_API_KEY
previously failed SILENTLY: every /*/briefing and /*/investigate endpoint
would just fall back to MockProvider with a small note buried at the end
of a 200-word summary, which is easy to miss and looks identical to a
genuinely broken feature. This endpoint makes an actual (cheap, one-line)
real API call right now and reports plainly whether it worked, so
"is my key actually working" has a direct answer instead of one you have
to infer from reading investigation text carefully.
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/ai-status")
def ai_status():
    """
    Actually calls the configured AI provider (not just checks that a key
    is present) and reports success/failure plainly, including the raw
    error message on failure — e.g. a decommissioned model name, an
    invalid key, or a network/firewall block will each show a distinct,
    diagnosable error here instead of a generic mock fallback.
    """
    configured = settings.AI_PROVIDER

    if configured not in ("groq", "gemini"):
        return {
            "configured_provider": configured,
            "status": "mock_by_design",
            "detail": "AI_PROVIDER is set to 'mock' (or unset) in backend/.env — "
                      "this is expected behavior, not an error. Set AI_PROVIDER=groq "
                      "or AI_PROVIDER=gemini plus the matching API key to use a real LLM.",
        }

    key_env_var = "GROQ_API_KEY" if configured == "groq" else "GEMINI_API_KEY"
    import os
    if not os.getenv(key_env_var):
        return {
            "configured_provider": configured,
            "status": "missing_key",
            "detail": f"AI_PROVIDER={configured} but {key_env_var} is empty/unset in backend/.env. "
                      "Every request is silently using MockProvider as a result.",
        }

    try:
        if configured == "groq":
            from app.services.ai_providers.groq_provider import GroqProvider, MODEL_FALLBACK_CHAIN
            provider = GroqProvider()
        else:
            from app.services.ai_providers.gemini_provider import GeminiProvider, MODEL_FALLBACK_CHAIN
            provider = GeminiProvider()

        text = provider.generate(
            "Reply with exactly one short sentence confirming you received this message.",
            "Health check ping — confirm you're receiving this.",
        )
        return {
            "configured_provider": configured,
            "status": "ok",
            "model_used": provider.model,
            "sample_response": text,
            "detail": f"Real API call to {configured} succeeded using model '{provider.model}'.",
        }
    except Exception as e:
        return {
            "configured_provider": configured,
            "status": "call_failed",
            "models_tried": MODEL_FALLBACK_CHAIN,
            "error": str(e),
            "detail": (
                f"AI_PROVIDER={configured} and {key_env_var} is set, but the real API call failed "
                f"(see 'error' above) — every /*/briefing and /*/investigate request is silently "
                "falling back to MockProvider as a result. Common causes: invalid/expired API key, "
                "no remaining free-tier quota, a decommissioned model name (check the provider's "
                "model-deprecations page), or this server's network blocking outbound HTTPS to the "
                "provider's API host."
            ),
        }
