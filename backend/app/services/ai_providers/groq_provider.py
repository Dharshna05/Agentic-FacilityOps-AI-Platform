"""
Real Groq-backed provider. Requires GROQ_API_KEY in the environment.
Groq is the default real-LLM choice for this project (fast inference,
generous free tier) — Gemini remains available as an alternative.

Groq's API is OpenAI-compatible, which means tool/function calling needs
an explicit JSON schema per tool (unlike google-genai's automatic schema
generation from raw Python functions). app/services/ai_providers/tool_schema.py
builds that schema from each tool's type hints + docstring, so the same
functions in app/core/agent_tools.py work for both providers unmodified.
"""
import os
import json
from typing import Callable

from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.tool_schema import function_to_tool_schema

MAX_AGENT_ITERATIONS = 8


class GroqProvider(AIProvider):
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Add it to backend/.env to use GroqProvider, "
                "or use MockProvider for local dev without a key."
            )
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

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

        for _ in range(MAX_AGENT_ITERATIONS):
            response = self.client.chat.completions.create(
                model=self.model,
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
