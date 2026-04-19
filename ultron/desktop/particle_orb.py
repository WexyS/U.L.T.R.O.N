import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen

class FluidParticleOrb(QWidget):
    """
    Modern Silver/Metallic 3D Particle Orb.
    Generates points on a sphere, rotates them, applies a wave deformation,
    and projects them to the 2D surface.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        
        self.state = 'idle'  # idle, listening, processing
        self.time_cycle = 0.0
        
        # Performance: Pre-calculate the spherical coordinates (phi, theta)
        self.num_points = 500
        self.particles = []
        
        # Golden ratio spiral to evenly distribute points on a sphere
        golden_ratio = (1 + 5 ** 0.5) / 2
        for i in range(self.num_points):
            t = i / self.num_points
            phi = math.acos(1 - 2 * t)
            theta = 2 * math.pi * i / golden_ratio
            self.particles.append((phi, theta))
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)  # ~33fps
        
        # Silver colors
        self.idle_core = QColor(200, 200, 210, 255)
        self.idle_glow = QColor(150, 150, 160, 100)
        
        self.listen_core = QColor(255, 255, 255, 255)
        self.listen_glow = QColor(200, 200, 220, 150)
        
        self.process_core = QColor(230, 230, 240, 255)
        self.process_glow = QColor(180, 180, 200, 180)

    def set_state(self, state: str):
        self.state = state
        
    def animate(self):
        speed = 0.05
        if self.state == 'listening':
            speed = 0.15
        elif self.state == 'processing':
            speed = 0.3
            
        self.time_cycle += speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Siyah / Koyu transparan arka plan
        painter.fillRect(self.rect(), QColor(5, 5, 5, 0))
        
        center_f = self.rect().center().toPointF()
        cx = center_f.x()
        cy = center_f.y()
        w = self.width()
        h = self.height()
        base_radius = min(w, h) / 2.0 - 50.0  # leave room for wave
        
        # Set colors
        if self.state == 'idle':
            c_core, c_glow = self.idle_core, self.idle_glow
            wave_amp = 0.05
            rot_y_speed = 0.5
        elif self.state == 'listening':
            c_core, c_glow = self.listen_core, self.listen_glow
            wave_amp = 0.15
            rot_y_speed = 0.8
        else: # processing
            c_core, c_glow = self.process_core, self.process_glow
            wave_amp = 0.3
            rot_y_speed = 2.0
            
        breathe = (math.sin(self.time_cycle) + 1) / 2
        
        # Y axis rotation angle
        rot_y = self.time_cycle * rot_y_speed
        # X axis slight tilt
        rot_x = math.radians(20) 
        
        # Optional: Inner Glow
        grad = QRadialGradient(cx, cy, base_radius * 1.2)
        grad.setColorAt(0.0, QColor(c_core.red(), c_core.green(), c_core.blue(), 40))
        grad.setColorAt(0.5, QColor(c_glow.red(), c_glow.green(), c_glow.blue(), 20))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(center_f, base_radius * 1.2, base_radius * 1.2)
        
        painter.setBrush(QColor(c_core.red(), c_core.green(), c_core.blue(), 200))
        painter.setPen(Qt.PenStyle.NoPen)
        
        cos_rx = math.cos(rot_x)
        sin_rx = math.sin(rot_x)
        cos_ry = math.cos(rot_y)
        sin_ry = math.sin(rot_y)
        
        # Draw points
        for phi, theta in self.particles:
            # Add Perlin-like noise using multi-sine waves
            freq = 4.0
            noise = math.sin(phi * freq + self.time_cycle) * math.cos(theta * freq + self.time_cycle)
            r = base_radius * (1.0 + wave_amp * noise)
            
            # Spherical to Cartesian
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            
            # Rotate Y
            x2 = x * cos_ry - z * sin_ry
            z2 = x * sin_ry + z * cos_ry
            
            # Rotate X
            y3 = y * cos_rx - z2 * sin_rx
            z3 = y * sin_rx + z2 * cos_rx
            
            # Depth sorting hint (skip points very far in the back for aesthetic semi-transparency)
            if z3 < -base_radius * 0.5:
                # Dimmer for back points
                painter.setBrush(QColor(c_glow.red(), c_glow.green(), c_glow.blue(), 100))
                dot_size = 1.0
            else:
                painter.setBrush(QColor(c_core.red(), c_core.green(), c_core.blue(), 255))
                dot_size = 2.0 + (z3 / base_radius) # closer points are larger
            
            # Project to 2D
            proj_x = cx + x2
            proj_y = cy + y3
            
            painter.drawEllipse(QPointF(proj_x, proj_y), dot_size, dot_size)
