"""
Real Gemini-backed provider. Requires GEMINI_API_KEY in the environment.
Uses the google-genai SDK — same choice as AG-ASE-2026 for consistency.

MODEL DEPRECATION NOTE (fixed here): this provider previously defaulted to
"gemini-2.0-flash", which Google shut down on 2026-06-01 — every real API
call was returning a 404 "no longer available" and silently falling back
to MockProvider (see intelligence_engine.py's _safe_generate/
_safe_agentic_task), which is exactly why a correctly-configured
GEMINI_API_KEY looked like it "wasn't working" — no visible error, just a
mock response every time. Now defaults to "gemini-2.5-flash" (Google's
recommended replacement). NOTE FOR FUTURE-YOU: gemini-2.5-flash itself has
a "no earlier than October 16, 2026" scheduled shutdown per
https://ai.google.dev/gemini-api/docs/deprecations — if real Gemini calls
start silently falling back to mock again after that date, this is almost
certainly why; check that page and update MODEL_FALLBACK_CHAIN below
before assuming a code bug.
"""
import os
import logging
from typing import Callable
from app.services.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)

# Tried in order; only advances to the next if the current one raises —
# survives a model being retired without falling all the way back to mock.
MODEL_FALLBACK_CHAIN = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]


class GeminiProvider(AIProvider):
    def __init__(self, model: str = MODEL_FALLBACK_CHAIN[0]):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Add it to backend/.env to use GeminiProvider, "
                "or use MockProvider for local dev without a key."
            )
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self._models_to_try = [model] + [m for m in MODEL_FALLBACK_CHAIN if m != model]

    def _call_with_fallback(self, fn):
        last_error = None
        for model in self._models_to_try:
            try:
                result = fn(model)
                if model != self.model:
                    logger.warning(f"Gemini model '{self.model}' failed; '{model}' succeeded instead. "
                                    f"Consider updating the default in gemini_provider.py.")
                return result
            except Exception as e:
                last_error = e
                continue
        raise last_error

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        def call(model):
            response = self.client.models.generate_content(
                model=model,
                contents=user_prompt,
                config={"system_instruction": system_prompt},
            )
            return response.text
        return self._call_with_fallback(call)

    def run_agentic_task(self, system_prompt: str, task_prompt: str, tools: list[Callable]) -> dict:
        """
        Real agentic execution: passes the tool functions directly to
        Gemini. The SDK's Automatic Function Calling (AFC) lets the model
        decide which tools to call and in what order — it calls them,
        feeds results back to the model, and loops until the model returns
        a final answer (default cap: 10 remote calls).
        """
        from google.genai import types

        def call(model):
            response = self.client.models.generate_content(
                model=model,
                contents=task_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=tools,
                ),
            )

            trace = []
            history = getattr(response, "automatic_function_calling_history", None) or []
            for content in history:
                for part in getattr(content, "parts", []) or []:
                    fc = getattr(part, "function_call", None)
                    fr = getattr(part, "function_response", None)
                    if fc:
                        trace.append({"tool": fc.name, "args": dict(fc.args or {}), "result": None})
                    elif fr and trace:
                        trace[-1]["result"] = fr.response

            return {"final_text": response.text, "tool_calls": trace}

        return self._call_with_fallback(call)
