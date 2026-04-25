import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from ultron.v2.core.reasoning_engine import ReasoningEngine
    print(f"ReasoningEngine class: {ReasoningEngine}")
    print(f"ReasoningEngine file: {ReasoningEngine.__module__}")
    
    import ultron.v2.core.reasoning_engine as re_mod
    print(f"Module file: {re_mod.__file__}")
    
    engine = ReasoningEngine()
    print(f"Instance created: {engine}")
    
    if hasattr(engine, 'reason'):
        print("Attribute 'reason' FOUND")
    else:
        print("Attribute 'reason' NOT FOUND")
        
    if hasattr(engine, 'think_and_answer'):
        print("Attribute 'think_and_answer' FOUND")
    else:
        print("Attribute 'think_and_answer' NOT FOUND")

except Exception as e:
    print(f"Error: {e}")
