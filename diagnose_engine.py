
import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from ultron.v2.core.reasoning_engine import ReasoningEngine

engine = ReasoningEngine()
print(f"Engine class: {engine.__class__}")
print(f"Has 'reason' attribute: {hasattr(engine, 'reason')}")
print(f"Has 'think_and_answer' attribute: {hasattr(engine, 'think_and_answer')}")
print(f"Dir: {dir(engine)}")
