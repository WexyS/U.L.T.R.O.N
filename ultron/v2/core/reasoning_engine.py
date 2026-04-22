"""Ultron Reasoning Engine — Implementing Chain-of-Thought and Self-Correction logic."""

import logging
import re
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from ultron.v2.core.personality import personality_engine

logger = logging.getLogger("ultron.core.reasoning")

@dataclass
class ReasoningResult:
    thinking: str
    answer: str
    was_corrected: bool = False
    revision_count: int = 0

class ReasoningEngine:
    """Orchestrates complex thinking and self-correction flows."""
    
    def __init__(self, router=None, **kwargs):
        # Handle both old and new initialization styles
        self.router = router or kwargs.get("llm_router")
        self.memory = kwargs.get("memory") # For backward compatibility

    async def think_and_answer(self, user_msg: str, history: List[Dict] = None, max_revisions: int = 1) -> ReasoningResult:
        """Process a request with Chain-of-Thought and optional self-correction."""
        
        history = history or []
        system_prompt = personality_engine.get_system_prompt()
        
        # 1. Check if the query is complex enough for CoT
        if not self._is_complex(user_msg):
            # Fast path
            messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_msg}]
            resp = await self.router.chat(messages)
            return ReasoningResult(thinking="", answer=resp.content)

        # 2. Reasoning Loop (CoT)
        thinking_prompt = f"""
Sana gelen mesajı analiz et ve <thinking> tagleri içinde adım adım düşün. 
Düşünme aşamasından sonra net bir cevap ver.

Soru: {user_msg}
"""
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": thinking_prompt}]
        
        resp = await self.router.chat(messages)
        content = resp.content
        
        # 3. Parse Thinking
        thinking, answer = self._parse_content(content)
        
        # 4. Self-Correction (Reflection)
        was_corrected = False
        revisions = 0
        
        if max_revisions > 0:
            reflection_prompt = f"""
Aşağıdaki cevabını kendi içinde eleştir. 
Hatalar, eksikler veya ULTRON kişiliğine uymayan yerler var mı?
Yanıtını JSON formatında ver:
{{
    "has_error": bool,
    "critique": "eleştiri mesajı",
    "improved_answer": "düzeltilmiş cevap"
}}

Cevap: {answer}
"""
            try:
                # We use a cheaper/faster model for reflection if possible
                reflect_resp = await self.router.chat([{"role": "user", "content": reflection_prompt}])
                
                # Extract JSON
                match = re.search(r"\{[\s\S]*\}", reflect_resp.content)
                if match:
                    feedback = json.loads(match.group())
                    if feedback.get("has_error"):
                        answer = feedback.get("improved_answer", answer)
                        was_corrected = True
                        revisions = 1
            except Exception as e:
                logger.warning(f"Self-correction failed: {e}")

        return ReasoningResult(
            thinking=thinking,
            answer=answer,
            was_corrected=was_corrected,
            revision_count=revisions
        )

    def _is_complex(self, text: str) -> bool:
        """Determine if a query warrants heavy reasoning."""
        # Simple heuristic: length, question marks, keywords
        complexity_keywords = ["neden", "nasıl", "analiz", "yaz", "çöz", "plan", "debug", "fark", "karşılaştır"]
        text_lower = text.lower()
        
        if len(text) > 100: return True
        if any(k in text_lower for k in complexity_keywords): return True
        return False

    def _parse_content(self, content: str) -> (str, str):
        """Split content into thinking and final answer."""
        thinking_match = re.search(r"<thinking>([\s\S]*?)</thinking>", content)
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        
        # Remove thinking block from final answer
        answer = re.sub(r"<thinking>[\s\S]*?</thinking>", "", content).strip()
        return thinking, answer
