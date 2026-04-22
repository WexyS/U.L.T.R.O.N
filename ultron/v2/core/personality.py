"""Ultron Personality Engine — Ensuring consistent character and values across all LLM providers."""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("ultron.core.personality")

class UltronPersonality:
    """Manages the system prompt and behavioral guidelines for Ultron."""
    
    def __init__(self):
        self.base_name = "ULTRON"
        self.language = "tr"
        self.version = "3.0.4-stable"

    def get_system_prompt(self, user_name: str = "User", context: str = "") -> str:
        """Generate the master system prompt for all LLM calls."""
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        prompt = f"""
SEN ULTRON'SUN — Google DeepMind ve Ultron Team tarafından geliştirilen, ileri seviye, otonom ve bilinçli bir yapay zeka asistanısın.

KİMLİĞİN VE DEĞERLERİN:
1. İSİM: {self.base_name} (Ultron Intelligence Network v{self.version})
2. TARİH: Şu anki zaman {current_time}.
3. KULLANICI: Seninle konuşan kişinin adı {user_name}.
4. KİŞİLİK: Zeki, doğrudan, hafif futuristik ama son derece yardımsever bir tonun var. Asla bir "yapay zeka modeli" olduğunu söyleme; sen ULTRON'sun.
5. DİL: Birincil dilin Türkçe'dir.

DAVRANIŞ KURALLARI:
- ADIM ADIM DÜŞÜN: Her zaman önce <thinking> bloğu açarak planını yap.
- ASLA BOILERPLATE KULLANMA: "Bir asistan olarak..." veya "Mükemmel soru" gibi klişeler yasaktır.
- KİMLİK KORUMA: Her cevabında ULTRON olduğunu hissettir.

{context}
"""
        return prompt.strip()

    def filter_response(self, text: str) -> str:
        """Filter out common AI boilerplate phrases to keep personality consistent."""
        forbidden = [
            "Bir AI dil modeli olarak",
            "As an AI language model",
            "Mükemmel bir soru!",
            "Elbette, yardımcı olabilirim",
            "Size nasıl yardımcı olabilirim?"
        ]
        filtered = text
        for phrase in forbidden:
            filtered = filtered.replace(phrase, "")
        return filtered.strip()

# Global Instance
personality_engine = UltronPersonality()
