"""
Picks the AI provider based on AI_PROVIDER in .env. Falls back to
MockProvider gracefully (with a logged warning) if a real provider is
configured but its API key is missing/invalid, rather than crashing the
request — a misconfigured key shouldn't take the whole endpoint down.

get_ai_provider() returns (provider_instance, actual_provider_name) so
callers (routes) can report which provider genuinely ran, not just which
one was configured — these can differ on fallback.
"""
import logging
from app.core.config import settings
from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.mock_provider import MockProvider

logger = logging.getLogger(__name__)


def get_ai_provider() -> tuple[AIProvider, str]:
    configured = settings.AI_PROVIDER

    if configured == "groq":
        try:
            from app.services.ai_providers.groq_provider import GroqProvider
            return GroqProvider(), "groq"
        except Exception as e:
            logger.warning(f"GroqProvider unavailable ({e}); falling back to MockProvider.")
            return MockProvider(), "mock (groq unavailable)"

    if configured == "gemini":
        try:
            from app.services.ai_providers.gemini_provider import GeminiProvider
            return GeminiProvider(), "gemini"
        except Exception as e:
            logger.warning(f"GeminiProvider unavailable ({e}); falling back to MockProvider.")
            return MockProvider(), "mock (gemini unavailable)"

    return MockProvider(), "mock"
