
import sys
import os
sys.path.append(os.getcwd())

from ultron.core.reasoning_engine import ReasoningEngine
import inspect

print(f"File: {inspect.getfile(ReasoningEngine)}")
print(f"Attributes: {dir(ReasoningEngine)}")

engine = ReasoningEngine(router=None)
print(f"Has reason: {hasattr(engine, 'reason')}")
