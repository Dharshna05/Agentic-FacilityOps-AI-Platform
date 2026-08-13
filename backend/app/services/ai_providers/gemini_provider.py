"""
Real Gemini-backed provider. Requires GEMINI_API_KEY in the environment.
Uses the google-genai SDK — same choice as AG-ASE-2026 for consistency.
"""
import os
from typing import Callable
from app.services.ai_providers.base import AIProvider


class GeminiProvider(AIProvider):
    def __init__(self, model: str = "gemini-2.0-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Add it to backend/.env to use GeminiProvider, "
                "or use MockProvider for local dev without a key."
            )
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config={"system_instruction": system_prompt},
        )
        return response.text

    def run_agentic_task(self, system_prompt: str, task_prompt: str, tools: list[Callable]) -> dict:
        """
        Real agentic execution: passes the tool functions directly to
        Gemini. The SDK's Automatic Function Calling (AFC) lets the model
        decide which tools to call and in what order — it calls them,
        feeds results back to the model, and loops until the model returns
        a final answer (default cap: 10 remote calls).
        """
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
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
