import tkinter as tk
from tkinter import font
import sys

def create_indicator():
    root = tk.Tk()
    root.title("Ultron Vision Active")
    
    # Hide window decorations
    root.overrideredirect(True)
    
    # Always on top
    root.attributes("-topmost", True)
    
    # Transparent background (on Windows)
    try:
        root.attributes("-transparentcolor", "white")
        bg_color = "white"
    except:
        bg_color = "#1a1a1a" # Fallback dark
        
    root.configure(bg=bg_color)

    # Label with eye emoji
    eye_font = font.Font(size=24)
    label = tk.Label(root, text="👁️", font=eye_font, fg="#00f2ff", bg=bg_color)
    label.pack()

    # Position in bottom-right
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    width = 40
    height = 40
    
    # 10px padding from edges
    x = screen_width - width - 20
    y = screen_height - height - 50 # Slightly higher to avoid taskbar overlap
    
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Close on click (emergency)
    root.bind("<Button-1>", lambda e: sys.exit())

    root.mainloop()

if __name__ == "__main__":
    create_indicator()
