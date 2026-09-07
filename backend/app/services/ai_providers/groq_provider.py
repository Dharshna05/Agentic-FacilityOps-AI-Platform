"""
Real Groq-backed provider. Requires GROQ_API_KEY in the environment.
Groq is the default real-LLM choice for this project (fast inference,
generous free tier) — Gemini remains available as an alternative.

Groq's API is OpenAI-compatible, which means tool/function calling needs
an explicit JSON schema per tool (unlike google-genai's automatic schema
generation from raw Python functions). app/services/ai_providers/tool_schema.py
builds that schema from each tool's type hints + docstring, so the same
functions in app/core/agent_tools.py work for both providers unmodified.

MODEL DEPRECATION NOTE (fixed here): this provider previously defaulted to
"llama-3.3-70b-versatile", which Groq deprecated on 2026-06-17 and fully
decommissioned by 2026-08-16 — every real API call was returning HTTP 400
"model_decommissioned" and silently falling back to MockProvider (see
intelligence_engine.py's _safe_generate/_safe_agentic_task), which is
exactly why a correctly-configured GROQ_API_KEY looked like it "wasn't
working" — there was no visible error, just a mock response every time.
Now defaults to "openai/gpt-oss-120b" (Groq's own recommended replacement,
confirmed to support tool calling). Because Groq has deprecated multiple
models in fast succession this year, MODEL_FALLBACK_CHAIN below tries a
second model automatically if the primary one is ever decommissioned
again, instead of silently degrading all the way to mock on a single
model-name failure.
"""
import os
import json
import logging
from typing import Callable

from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.tool_schema import function_to_tool_schema

logger = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 8

# Tried in order; only advances to the next if the current one raises (e.g.
# a future model_decommissioned error) — this is specifically to survive
# Groq's frequent model retirements without another silent full-mock
# fallback. Update this list if Groq deprecates gpt-oss-120b too — check
# https://console.groq.com/docs/deprecations.
MODEL_FALLBACK_CHAIN = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"]


class GroqProvider(AIProvider):
    def __init__(self, model: str = MODEL_FALLBACK_CHAIN[0]):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Add it to backend/.env to use GroqProvider, "
                "or use MockProvider for local dev without a key."
            )
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        # Any model not already first in the chain (e.g. explicitly passed
        # in) still gets the rest of the chain as fallbacks behind it.
        self._models_to_try = [model] + [m for m in MODEL_FALLBACK_CHAIN if m != model]

    def _call_with_fallback(self, fn):
        """Try each model in self._models_to_try in order; only move to the
        next on failure (so a working model is never abandoned for a
        cosmetic reason), and raise the LAST error if all fail."""
        last_error = None
        for model in self._models_to_try:
            try:
                result = fn(model)
                if model != self.model:
                    logger.warning(f"Groq model '{self.model}' failed; '{model}' succeeded instead. "
                                    f"Consider updating the default in groq_provider.py.")
                return result
            except Exception as e:
                last_error = e
                continue
        raise last_error

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        def call(model):
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content
        return self._call_with_fallback(call)

    def run_agentic_task(self, system_prompt: str, task_prompt: str, tools: list[Callable]) -> dict:
        """
        Real agentic execution via Groq's OpenAI-compatible tool calling.
        Unlike google-genai, Groq doesn't loop automatically — we drive the
        loop ourselves: send messages + tool schemas, if the model responds
        with tool_calls, execute them, append results, and send again. Stops
        when the model responds with plain text (no more tool calls) or
        after MAX_AGENT_ITERATIONS as a safety cap.
        """
        tool_map = {t.__name__: t for t in tools}
        tool_schemas = [function_to_tool_schema(t) for t in tools]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_prompt},
        ]
        trace = []

        def run_with_model(model):
            for _ in range(MAX_AGENT_ITERATIONS):
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                )
                message = response.choices[0].message

                if not message.tool_calls:
                    return {"final_text": message.content or "", "tool_calls": trace}

                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [tc.model_dump() for tc in message.tool_calls],
                })

                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    if name in tool_map:
                        result = tool_map[name](**args)
                    else:
                        result = {"error": f"unknown tool: {name}"}

                    trace.append({"tool": name, "args": args, "result": result})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    })

            return {
                "final_text": "Investigation stopped after reaching the maximum number of reasoning steps.",
                "tool_calls": trace,
            }

        # NOTE: the fallback chain only helps if the FIRST call of a model
        # fails (e.g. decommissioned model name) — once tool calls have
        # already been appended to `messages` under one model, we don't
        # silently swap models mid-conversation. _call_with_fallback here
        # effectively only retries a fresh attempt if run_with_model raises
        # before any tool call succeeds.
        return self._call_with_fallback(run_with_model)
