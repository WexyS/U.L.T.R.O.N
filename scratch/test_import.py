import sys
import os
sys.path.append(os.getcwd())

try:
    from ultron.v2.core.security import SecurityManager
    print("SUCCESS: SecurityManager imported.")
    sm = SecurityManager()
    print(f"SUCCESS: SecurityManager instance created. Roots: {sm.allowed_roots}")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
