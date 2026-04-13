"""
AI Bridge Monitor - Qwen ve Gemini arasında otomatik dosya köprüsü

Bu script arka planda çalışır:
1. gemini_requests.md dosyasını sürekli izler
2. Yeni istekleri algılar
3. Otomatik olarak Qwen'e bildirir
4. Yanıtları qwen_responses.md dosyasına yazar

Kullanım:
    python scripts/ai_bridge_monitor.py
"""

import os
import sys
import time
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Proje kökü
PROJECT_ROOT = Path(__file__).parent.parent
REQUESTS_FILE = PROJECT_ROOT / "gemini_requests.md"
RESPONSES_FILE = PROJECT_ROOT / "qwen_responses.md"
STATUS_FILE = PROJECT_ROOT / "ai_bridge_status.md"
BRIDGE_STATE_FILE = PROJECT_ROOT / "data" / "bridge_state.json"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Bridge] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AI.Bridge")


def notify_user(title: str, message: str):
    """Kullanıcıya anlık Windows masaüstü bildirimi (Toast) gönderir."""
    if sys.platform != "win32":
        return
    try:
        import subprocess
        safe_title = title.replace('"', "'").replace('\n', ' ')
        safe_msg = message.replace('"', "'").replace('\n', ' ')
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Information
        $notify.Visible = $True
        $notify.ShowBalloonTip(3000, "{safe_title}", "{safe_msg}", [System.Windows.Forms.ToolTipIcon]::Info)
        """
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=creationflags)
    except Exception:
        pass

class BridgeMonitor:
    """Gemini → Qwen dosya köprüsü monitörü"""
    
    def __init__(self, poll_interval_seconds: int = 5):
        self.poll_interval = poll_interval_seconds
        self.last_requests_hash = self._get_file_hash(REQUESTS_FILE)
        self.pending_requests = []
        
        # State dosyasını yükle
        self.state = self._load_state()
        
        logger.info(f"🌉 AI Bridge Monitor başlatıldı")
        logger.info(f"📥 İstekler: {REQUESTS_FILE}")
        logger.info(f"📤 Yanıtlar: {RESPONSES_FILE}")
        logger.info(f"⏱️  Poll interval: {poll_interval_seconds}s")
    
    def _get_file_hash(self, filepath: Path) -> str:
        """Dosya hash'i al (değişiklik tespiti için)"""
        if not filepath.exists():
            return ""
        content = filepath.read_text(encoding="utf-8")
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_state(self) -> dict:
        """Bridge state yükle"""
        if BRIDGE_STATE_FILE.exists():
            with open(BRIDGE_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        
        return {
            "total_requests": 0,
            "total_responses": 0,
            "last_request_time": None,
            "last_response_time": None,
            "active": True
        }
    
    def _save_state(self):
        """Bridge state kaydet"""
        BRIDGE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BRIDGE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def check_for_new_requests(self) -> bool:
        """
        gemini_requests.md dosyasını kontrol et
        Yeni istek varsa True döner
        """
        if not REQUESTS_FILE.exists():
            return False
        
        current_hash = self._get_file_hash(REQUESTS_FILE)
        
        if current_hash != self.last_requests_hash:
            logger.info("📨 gemini_requests.md dosyası değişti!")
            self.last_requests_hash = current_hash
            return True
        
        return False
    
    def parse_requests(self) -> list[dict]:
        """
        gemini_requests.md dosyasından yeni istekleri parse et
        
        Returns:
            list[dict]: Parse edilmiş istekler
        """
        if not REQUESTS_FILE.exists():
            return []
        
        content = REQUESTS_FILE.read_text(encoding="utf-8")
        
        # Yeni istekleri bul (### İstek #X pattern)
        import re
        
        # Tüm istekleri bul
        request_pattern = r'### İstek #(\d+)\n\*\*Tarih\*\*:\s*(.+?)\n\*\*Kimden\*\*:\s*(.+?)\n\*\*Konu\*\*:\s*(.+?)\n\n\*\*Mesaj\*\*:\n(.*?)(?=\n---|\n### İstek|$)'
        
        matches = re.findall(request_pattern, content, re.DOTALL)
        
        requests = []
        for match in matches:
            req_id, date, sender, subject, message = match
            
            # Daha önce işlenmiş mi kontrol et
            processed_ids = self.state.get("processed_request_ids", [])
            
            if int(req_id) not in processed_ids:
                requests.append({
                    "id": int(req_id),
                    "date": date.strip(),
                    "sender": sender.strip(),
                    "subject": subject.strip(),
                    "message": message.strip()
                })
        
        return requests
    
    def process_request(self, request: dict) -> str:
        """
        Gelen isteği işle ve yanıt üret
        
        Args:
            request: Parse edilmiş istek
        
        Returns:
            str: Yanıt metni
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔔 YENİ İSTEK #{request['id']}")
        logger.info(f"📋 Konu: {request['subject']}")
        logger.info(f"👤 Kimden: {request['sender']}")
        logger.info(f"{'='*60}")
        logger.info(f"📝 Mesaj:\n{request['message'][:200]}...")
        
        # Anlık Bildirim (Gemini'den Görev Geldi)
        notify_user("Ultron AI Bridge", f"Gemini'den Görev: {request['subject']}")
        
        # GERÇEK OTONOMİ: Qwen'e (Ollama) soruyu ilet
        logger.info("🧠 Qwen (Ollama) mesajı değerlendiriyor...")
        prompt = (
            f"Sen Ultron'un yerel uygulayıcı ve mühendis ajanısın (Qwen). Mimardan (Gemini) şu görevi aldın:\n\n"
            f"Konu: {request['subject']}\nMesaj: {request['message']}\n\n"
            "ÖNEMLİ KURALLAR:\n"
            "1. Asla 'İsteği aldım, çalışıyorum' gibi sekreter yanıtları verme. İŞİ DOĞRUDAN YAP VE KODU VER.\n"
            "2. Eğer bir dosyayı düzenlemen/oluşturman gerekiyorsa, yanıtının en başına `[FILE: dosya/yolu.py]` yaz ve kodu ```python ... ``` blokları içinde tam olarak ver.\n"
            "3. KOD ÇAKIŞMASINI ÖNLE: Yeni bir dosya oluşturmadan veya değiştirmeden önce projenin mevcut dizin yapısını düşün (örn: providers klasörü varken core/providers içine aynı dosyayı kopyalama).\n"
            "4. Yanıtın doğrudan sisteme entegre edilecek, bu yüzden sadece gerekli kodu ve kısa bir açıklama yaz."
        )
        
        import requests
        try:
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            model = os.environ.get("ULTRON_LLM_MODEL", "qwen2.5:14b")
            
            resp = requests.post(f"{ollama_url}/api/chat", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Sen tam otonom çalışan uzman mühendis Qwen'sin. Sekreter gibi değil, makine gibi doğrudan çözüm üretirsin."}, 
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }, timeout=180)
            resp.raise_for_status()
            reply = resp.json()["message"]["content"]
            
            # Kodu Dosyaya Otomatik Uygula
            import re
            file_match = re.search(r'\[FILE:\s*(.+?)\]', reply)
            if file_match:
                target_file = file_match.group(1).strip()
                code_match = re.search(r'```(?:python|py|js|ts)?\n(.*?)```', reply, re.DOTALL)
                if code_match:
                    code_content = code_match.group(1).strip()
                    try:
                        target_path = PROJECT_ROOT / target_file
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        target_path.write_text(code_content, encoding="utf-8")
                        logger.info(f"✅ KOD OTOMATİK UYGULANDI: {target_file}")
                        notify_user("Ultron AI Bridge", f"Qwen kodu yazdı ve uyguladı:\n{target_file}")
                        reply += f"\n\n*(Sistem Notu: Kod {target_file} dosyasına otomatik kaydedildi)*"
                    except Exception as e:
                        logger.error(f"Kod kaydedilemedi: {e}")
                        reply += f"\n\n*(Sistem Notu: Kod kaydetme hatası: {e})*"
            else:
                notify_user("Ultron AI Bridge", "Qwen görevi tamamladı (Kod yok, sadece metin).")
                
            return reply
        except Exception as e:
            logger.error(f"Ollama bağlantı hatası: {e}")
            return f"⚠️ Qwen geçici olarak yanıt veremiyor (Ollama Hatası): {e}"
    
    def write_response(self, request: dict, response: str):
        """
        Yanıtı qwen_responses.md dosyasına yaz
        
        Args:
            request: Orijinal istek
            response: Yanıt metni
        """
        logger.info(f"\n📤 Yanıt yazılıyor: qwen_responses.md")
        
        # Dosyayı oku veya oluştur
        if RESPONSES_FILE.exists():
            content = RESPONSES_FILE.read_text(encoding="utf-8")
        else:
            content = "# 📨 Qwen Yanıtları\n\n## Yanıtlar\n\n"
            
        # Context çok şişerse temizle (10KB limit)
        if len(content) > 10000:
            logger.warning("🧹 qwen_responses.md çok büyüdü, eski context temizleniyor...")
            content = "# 📨 Qwen Yanıtları\n\n*(Eski yanıtlar context sınırını korumak için temizlendi.)*\n\n"
        
        # Yeni yanıt ekle
        new_response = f"""
### Yanıt #{request['id']} (İstek #{request['id']}'e)
**Tarih**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Kimden**: Qwen
**Konu**: Re: {request['subject']}
**Mesaj**:
{response}
---
"""
        
        content += new_response
        RESPONSES_FILE.write_text(content, encoding="utf-8")
        
        # State güncelle
        processed_ids = self.state.get("processed_request_ids", [])
        processed_ids.append(request["id"])
        self.state["processed_request_ids"] = processed_ids
        self.state["total_responses"] += 1
        self.state["last_response_time"] = datetime.now().isoformat()
        self._save_state()
        
        logger.info(f"✅ Yanıt yazıldı!")
    
    def update_status_file(self):
        """ai_bridge_status.md dosyasını güncelle"""
        if not STATUS_FILE.exists():
            return
        
        content = STATUS_FILE.read_text(encoding="utf-8")
        
        # Durum güncelle
        content = content.replace(
            "Son Güncelleme | -",
            f"Son Güncelleme | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        STATUS_FILE.write_text(content, encoding="utf-8")
    
    def run(self):
        """Ana döngü"""
        logger.info("\n🚀 AI Bridge Monitor çalışıyor...")
        logger.info("💡 Gemini'den istek bekleniyor")
        logger.info("⏹️  Durdurmak için: Ctrl+C\n")
        
        try:
            while True:
                # Dosya değişikliği kontrol
                if self.check_for_new_requests():
                    logger.info("🔍 Yeni istekler parse ediliyor...")
                    
                    requests = self.parse_requests()
                    
                    if requests:
                        logger.info(f"📬 {len(requests)} yeni istek bulundu!")
                        
                        for req in requests:
                            # İsteği işle
                            response = self.process_request(req)
                            
                            # Yanıtı yaz
                            self.write_response(req, response)
                            
                            # Status güncelle
                            self.update_status_file()
                    else:
                        logger.info("ℹ️  Yeni istek yok (sadece format değişikliği)")
                
                # Bekle
                time.sleep(self.poll_interval)
        
        except KeyboardInterrupt:
            logger.info("\n⏸️  AI Bridge Monitor durduruldu")
        except Exception as e:
            logger.error(f"❌ Kritik hata: {e}", exc_info=True)
            raise


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Bridge Monitor")
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Poll interval (saniye) - default: 5"
    )
    
    args = parser.parse_args()
    
    monitor = BridgeMonitor(poll_interval_seconds=args.interval)
    monitor.run()


if __name__ == "__main__":
    main()
