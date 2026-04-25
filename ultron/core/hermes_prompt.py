"""Hermes system prompt builder."""
from __future__ import annotations
import json
from ultron.core.hermes_tool import HermesTool

_LT = chr(60)  # <
_GT = chr(62)  # >

def to_hermes_system_prompt(tools: list[HermesTool]) -> str:
    base = ("You are a function calling AI model. You are provided with function "
            "signatures within tools tags. You may call one or more functions to "
            "assist with the user query. Don't make assumptions about what values "
            "to plug into functions. Here are the available tools:\n")
    tx = f"{_LT}tools{_GT}\n"
    for t in tools:
        sj = json.dumps(t.to_pydantic_schema(), indent=2)
        tx += f"{_LT}function{_GT}\n{_LT}name{_GT}{t.name}{_LT}/name{_GT}\n{_LT}description{_GT}{t.description}{_LT}/description{_GT}\n{_LT}parameters{_GT}\n{sj}\n{_LT}/parameters{_GT}\n{_LT}/function{_GT}\n"
    tx += f"{_LT}/tools{_GT}\n"
    fcall = json.dumps({"title":"FunctionCall","type":"object","properties":{"name":{"title":"Name","type":"string"},"arguments":{"title":"Arguments","type":"object"}},"required":["name","arguments"]}, indent=2)
    instr = (f"\nCall functions using this JSON schema inside tool_call tags:\n{fcall}\n\n"
             f"Rules:\n1. Think before calling: explain reasoning in thought tags\n"
             f"2. Output ONLY one function call per response inside tool_call tags\n"
             f"3. If no tool needed, respond normally\n"
             f"4. On errors, analyze the error and try a different approach\n")
    return base + tx + instr
