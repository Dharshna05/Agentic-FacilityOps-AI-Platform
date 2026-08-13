"""
Groq (and OpenAI-compatible APIs generally) expect tools as explicit JSON
Schema, unlike google-genai which can auto-generate schemas from raw Python
functions. This module introspects a Python function's type hints and
Google-style docstring ("Args:" section) to build that schema automatically,
so app/core/agent_tools.py doesn't need to be duplicated or hand-written
twice for two different providers.
"""
import inspect
import re
from typing import Callable

_TYPE_MAP = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _parse_arg_descriptions(docstring: str) -> dict:
    """Extract {param_name: description} from a Google-style 'Args:' block."""
    if not docstring:
        return {}
    descriptions = {}
    in_args = False
    current_name = None
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.startswith("Args:"):
            in_args = True
            continue
        if not in_args:
            continue
        match = re.match(r"(\w+):\s*(.*)", stripped)
        if match:
            current_name = match.group(1)
            descriptions[current_name] = match.group(2)
        elif current_name and stripped:
            descriptions[current_name] += " " + stripped
    return descriptions


def function_to_tool_schema(func: Callable) -> dict:
    """Build an OpenAI/Groq-style tool schema dict from a Python function."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    summary = doc.split("\n\n")[0].replace("\n", " ").strip()
    arg_descriptions = _parse_arg_descriptions(doc)

    properties, required = {}, []
    for name, param in sig.parameters.items():
        json_type = _TYPE_MAP.get(param.annotation, "string")
        properties[name] = {"type": json_type, "description": arg_descriptions.get(name, "")}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": summary,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }
