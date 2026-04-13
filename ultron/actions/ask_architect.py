"""
Ultron Action: ask_architect — Yerel LLM'in (Qwen) içinden çıkamadığı
zor mimari kararlarda veya inatçı bug'larda bulut tabanlı kıdemli bir modele (Gemini) danışmasını sağlar.

İKİ YÖNLÜ İLETİŞİM DESTEKLİ:
- Qwen → Gemini: Mimari danışmanlık
- Gemini → Qwen: Otomatik kod önerisi ve uygulama
"""

import os
import json
import logging
import requests
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# OpenRouter API endpoint
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Gemini model seçeneği (ücretsiz veya ücretli)
GEMINI_MODEL = "google/gemini-2.5-flash"  # veya "google/gemini-2.0-flash-exp:free"


def run(parameters: dict, **kwargs) -> str:
    """
    Buluttaki Mimar'a (Gemini) soru sorar ve yanıt alır.
    
    Parameters:
        question: str - Sorulacak soru
        code_context: str - İlgili kod/hata bağlamı (opsiyonel)
        mode: str - "consult" (danışmanlık) veya "implement" (uygulama) [default: consult]
        file_path: str - Düzenlenecek dosya yolu (implement modunda)
    
    Returns:
        str - Gemini'nin yanıtı
    """
    question = parameters.get("question", "").strip()
    code_context = parameters.get("code_context", "").strip()
    mode = parameters.get("mode", "consult").strip()
    file_path = parameters.get("file_path", "").strip()

    if not question:
        return "❌ Hata: Mimara sorulacak soru (question) belirtilmedi."

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "❌ Hata: OPENROUTER_API_KEY çevre değişkeni bulunamadı. Lütfen .env dosyasına ekleyin."

    # Mod'a göre sistem promptunu ayarla
    if mode == "implement":
        system_prompt = (
            "Sen kıdemli bir yazılım mühendisisin (Gemini). "
            "Ultron (Qwen) adlı yerel bir AI asistanı sana danışıyor. "
            "SADECE düzeltilmiş kodu ver. Kısa açıklama + kod bloğu formatında yanıt ver. "
            "Dosya yolu belirtilmişse, o dosyayı nasıl düzenleyeceğini adım adım göster."
        )
    else:  # consult
        system_prompt = (
            "Sen kıdemli bir yazılım mimarı ve danışmanısın (Gemini). "
            "Ultron (Qwen) adlı yerel bir AI asistanı sana takıldığı yerlerde danışıyor. "
            "Lafı uzatmadan doğrudan çözümü, mimari kararı veya düzeltilmiş kodu ver. "
            "Önce kısa analiz, sonra somut öneri formatında yanıt ver."
        )

    prompt = question
    if code_context:
        prompt += f"\n\n📂 İlgili Kod/Bağlam/Hata Logu:\n```\n{code_context}\n```"
    
    if mode == "implement" and file_path:
        prompt += f"\n\n📍 Hedef Dosya: `{file_path}`"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    try:
        logger.info(f"🧠 Gemini'ye danışılıyor (mode={mode})...")
        
        response = requests.post(
            url=OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Ultron-Assistant",
                "X-Title": "Ultron Architect Consultation"
            },
            json={
                "model": GEMINI_MODEL,
                "messages": messages,
                "temperature": 0.3 if mode == "consult" else 0.2,
                "max_tokens": 4000
            },
            timeout=90
        )
        response.raise_for_status()
        result = response.json()
        
        # Token kullanım bilgisi
        usage = result.get("usage", {})
        tokens_prompt = usage.get("prompt_tokens", "?")
        tokens_completion = usage.get("completion_tokens", "?")
        
        answer = result["choices"][0]["message"]["content"]
        
        logger.info(f"✅ Gemini yanıtı alındı ({tokens_prompt}→{tokens_completion} tokens)")
        
        # Yanıtı formatla
        response_text = f"🏗️ [Kıdemli Mimarın Yanıtı] (mode={mode})\n\n{answer}"
        
        # Token kullanımını ekle
        response_text += f"\n\n📊 Token Kullanımı: {tokens_prompt} (input) → {tokens_completion} (output)"
        
        return response_text
        
    except requests.exceptions.Timeout:
        logger.error("⏱️ Gemini API yanıt vermedi (timeout)")
        return "⏱️ Hata: Gemini API'si yanıt vermedi. Bağlantıyı kontrol edin."
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP Hatası: {e}")
        return f"❌ HTTP Hatası: {e.response.status_code} - {e.response.text[:200]}"
        
    except Exception as e:
        logger.error(f"❌ Mimara danışılırken hata: {e}")
        return f"❌ Mimara danışılırken beklenmeyen hata: {type(e).__name__}: {e}"


def ask_and_apply(question: str, file_path: str, code_context: Optional[str] = None) -> str:
    """
    Gemini'ye danış ve yanıtını otomatik olarak dosyaya uygula.
    
    Bu fonksiyon, Gemini'nin önerdiği kod değişikliklerini otomatik olarak
    hedef dosyaya uygular. Dikkatli kullanın - dosyayı değiştirir!
    
    Parameters:
        question: str - Soru
        file_path: str - Düzenlenecek dosya
        code_context: str - Mevcut kod (opsiyonel, dosyadan okunur)
    
    Returns:
        str - İşlem sonucu
    """
    # Dosyayı oku
    target_path = Path(file_path)
    current_code = code_context or ""
    if not target_path.exists():
        logger.info(f"✨ Yeni dosya oluşturulacak (Tam Otonom): {file_path}")
    else:
        current_code = code_context or target_path.read_text(encoding="utf-8")
    
    # Gemini'ye danış
    result = run({
        "question": question,
        "code_context": current_code,
        "mode": "implement",
        "file_path": file_path
    })
    
    # Yanıt başarısız olduysa, uygula
    if "❌ Hata" in result or "⏱️ Hata" in result:
        return result
    
    # Gemini'nin yanıtından kod bloğunu çıkar
    import re
    
    # ```python veya ``` bloklarını bul
    code_blocks = re.findall(r'```(?:python)?\n(.*?)```', result, re.DOTALL)
    
    if not code_blocks:
        return f"⚠️ Gemini yanıtı kod bloğu içermiyor. Yanıt:\n{result}"
    
    # İlk kod bloğunu al (genellikle ana öneri)
    suggested_code = code_blocks[0].strip()
    
    # Yedekle
    backup_path = None
    if target_path.exists():
        backup_path = target_path.with_suffix(f"{target_path.suffix}.backup")
        import shutil
        shutil.copy2(target_path, backup_path)
        logger.info(f"💾 Yedek oluşturuldu: {backup_path}")
    
    # Dosyaya yaz
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(suggested_code, encoding="utf-8")
    logger.info(f"✅ Dosya güncellendi: {file_path}")
    
    response_msg = f"✅ Kod uygulandı!\n\n📂 Dosya: {file_path}\n"
    if backup_path:
        response_msg += f"💾 Yedek: {backup_path}\n"
    response_msg += f"\n📝 Gemini'nin Tam Yanıtı:\n{result}"
    return response_msg