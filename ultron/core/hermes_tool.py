"""Hermes tool schema definition."""
from __future__ import annotations
import asyncio, inspect, json
from dataclasses import dataclass
from typing import Any, Callable, Optional

@dataclass
class HermesTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Optional[Callable] = None
    is_async: bool = False
    category: str = "general"
    returns_direct: bool = False
    is_termination_fn: bool = False

    def to_openai_schema(self) -> dict:
        return {"type":"function","function":{"name":self.name,"description":self.description,"parameters":{"type":"object","properties":self.parameters.get("properties",{}),"required":self.parameters.get("required",[])}}}

    def to_pydantic_schema(self) -> dict:
        props = self.parameters.get("properties", {})
        req = self.parameters.get("required", [])
        pp = {}
        for pn, pd in props.items():
            p = {"title": pn.replace("_", " ").title(), "type": pd.get("type", "string")}
            if "description" in pd: p["description"] = pd["description"]
            if pn not in req: p["default"] = pd.get("default", None)
            pp[pn] = p
        return {"title": f"{self.name.title().replace('_', '')}Arguments", "type": "object", "properties": pp, "required": req}
