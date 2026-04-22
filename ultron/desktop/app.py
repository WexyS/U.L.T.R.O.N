import os
import sys
import asyncio
import qasync
import webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QScrollArea, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from ultron.desktop.widgets import AnimatedOrb
from ultron.skills.system_monitor import SystemMonitor
from ultron.skills.offline_hotword import OfflineHotwordListener

class UltronDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ULTRON v2.1 TACTICAL INTERFACE")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1000, 700)
        
        self.drag_pos = None
        self._is_processing = False
        self.current_lang = "TR"
        self.chat_history = []
        
        self.init_ui()
        self.load_theme()
        
        # Start system monitor loop
        self.sys_timer = QTimer(self)
        self.sys_timer.timeout.connect(self.update_system_stats)
        self.sys_timer.start(2000)
        
        # Wake word listener
        self.hotword = OfflineHotwordListener("ultron", self.hotword_callback, self.hotword_log_callback)
        
        self.log_message("ULTRON GLOBAL SECURITY NETWORK ONLINE.")
        self.log_message("ALL SYSTEMS NOMINAL. AWAITING DIRECTIVES.")
        self.update_system_stats()

    def hotword_callback(self):
        # Arka plandaki pyAudio dinleyicisinden gelen sinyali güvenli Main GUI Thread'ine ve asıl event loop'una taşıyoruz.
        QTimer.singleShot(0, self.on_wake_word_triggered)

    def hotword_log_callback(self, msg: str):
        # Arka plan iş parçacığından doğrudan UI'ye log yazabilmek için callback wrapper
        # PyQt timer aracılığıyla ana iş parçacığına taşı
        QTimer.singleShot(0, lambda: self.log_message(msg))

    def init_ui(self):
        # Central HUD widget
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("CentralHUD")
        self.setCentralWidget(self.central_widget)
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # --- HEADER ---
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_label = QLabel("U.L.T.R.O.N.")
        title_label.setObjectName("TitleLabel")
        subtitle_label = QLabel("GLOBAL SECURITY & AI PLATFORM")
        subtitle_label.setObjectName("SubtitleLabel")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        minimize_btn = QPushButton("_")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.setObjectName("MinimizeBtn")
        minimize_btn.clicked.connect(self.showMinimized)
        
        close_btn = QPushButton("X")
        close_btn.setFixedSize(30, 30)
        close_btn.setObjectName("CloseBtn")
        close_btn.clicked.connect(self.exit_system)
        
        header_layout.addWidget(minimize_btn)
        header_layout.addWidget(close_btn)
        main_layout.addLayout(header_layout)
        
        # --- CENTER DASHBOARD ---
        center_layout = QHBoxLayout()
        
        # LEFT PANEL (Action Skills)
        left_panel = QGroupBox("STRATEGIC ASSETS")
        left_layout = QVBoxLayout(left_panel)
        btn_weather = QPushButton("GLOBAL WEATHER")
        btn_weather.clicked.connect(lambda: self.log_message("> FETCHING ATMOSPHERIC DATA..."))
        btn_maps = QPushButton("SATELLITE MAPS")
        btn_maps.clicked.connect(lambda: self.open_url("https://maps.google.com"))
        btn_youtube = QPushButton("INTERCEPT YOUTUBE")
        btn_youtube.clicked.connect(lambda: self.open_url("https://youtube.com"))
        btn_camera = QPushButton("ENGAGE OPTICS (CAMERA)")
        btn_camera.clicked.connect(lambda: self.log_message("> ACCESSING SECURE WEBCAM FEED..."))
        
        left_layout.addWidget(btn_weather)
        left_layout.addWidget(btn_maps)
        left_layout.addWidget(btn_youtube)
        left_layout.addWidget(btn_camera)
        left_layout.addStretch()
        left_panel.setFixedWidth(200)
        center_layout.addWidget(left_panel)
        
        # CORE ORB
        orb_layout = QVBoxLayout()
        self.reactor = AnimatedOrb()
        orb_layout.addWidget(self.reactor, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Mini Stats under Orb
        stats_layout = QHBoxLayout()
        self.lbl_cpu = QLabel("CPU: 0%")
        self.lbl_ram = QLabel("RAM: 0%")
        self.lbl_bat = QLabel("PWR: Check")
        self.lbl_ip = QLabel("NET: Check")
        stats_layout.addWidget(self.lbl_cpu)
        stats_layout.addWidget(self.lbl_ram)
        stats_layout.addWidget(self.lbl_bat)
        stats_layout.addWidget(self.lbl_ip)
        orb_layout.addLayout(stats_layout)
        
        center_layout.addLayout(orb_layout)
        
        # RIGHT PANEL (Security & Agent Actions)
        right_panel = QGroupBox("CORE SYSTEMS")
        right_layout = QVBoxLayout(right_panel)
        btn_email = QPushButton("EMAIL AGENT")
        btn_email.clicked.connect(lambda: self.log_message("> ENGAGING EMAIL TRANSMISSION SUBROUTINE..."))
        btn_net_scan = QPushButton("NETWORK SCAN")
        btn_net_scan.clicked.connect(lambda: self.log_message("> INITIATING LOCAL SUBNET SCAN..."))
        btn_stealth = QPushButton("STEALTH PROTOCOL")
        btn_stealth.clicked.connect(lambda: self.log_message("> STEALTH MODE ACTIVATED. FOOTPRINT MINIMIZED."))
        btn_calc = QPushButton("TRAJECTORY CALC")
        btn_calc.clicked.connect(lambda: self.log_message("> MATH ENGINE LOADED."))
        
        right_layout.addWidget(btn_email)
        right_layout.addWidget(btn_net_scan)
        right_layout.addWidget(btn_stealth)
        right_layout.addWidget(btn_calc)
        right_layout.addStretch()
        right_panel.setFixedWidth(200)
        center_layout.addWidget(right_panel)
        
        main_layout.addLayout(center_layout)
        
        # --- LOGS ---
        log_scroll = QScrollArea()
        log_scroll.setWidgetResizable(True)
        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.log_layout.setContentsMargins(5, 5, 5, 5)
        log_scroll.setWidget(self.log_container)
        log_scroll.setFixedHeight(120)
        
        main_layout.addWidget(log_scroll)
        
        # --- CONTROLS ---
        controls_layout = QHBoxLayout()
        self.btn_listen = QPushButton("ENABLE AUDIO PROTOCOL")
        self.btn_listen.setMinimumHeight(40)
        self.btn_listen.clicked.connect(self.toggle_listening)
        
        self.btn_lang = QPushButton("LANGUAGE: TR")
        self.btn_lang.setMinimumHeight(40)
        self.btn_lang.clicked.connect(self.toggle_language)
        
        self.btn_test = QPushButton("DIAGNOSTICS CYCLE")
        self.btn_test.setMinimumHeight(40)
        self.btn_test.clicked.connect(self.run_test_protocol)
        
        controls_layout.addWidget(self.btn_listen)
        controls_layout.addWidget(self.btn_lang)
        controls_layout.addWidget(self.btn_test)
        
        main_layout.addLayout(controls_layout)

    def load_theme(self):
        theme_path = os.path.join(os.path.dirname(__file__), "theme.qss")
        if os.path.exists(theme_path):
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            self.log_message(f"ERROR: Theme file not found at {theme_path}")

    def update_system_stats(self):
        cpu = SystemMonitor.get_cpu_usage()
        ram_pct, ram_desc = SystemMonitor.get_ram_usage()
        
        self.lbl_cpu.setText(f"CPU: {cpu}%")
        self.lbl_ram.setText(f"RAM: {ram_pct}%")
        self.lbl_bat.setText(f"BAT: {SystemMonitor.get_battery_status()}")
        self.lbl_ip.setText(f"IP: {SystemMonitor.get_ip_address()}")

    def log_message(self, message: str):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        lbl = QLabel(f"{timestamp} {message}")
        lbl.setObjectName("LogText")
        self.log_layout.addWidget(lbl)
        QTimer.singleShot(50, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        scroll_area = self.centralWidget().findChild(QScrollArea)
        if scroll_area:
            bar = scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    def open_url(self, url):
        self.log_message(f"> INTERCEPTING EXTERNAL FEED: {url}")
        webbrowser.open(url)
        self.reactor.set_state("processing")
        QTimer.singleShot(2000, lambda: self.reactor.set_state("idle"))

    def toggle_language(self):
        self.current_lang = "EN" if self.current_lang == "TR" else "TR"
        self.btn_lang.setText(f"LANGUAGE: {self.current_lang}")
        self.log_message(f"> LANGUAGE SET TO {self.current_lang}")

    def toggle_listening(self):
        if not self.hotword.running:
            self.btn_listen.setText("AUDIO PROTOCOL ONLINE")
            self.log_message("> AUDIO SENSORS ENGAGED. LISTENING FOR 'ULTRON'...")
            self.reactor.set_state("listening")
            self.hotword.start()
        else:
            self.btn_listen.setText("ENABLE AUDIO PROTOCOL")
            self.log_message("> AUDIO SENSORS DISENGAGED.")
            self.reactor.set_state("idle")
            self.hotword.stop()

    def on_wake_word_triggered(self):
        if self._is_processing:
            return
        self.log_message("> WAKE WORD DETECTED. INITIATING CORE DIRECTIVES.")
        self.reactor.set_state("listening")
        asyncio.ensure_future(self.process_voice_interaction())

    async def process_voice_interaction(self):
        self._is_processing = True
        try:
            import speech_recognition as sr
            import httpx
            import pygame
            import io
            import os
            from tempfile import NamedTemporaryFile

            # 1. Listen for command
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                self.log_message("> SPEAK NOW...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            self.reactor.set_state("processing")
            self.log_message("> TRANSCRIBING AUDIO (LOCAL WHISPER)...")
            
            # 2. STT (Local Whisper)
            try:
                from ultron.skills.whisper_engine import whisper_engine
                # Save audio to temp file for Whisper
                with NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    f.write(audio.get_wav_data())
                    temp_audio_path = f.name
                
                lang_code = "tr" if self.current_lang == "TR" else "en"
                user_text = await whisper_engine.transcribe(temp_audio_path, language=lang_code)
                
                try: os.remove(temp_audio_path)
                except: pass
                
                if not user_text:
                    raise ValueError("No speech detected.")
                    
                self.log_message(f"> USER ({self.current_lang}): {user_text}")
            except Exception as e:
                self.log_message(f"> STT ERROR: {e}")
                self.reactor.set_state("idle")
                self._is_processing = False
                return

            # 3. Chat with Backend
            self.chat_history.append({"role": "user", "content": user_text})
            self.log_message("> CONSULTING ULTRON CORE...")
            sys_msg = "Please reply strictly in Turkish." if self.current_lang == "TR" else "Please reply strictly in English."
            
            # Combine system message with last 10 messages of history
            messages_payload = [{"role": "system", "content": sys_msg}] + self.chat_history[-10:]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                chat_resp = await client.post("http://localhost:8000/api/v2/chat", json={
                    "messages": messages_payload
                })
                if chat_resp.status_code == 200:
                    data = chat_resp.json()
                    ai_text = data.get("content", "I am unable to process that.")
                    self.chat_history.append({"role": "assistant", "content": ai_text})
                    self.log_message(f"> ULTRON: {ai_text}")
                else:
                    ai_text = "Backend communication failed."
                    self.log_message("> ERROR: Backend unreachable.")

            # 4. TTS
            self.log_message("> SYNTHESIZING RESPONSE...")
            tts_lang = "tr" if self.current_lang == "TR" else "en"
            async with httpx.AsyncClient(timeout=30.0) as client:
                tts_resp = await client.post("http://localhost:8000/api/v2/tts", json={
                    "text": ai_text,
                    "language": tts_lang
                })
                if tts_resp.status_code == 200:
                    # Play Audio via Pygame
                    with NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                        f.write(tts_resp.content)
                        temp_path = f.name
                    
                    pygame.mixer.init()
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.1)
                    pygame.mixer.quit()
                    
                    try: os.remove(temp_path)
                    except: pass
                else:
                    self.log_message("> ERROR: TTS service failed.")

        except Exception as e:
            self.log_message(f"> VOICE SYSTEM ERROR: {e}")
        finally:
            self._is_processing = False
            self.reactor.set_state("listening") if self.hotword.running else self.reactor.set_state("idle")

    def run_test_protocol(self):
        self.log_message("RUNNING DIAGNOSTICS CYCLE...")
        self.reactor.set_state("processing")
        QTimer.singleShot(3000, lambda: self.reactor.set_state("idle"))

    def exit_system(self):
        self.log_message("SHUTTING DOWN CORE SYSTEMS...")
        self.hotword.stop()
        try:
            from pyowm import __version__ # Dummy cleanup
        except:
            pass
        # Kill running command
        try:
            self.reactor.timer.stop()
            self.sys_timer.stop()
        except Exception:
            pass
        QApplication.quit()

    # Sürükle-bırak pencere hareketi için
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

def run_desktop():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = UltronDesktop()
    window.show()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    run_desktop()
