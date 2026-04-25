"""
Ultron Action: open_app — Uygulama ve Web sitesi açar (Windows/Mac/Linux).
"""

import os
import platform
import subprocess
import webbrowser
import logging

logger = logging.getLogger(__name__)

# Uygulama takma adları - Windows için URI protokolleri ve start komutları eklendi
_APP_ALIASES = {
    "steam": {"Windows": "steam://open/main", "Darwin": "Steam", "Linux": "steam"},
    "spotify": {"Windows": "spotify:", "Darwin": "Spotify", "Linux": "spotify"},
    "whatsapp": {"Windows": "whatsapp:", "Darwin": "WhatsApp", "Linux": "whatsapp"},
    "discord": {"Windows": "discord:", "Darwin": "Discord", "Linux": "discord"},
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "google chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "calculator": {"Windows": "calc", "Darwin": "Calculator", "Linux": "gnome-calculator"},
    "notepad": {"Windows": "notepad", "Darwin": "TextEdit", "Linux": "gedit"},
    "word": {"Windows": "winword", "Darwin": "Microsoft Word", "Linux": "libreoffice --writer"},
    "excel": {"Windows": "excel", "Darwin": "Microsoft Excel", "Linux": "libreoffice --calc"},
    "paint": {"Windows": "mspaint", "Darwin": "Preview", "Linux": "gimp"},
    "cmd": {"Windows": "cmd", "Darwin": "Terminal", "Linux": "bash"},
    "terminal": {"Windows": "cmd", "Darwin": "Terminal", "Linux": "gnome-terminal"},
}

# Web siteleri için özel yönlendirmeler
_WEB_ALIASES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "reddit": "https://www.reddit.com",
    "github": "https://github.com",
    "netflix": "https://www.netflix.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "chatgpt": "https://chat.openai.com",
}

def _normalize(raw: str) -> str:
    system = platform.system()
    key = raw.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(system, raw)
    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(system, raw)
    return raw

def _launch(app_name: str) -> bool:
    system = platform.system()
    try:
        if system == "Windows":
            # 1. URI Protokolleri (steam://, spotify: vb.) kontrolü
            if "://" in app_name or app_name.endswith(":"):
                os.startfile(app_name)
                return True
            
            # 2. Windows Start komutu (Registry'den otomatik bulur)
            # stderr DEVNULL YAPILMADI, hataları yakalayabileceğiz.
            result = subprocess.run(f"start {app_name}", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                logger.error(f"Start komutu başarısız: {result.stderr}")
                return False
                
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
            return True
        else:
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception as e:
        logger.error(f"Uygulama başlatma hatası: {e}")
        return False

def run(parameters: dict, **kwargs) -> str:
    """Uygulama veya Web sitesi açar."""
    app_name = (parameters or {}).get("app_name", "").strip().lower()
    if not app_name:
        return "Hata: Lütfen açmak istediğiniz uygulamanın veya sitenin adını belirtin."

    # 1. ÖNCE WEB SİTELERİNİ KONTROL ET
    for web_key, url in _WEB_ALIASES.items():
        if web_key in app_name:
            webbrowser.open(url)
            return f"Başarılı: {web_key} tarayıcıda açıldı."

    # 2. YEREL UYGULAMALARI AÇ
    normalized = _normalize(app_name)
    success = _launch(normalized)

    if success:
        return f"Başarılı: {app_name} başlatıldı."

    # Normalized isimle açılmazsa orijinal ismi (start komutu ile) dene
    if normalized != app_name:
        if _launch(app_name):
            return f"Başarılı: {app_name} başlatıldı."

    return f"Hata: '{app_name}' açılamadı. Uygulamanın Windows PATH'inde yüklü olduğundan emin olun."
