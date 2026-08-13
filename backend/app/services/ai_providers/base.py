"""
AI provider abstraction — same pattern as AG-ASE-2026's AIProvider interface.
Lets the Intelligence Engine swap between real LLM providers (Gemini, Groq,
OpenAI) and a MockProvider for tests/dev without an API key, without
touching any calling code.
"""
from abc import ABC, abstractmethod
from typing import Callable


class AIProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's text response for a single-turn prompt
        (no tool use). Used for straightforward summarization tasks."""
        raise NotImplementedError

    @abstractmethod
    def run_agentic_task(self, system_prompt: str, task_prompt: str, tools: list[Callable]) -> dict:
        """
        Run a genuinely agentic task: the model is given a goal and a set
        of callable tools, and DECIDES for itself which tools to call, in
        what order, and when it has enough information to stop — as
        opposed to us hardcoding a fixed pipeline of calls.

        Returns:
            {
                "final_text": str,              # the model's final synthesis
                "tool_calls": [                  # trace of what the model decided to do
                    {"tool": str, "args": dict, "result": Any}, ...
                ],
            }
        """
        raise NotImplementedError
