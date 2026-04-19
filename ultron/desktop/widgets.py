import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen

class AnimatedOrb(QWidget):
    """Futuristic 3D Glowing Core ORB that breathes and changes color based on state."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 250)
        
        # State: idle, listening, processing
        self.state = 'idle'
        
        self.time_cycle = 0.0
        self.breathe_speed = 0.1
        
        # Colors per state (Core Color, Glow Color)
        self.theme_colors = {
            'idle': (QColor(255, 30, 30, 255), QColor(255, 0, 0, 100)),        # Red menacing
            'listening': (QColor(0, 255, 255, 255), QColor(0, 150, 255, 120)),   # Cyan / Blue
            'processing': (QColor(255, 200, 0, 255), QColor(255, 100, 0, 120))   # Yellow / Orange
        }
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)  # ~33fps

    def set_state(self, state: str):
        if state in self.theme_colors:
            self.state = state
            if state == 'idle':
                self.breathe_speed = 0.05
            elif state == 'listening':
                self.breathe_speed = 0.15
            elif state == 'processing':
                self.breathe_speed = 0.3
                
    def animate(self):
        self.time_cycle += self.breathe_speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_f = self.rect().center().toPointF()
        cx = center_f.x()
        cy = center_f.y()
        w = self.width()
        h = self.height()
        radius = min(w, h) / 2.0 - 20.0
        
        core_color, glow_color = self.theme_colors[self.state]
        
        # Calculate dynamic radius based on breathing sine wave
        breathe_factor = (math.sin(self.time_cycle) + 1) / 2  # 0.0 to 1.0
        dynamic_radius = radius * 0.8 + (radius * 0.2 * breathe_factor)
        
        # Outer Tech Rings
        painter.setPen(QPen(glow_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_f, radius + 5.0, radius + 5.0)
        
        # Second dashed ring spinning
        painter.save()
        painter.translate(center_f)
        painter.rotate(math.degrees(self.time_cycle * 0.5))
        pen = QPen(core_color, 3)
        pen.setDashPattern([5, 10, 15, 10])
        painter.setPen(pen)
        painter.drawEllipse(int(-radius), int(-radius), int(radius * 2), int(radius * 2))
        painter.restore()
        
        # Inner Glowing Orb
        grad = QRadialGradient(cx, cy, dynamic_radius)
        
        # Core intense color
        c1 = QColor(core_color)
        c1.setAlphaF(min(1.0, 0.6 + breathe_factor * 0.4))
        
        # Outer fade
        c2 = QColor(glow_color)
        c2.setAlphaF(min(0.8, 0.3 + breathe_factor * 0.5))
        
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.6, c2)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(center_f, dynamic_radius, dynamic_radius)
