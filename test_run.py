import traceback
try:
    from ultron.desktop.app import run_desktop
    run_desktop()
except Exception as e:
    print("FATAL ERROR:")
    traceback.print_exc()
