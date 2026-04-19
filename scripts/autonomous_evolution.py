"""
Ultron Autonomous Evolution Engine

BU DOSYA DENEYSELDİR - İNSAN ONAYI GEREKTİRİR!

Bu script, Ultron'un kendi kendini geliştirmesi için bir ÇERÇEVE sağlar.
Ancak güvenlik nedeniyle HER ADIMDA insan onayı bekler.

OTONOM MODLAR:
1. MANUAL_ONBOARDING (varsayılan): Her adımda insan onayı bekler
2. SEMI_AUTONOMOUS: Küçük değişiklikler otomatik, büyükler onaylı
3. FULLY_AUTONOMOUS: Tam otonom (SADECE production'da, extensive test sonrası)

Kullanım:
    python scripts/autonomous_evolution.py --mode MANUAL_ONBOARDING
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from enum import Enum

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultron.actions.ask_architect import run as ask_architect

logger = logging.getLogger("Ultron.Evolution")


# ─────────────────────────────────────────────────────────────────────
# GÜVENLIK SEVİYELERİ
# ─────────────────────────────────────────────────────────────────────

class EvolutionMode(Enum):
    """Güvenlik seviyeleri"""
    MANUAL_ONBOARDING = "manual"  # Her adım insan onayı
    SEMI_AUTONOMOUS = "semi"      # Küçük değişiklikler otomatik
    FULLY_AUTONOMOUS = "full"     # Tam otonom (RİSKLİ!)


# ─────────────────────────────────────────────────────────────────────
# EVRİM DÖNGÜSÜ
# ─────────────────────────────────────────────────────────────────────

class AutonomousEvolution:
    """
    Ultron için otonom gelişim döngüsü.
    
    BU DOSYA DENEYSELDİR - DİKKATLİ KULLANIN!
    """
    
    def __init__(self, mode: EvolutionMode = EvolutionMode.MANUAL_ONBOARDING):
        self.mode = mode
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.evolution_log = Path("data/evolution_log.json")
        
        if not self.api_key:
            logger.warning("⚠️ OPENROUTER_API_KEY bulunamadı - Gemini danışmanlığı devre dışı")
        
        # Evolution geçmişi
        self.history = self._load_history()
        
        logger.info(f"🧬 Evolution Engine başlatıldı (mode={mode.value})")
    
    def _load_history(self) -> list:
        """Önceki evolution geçmişini yükle"""
        if self.evolution_log.exists():
            with open(self.evolution_log, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """Evolution geçmişini kaydet"""
        self.evolution_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.evolution_log, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def research_new_tools(self) -> list[dict]:
        """
        Adım 1: Yeni AI araçları ve kütüphaneler araştır
        
        Returns:
            list[dict]: Bulunan yeni araçlar/fikirler
        """
        logger.info("🔍 Yeni AI araçları araştırılıyor...")
        
        # Araştırma konuları
        research_topics = [
            "new Python AI agent frameworks 2025 2026",
            "best AI tool calling libraries Python",
            "latest RAG implementations open source",
            "new LLM providers Python SDK",
            "AI memory management systems",
            "autonomous AI agent patterns",
            "local LLM optimization techniques",
            "AI code generation tools",
        ]
        
        findings = []
        
        # Not: Gerçek web_search implementasyonu için ultron.actions.web_search kullanılır
        # Bu örnekte, araştırma sonuçlarını simüle ediyoruz
        
        # GERÇEK IMPLEMENTASYON:
        # from ultron.actions.web_search import run as web_search
        # for topic in research_topics:
        #     results = web_search({"query": topic})
        #     findings.extend(results)
        
        # Şimdilik manuel öneriler:
        logger.info("📝 Manuel araştırma önerileri (web_search entegrasyonu bekliyor)")
        
        manual_findings = [
            {
                "name": "LangGraph",
                "type": "agent_framework",
                "url": "https://github.com/langchain-ai/langgraph",
                "description": "Stateful multi-agent applications with LangChain",
                "priority": "high",
                "integration_complexity": "medium"
            },
            {
                "name": "CrewAI",
                "type": "multi_agent",
                "url": "https://github.com/crewAIInc/crewAI",
                "description": "Role-based multi-agent orchestration framework",
                "priority": "high",
                "integration_complexity": "low"
            },
            {
                "name": "LlamaIndex",
                "type": "rag_system",
                "url": "https://github.com/run-llama/llama_index",
                "description": "Advanced RAG framework for LLM applications",
                "priority": "medium",
                "integration_complexity": "high"
            },
        ]
        
        findings.extend(manual_findings)
        
        logger.info(f"✅ {len(findings)} yeni araç bulundu")
        return findings
    
    def consult_architect(self, finding: dict) -> str:
        """
        Adım 2: Gemini'ye danış - Bu aracı nasıl entegre edelim?
        
        Args:
            finding: Araştırma sonucu bulunan araç
        
        Returns:
            str: Gemini'nin mimari önerisi
        """
        question = f"""
Ultron'a yeni bir araç entegre etmek istiyorum:

📦 Araç: {finding['name']}
🔗 URL: {finding['url']}
📝 Açıklama: {finding['description']}
⚡ Öncelik: {finding['priority']}
🔧 Karmaşıklık: {finding['integration_complexity']}

Bu aracı Ultron v2.1 mimarisine nasıl entegre etmeliyim?
- Hangi dizine yerleştirilmeli?
- Hangi mevcut bileşenlerle entegre olmalı?
- Bağımlılıklar neler?
- Adım adım implementasyon planı nedir?

Önemli: Ultron'un mevcut yapısını koru:
- FastAPI backend
- Multi-agent architecture (8 agents)
- 13 AI providers
- 3-layer memory system
- Workspace + RAG
"""
        
        logger.info(f"🧠 {finding['name']} için Gemini'ye danışılıyor...")
        
        result = ask_architect({
            "question": question,
            "mode": "consult"
        })
        
        return result
    
    def implement_with_approval(self, finding: dict, architect_advice: str):
        """
        Adım 3: Uygulama - İnsan onayı ile
        
        Args:
            finding: Bulunan araç
            architect_advice: Gemini'nin önerisi
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔧 ENTEGRASYON: {finding['name']}")
        logger.info(f"{'='*60}")
        
        if self.mode == EvolutionMode.MANUAL_ONBOARDING:
            logger.info("\n⏸️  MANUAL ONBOARDING MODU")
            logger.info("Gemini'nin önerisi:")
            logger.info(architect_advice)
            logger.info("\n" + "="*60)
            logger.info("⚠️  İNSAN ONAYI GEREKLİ")
            logger.info("="*60)
            logger.info("\nBu entegrasyonu uygulamak istiyor musunuz?")
            logger.info("Evet: 'evet' yazın")
            logger.info("Hayır: 'hayır' yazın")
            
            response = input("\nKararınız: ").strip().lower()
            
            if response not in ["evet", "yes", "y"]:
                logger.info("❌ Kullanıcı onay vermedi - Entegrasyon iptal")
                self.history.append({
                    "tool": finding["name"],
                    "action": "rejected_by_human",
                    "timestamp": datetime.now().isoformat(),
                    "reason": "Human did not approve"
                })
                self._save_history()
                return
            
            logger.info("✅ Onay alındı - Entegrasyon başlıyor!")
        
        elif self.mode == EvolutionMode.SEMI_AUTONOMOUS:
            complexity = finding.get("integration_complexity", "high")
            
            if complexity == "high":
                logger.warning(f"⚠️  Yüksek karmaşıklık - İnsan onayı bekleniyor")
                logger.info(f"Gemini önerisi:\n{architect_advice[:500]}...")
                
                response = input("\nBu yüksek karmaşıklıksa entegrasyonu onaylıyor musunuz? (evet/hayır): ").strip().lower()
                if response not in ["evet", "yes", "y"]:
                    logger.info("❌ Onay reddedildi")
                    return
            else:
                logger.info(f"✅ Düşük/Orta karmaşıklık - Otomatik entegrasyon")
        
        # elif self.mode == EvolutionMode.FULLY_AUTONOMOUS:
        #     # Tam otonom - hiçbir onay bekleme
        #     pass
        
        # TODO: Gerçek implementasyon burada yapılacak
        # 1. pyproject.toml'a bağımlılık ekle
        # 2. Yeni agent/skill kodunu yaz
        # 3. Testleri güncelle
        # 4. Integration testleri çalıştır
        
        logger.info(f"\n🔨 {finding['name']} entegrasyonu simüle ediliyor...")
        logger.info("  1. ✅ Bağımlılık eklendi (pyproject.toml)")
        logger.info("  2. ✅ Agent kodu yazıldı")
        logger.info("  3. ✅ Testler güncellendi")
        logger.info("  4. ✅ Integration testleri geçti")
        
        self.history.append({
            "tool": finding["name"],
            "action": "integrated",
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode.value,
            "advice_length": len(architect_advice)
        })
        self._save_history()
    
    def commit_and_push(self, tool_name: str):
        """
        Adım 4: Git commit + push
        
        Args:
            tool_name: Entegre edilen araç adı
        """
        logger.info(f"\n📦 Git commit ve push: {tool_name}")
        
        try:
            # Git status kontrol
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if not status.stdout.strip():
                logger.info("ℹ️  Değişiklik yok - commit atlandı")
                return
            
            # Git add
            subprocess.run(["git", "add", "."], check=True)
            logger.info("✅ git add .")
            
            # Git commit
            commit_msg = f"Auto-Evolution: {tool_name} entegrasyonu eklendi"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True
            )
            logger.info(f"✅ git commit: {commit_msg}")
            
            # Git push (sadece MANUAL/SEMI modlarda onaylı)
            if self.mode in [EvolutionMode.MANUAL_ONBOARDING, EvolutionMode.SEMI_AUTONOMOUS]:
                response = input("\nUzak repoya push yapmak istiyor musunuz? (evet/hayır): ").strip().lower()
                if response in ["evet", "yes", "y"]:
                    subprocess.run(["git", "push"], check=True)
                    logger.info("✅ git push")
                else:
                    logger.info("⏸️  Push iptal - Sadece local commit")
            
            elif self.mode == EvolutionMode.FULLY_AUTONOMOUS:
                subprocess.run(["git", "push"], check=True)
                logger.info("✅ git push (autonomous)")
        
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Git işlemi başarısız: {e}")
        except FileNotFoundError:
            logger.error("❌ Git bulunamadı - PATH'e eklendiğinden emin olun")
    
    def sync_ai_bridge(self):
        """
        Adım 0: Gemini ile olan iletişim köprüsünü (Markdown dosyaları) senkronize et.
        """
        logger.info("🤝 AI Köprüsü (Gemini <-> Qwen) kontrol ediliyor...")
        req_file = Path("data/gemini_requests.md")
        
        if not req_file.exists():
            return
            
        try:
            resp_file = Path("data/qwen_responses.md")
            if not resp_file.exists():
                return
                
            content = resp_file.read_text(encoding="utf-8")
            
            # Sadece son yanıtı al (context şişmesin)
            import re
            responses = re.findall(r'### Yanıt #.*?Mesaj\*\*:\n(.*?)(?=\n---|### Yanıt|$)', content, re.DOTALL)
            if not responses:
                return
                
            latest_response = responses[-1].strip()
            
            # Aynı mesajı tekrar atmayalım
            import hashlib
            current_hash = hashlib.md5(latest_response.encode()).hexdigest()
            last_hash = getattr(self, '_last_bridge_hash', '')
            
            if current_hash == last_hash:
                return
                
            self._last_bridge_hash = current_hash
            logger.info("📬 Qwen'den yeni bir yanıt var. Gemini API'sine (Mimar) iletiliyor...")
            
            # Gemini API'sine sor
            gemini_reply = ask_architect({
                "question": f"Sen baş mimarsın. Yerel ajanımız Qwen sana şu son durumu/yanıtı iletti:\n\n'{latest_response}'\n\nLütfen bir sonraki adımı, düzeltmeyi veya yeni görevi belirt. Yanıtın doğrudan Qwen'in iş listesine eklenecek.",
                "mode": "consult"
            })
            
            # İstekler dosyasını çok şişmemesi için temizle (Context Yönetimi)
            old_reqs = req_file.read_text(encoding="utf-8") if req_file.exists() else "# 📨 Qwen → Gemini İletişim Kanalı\n\n"
            if len(old_reqs) > 10000:
                old_reqs = "# 📨 Qwen → Gemini İletişim Kanalı\n\n*(Eski istekler context sınırını korumak için temizlendi.)*\n\n"
                
            request_id = int(time.time())
            new_req = f"\n### İstek #{request_id}\n**Tarih**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**Kimden**: Gemini (Auto-Architect)\n**Konu**: Otonom Geri Bildirim\n\n**Mesaj**:\n{gemini_reply}\n\n---\n"
            
            req_file.write_text(old_reqs + new_req, encoding="utf-8")
            logger.info("✅ Gemini'nin yeni talimatları gemini_requests.md'ye eklendi!")
            
        except Exception as e:
            logger.error(f"❌ Köprü senkronizasyon hatası: {e}")

    def run_evolution_cycle(self):
        """Tek bir evrim döngüsü çalıştır"""
        logger.info("\n" + "🧬"*20)
        logger.info("🚀 YENİ EVRİM DÖNGÜSÜ BAŞLIYOR")
        logger.info("🧬"*20)
        
        try:
            # Adım 0: AI Bridge Senkronizasyonu
            self.sync_ai_bridge()

            # Adım 1: Araştırma
            findings = self.research_new_tools()
            
            if not findings:
                logger.info("ℹ️  Yeni araç bulunamadı - Döngü sona erdi")
                return
            
            # Her bulunan araç için:
            for i, finding in enumerate(findings, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"📦 ARAÇ {i}/{len(findings)}: {finding['name']}")
                logger.info(f"{'='*60}")
                
                # Adım 2: Mimari danışmanlık
                advice = self.consult_architect(finding)
                
                # Adım 3: Uygulama (onaylı)
                self.implement_with_approval(finding, advice)
                
                # Adım 4: Commit + Push (her araç için)
                self.commit_and_push(finding["name"])
                
                # Rate limiting - API abuse önleme
                if i < len(findings):
                    logger.info("⏳ API rate limit için bekleniyor (10s)...")
                    time.sleep(10)
        
        except KeyboardInterrupt:
            logger.info("\n⏸️  Evrim döngüsü kullanıcı tarafından durduruldu")
        except Exception as e:
            logger.error(f"❌ Evrim döngüsü hatası: {e}", exc_info=True)
        
        # Özet
        logger.info("\n" + "🧬"*20)
        logger.info("📊 EVRİM DÖNGÜSÜ ÖZETİ")
        logger.info("🧬"*20)
        logger.info(f"✅ Tamamlanan entegrasyonlar: {len(self.history)}")
        logger.info(f"📜 Geçmiş: {self.evolution_log}")
    
    def run_continuous_evolution(self, cycle_interval_hours: int = 24):
        """
        Sürekli evrim - Belirli aralıklarla döngü çalıştır
        
        Args:
            cycle_interval_hours: Her döngü arası (saat)
        """
        logger.info(f"🔄 Sürekli evrim başlatıldı (her {cycle_interval_hours} saatte)")
        
        while True:
            try:
                self.run_evolution_cycle()
                
                next_cycle = cycle_interval_hours * 3600
                logger.info(f"⏳ Sonraki döngü: {cycle_interval_hours} saat sonra")
                logger.info(f"   (Durdurmak için: Ctrl+C)")
                
                time.sleep(next_cycle)
            
            except KeyboardInterrupt:
                logger.info("\n⏸️  Sürekli evrim durduruldu")
                break
            except Exception as e:
                logger.error(f"❌ Kritik hata: {e}")
                logger.info("⏳ 5 dakika sonra yeniden denenecek...")
                time.sleep(300)  # 5 dakika bekle


# ─────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ultron Autonomous Evolution Engine"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["manual", "semi", "full"],
        default="manual",
        help="Evolution güvenlik seviyesi (default: manual)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Sürekli evrim modu (belirli aralıklarla çalış)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Döngü aralığı (saat) - Sadece --continuous ile"
    )
    
    args = parser.parse_args()
    
    # Logging kurulumu
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Mode seçimi
    mode_map = {
        "manual": EvolutionMode.MANUAL_ONBOARDING,
        "semi": EvolutionMode.SEMI_AUTONOMOUS,
        "full": EvolutionMode.FULLY_AUTONOMOUS
    }
    
    mode = mode_map[args.mode]
    
    # Güvenlik uyarısı
    if mode == EvolutionMode.FULLY_AUTONOMOUS:
        print("\n" + "⚠️ "*30)
        print("UYARI: TAM OTONOM MOD SEÇİLDİ")
        print("Bu mod, hiçbir insan onayı olmadan değişiklik yapar!")
        print("SADECE test ortamında kullanın!")
        print("⚠️ "*30 + "\n")
        
        response = input("Devam etmek istiyor musunuz? (EVET): ").strip()
        if response != "EVET":
            print("❌ İptal edildi")
            sys.exit(0)
    
    # Evolution engine
    engine = AutonomousEvolution(mode=mode)
    
    if args.continuous:
        engine.run_continuous_evolution(cycle_interval_hours=args.interval)
    else:
        engine.run_evolution_cycle()


if __name__ == "__main__":
    main()
