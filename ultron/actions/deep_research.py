"""
Ultron Action: deep_research — Kapsamlı internet araştırması yapar.
Verilen konuyu sadece aramakla kalmaz, bağlantıların içine girerek
içeriklerini okur, sentezler ve detaylı bir markdown raporu oluşturur.
"""

import logging
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def run(parameters: dict, **kwargs) -> str:
    """Derinlemesine web araştırması yapar."""
    topic = parameters.get("topic", "").strip()
    if not topic:
        return "❌ Hata: Araştırılacak konu (topic) belirtilmedi."

    logger.info(f"🔍 '{topic}' için derin araştırma başlatılıyor...")
    
    try:
        with DDGS() as ddgs:
            # Daha kapsamlı sonuç için limit 3
            search_results = list(ddgs.text(topic, max_results=3))
            
        if not search_results:
            return f"⚠️ '{topic}' hakkında bilgi bulunamadı."
            
        report = f"📊 **'{topic}' Derin Araştırma Raporu**\n\n"
        
        for i, res in enumerate(search_results, 1):
            title = res.get('title', 'Başlıksız')
            href = res.get('href', '')
            snippet = res.get('body', '')
            
            report += f"### {i}. {title}\n🔗 {href}\n📝 **Özet:** {snippet}\n\n"
            
            # Bağlantının içine girip sayfa içeriğini kazı
            try:
                resp = requests.get(href, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    paragraphs = soup.find_all('p')
                    text = " ".join(p.text.strip() for p in paragraphs if len(p.text.strip()) > 40)
                    if text:
                        report += f"📄 **Sayfa İçeriğinden Sentez:** {text[:400]}...\n\n"
            except Exception as e:
                logger.debug(f"Sayfa okunamadı ({href}): {e}")
                
        return report
        
    except Exception as e:
        logger.error(f"Derin araştırma hatası: {e}")
        return f"❌ Araştırma sırasında hata oluştu: {e}"
