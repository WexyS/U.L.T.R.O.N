"""Multi-Agent Debate Engine for Ultron v2."""

import logging
from typing import List, Dict, Any
from ultron.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class DebateEngine:
    """Manages a debate between multiple LLM personas to arrive at a superior conclusion."""
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def run_debate(self, topic: str, rounds: int = 2, mode: str = "standard", lesson_context: str = "") -> Dict[str, Any]:
        """Runs a debate between an Advocate, a Critic, and a Judge.
        Modes: standard, security_audit
        """
        lessons = f"\n\nGeçmişteki Deneyimlerden Öğrenilen Dersler:\n{lesson_context}" if lesson_context else ""
        
        if mode == "security_audit":
            advocate_prompt = f"Sen 'Güvenlik Savunucusu'sun. Önerilen kodun veya özelliğin neden güvenli olduğunu ve en iyi uygulamalara uyduğunu açıkla. SADECE TÜRKÇE YANIT VER.{lessons}"
            critic_prompt = f"Sen 'Siber Güvenlik Denetçisi'sin (Pen-tester). Önerideki güvenlik açıklarını, enjeksiyon risklerini ve zafiyetleri bul. Acımasız ama yapıcı ol. SADECE TÜRKÇE YANIT VER.{lessons}"
            judge_prompt = "Sen 'Güvenlik Yöneticisi'sin (CISO). Tartışmayı değerlendir ve bu değişikliğin canlıya alınması için %100 güvenli olup olmadığına karar ver. SADECE NİHAİ KARARI TÜRKÇE YAZ."
        else:
            advocate_prompt = f"Sen 'Savunucu' (Advocate) adlı yapay zekasın. Kullanıcının sorusuna detaylı, inandırıcı ve çözüm odaklı bir yanıt ver. " \
                              f"Eğer eleştiri gelirse kendini savun veya puanlarını geliştir. SADECE TÜRKÇE YANIT VER.{lessons}"
            critic_prompt = f"Sen 'Eleştirmen' (Critic) adlı yapay zekasın. Savunucu'nun argümanını incele. Olası hataları, halüsinasyonları, " \
                            f"güvenlik açıklarını veya eksikleri bul. Yapıcı bir dille eleştir. SADECE TÜRKÇE YANIT VER.{lessons}"
            judge_prompt = "Sen 'Yargıç' (Judge) adlı yapay zekasın. Konuyu, Savunucu'nun ve Eleştirmen'in argümanlarını değerlendir. " \
                           "En doğru, güvenli ve tutarlı nihai kararı sentezleyip ortaya çıkar. SADECE NİHAİ KARARI VE SEBEBİNİ TÜRKÇE OLARAK YAZ."

        # Keep a general transcript
        transcript = []
        
        # Initial proposal
        adv_msg = [{"role": "system", "content": advocate_prompt}, {"role": "user", "content": f"Topic: {topic}"}]
        proposal_resp = await self.llm_router.chat(adv_msg, max_tokens=1024)
        current_proposal = proposal_resp.content
        transcript.append({"role": "advocate", "content": current_proposal})
        
        for r in range(rounds):
            logger.info(f"Debate Engine - Round {r+1}/{rounds}")
            # Critic phase
            crit_msg = [
                {"role": "system", "content": critic_prompt},
                {"role": "user", "content": f"Topic: {topic}\n\nAdvocate's Proposal:\n{current_proposal}"}
            ]
            crit_resp = await self.llm_router.chat(crit_msg, max_tokens=1024)
            criticism = crit_resp.content
            transcript.append({"role": "critic", "content": criticism})
            
            # Advocate rebuttal/update phase (skip if Last Round to go to Judge directly)
            if r < rounds - 1:
                adv_msg = [
                    {"role": "system", "content": advocate_prompt},
                    {"role": "user", "content": f"Topic: {topic}\n\nYour previous proposal:\n{current_proposal}\n\nCritic's feedback:\n{criticism}\n\nProvide an improved proposal addressing the feedback."}
                ]
                proposal_resp = await self.llm_router.chat(adv_msg, max_tokens=1024)
                current_proposal = proposal_resp.content
                transcript.append({"role": "advocate", "content": current_proposal})
                
        # Judge phase
        judge_msg = [
            {"role": "system", "content": judge_prompt},
            {"role": "user", "content": f"Topic: {topic}\n\nTranscript of Debate:\n" + "\n\n".join([f"[{item['role'].upper()}]: {item['content']}" for item in transcript])}
        ]
        judge_resp = await self.llm_router.chat(judge_msg, max_tokens=2048)
        final_answer = judge_resp.content
        transcript.append({"role": "judge", "content": final_answer})
        
        return {
            "topic": topic,
            "rounds": rounds,
            "transcript": transcript,
            "final_answer": final_answer
        }
