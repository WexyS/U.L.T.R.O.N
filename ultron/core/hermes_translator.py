"""Hermes schema translator."""
from __future__ import annotations
import asyncio, inspect, json
from ultron.core.hermes_tool import HermesTool

class SchemaTranslator:
    @staticmethod
    def translate_tooldef(td: dict) -> HermesTool:
        p = td.get("parameters", {})
        return HermesTool(name=td["name"], description=td.get("description",""), parameters=p, handler=td.get("handler"), is_async=td.get("is_async",False), category=td.get("category","general"), returns_direct=td.get("returns_direct",False), is_termination_fn=td.get("is_termination_fn",False))

    @staticmethod
    def translate_function_to_schema(fn) -> HermesTool:
        sig = inspect.signature(fn)
        doc = inspect.getdoc(fn) or ""
        pd2 = {}
        ia = False
        for ln in doc.split("\n"):
            ln = ln.strip()
            if ln.startswith(("Args:", "Parameters:")): ia = True; continue
            if ia and ln.startswith("Returns:"): ia = False
            if ia and ":" in ln:
                n, d = ln.split(":", 1); pd2[n.strip()] = d.strip()
        props, req = {}, []
        for nm, par in sig.parameters.items():
            if nm == "self": continue
            tm = {str:"string", int:"integer", float:"number", bool:"boolean", list:"array", dict:"object"}
            pt = tm.get(par.annotation, "string") if par.annotation != inspect.Parameter.empty else "string"
            pr = {"type": pt}
            if nm in pd2: pr["description"] = pd2[nm]
            if par.default == inspect.Parameter.empty: req.append(nm)
            else: pr["default"] = par.default
            props[nm] = pr
        return HermesTool(name=fn.__name__, description=doc.split("\n")[0] if doc else f"Execute {fn.__name__}", parameters={"type":"object","properties":props,"required":req}, handler=fn, is_async=asyncio.iscoroutinefunction(fn))
