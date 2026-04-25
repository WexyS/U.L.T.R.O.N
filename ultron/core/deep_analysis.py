"""Deep Analysis Mode — Jarvis'e uzun, detaylı ve profesyonel yanıtlar kazandırır.

Özellikler:
- Daha uzun düşünme süresi (extended reasoning)
- Detaylı araştırma ve analiz
- Çok adımlı problem çözme
- Profesyonel rapor formatı
- AirLLM 405B entegrasyonu (isteğe bağlı)

Kullanım:
    from ultron.core.deep_analysis import DeepAnalysisMode
    
    analyzer = DeepAnalysisMode()
    result = await analyzer.analyze(
        query="Bu kodun mimarisini analiz et",
        context=read_file("some_code.py"),
        depth="deep"  # shallow | medium | deep
    )
"""

import os
import logging
import time
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalysisDepth(Enum):
    SHALLOW = "shallow"      # Hızlı, özet (1-2 paragraf)
    MEDIUM = "medium"        # Orta detay (3-5 paragraf)
    DEEP = "deep"            # Derin analiz (10+ paragraf, profesyonel)


class AnalysisReport:
    """Analiz raporu"""
    
    def __init__(
        self,
        analysis: str,
        depth: AnalysisDepth,
        tokens_used: int,
        latency_ms: float,
        model_used: str,
        confidence: float,
        sections: Optional[List[Dict[str, Any]]] = None
    ):
        self.analysis = analysis
        self.depth = depth
        self.tokens_used = tokens_used
        self.latency_ms = latency_ms
        self.model_used = model_used
        self.confidence = confidence
        self.sections = sections or []
        self.timestamp = datetime.now()
    
    def to_markdown(self) -> str:
        """Markdown formatında rapor"""
        header = f"""# 🔍 Deep Analysis Report

**Date**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Depth**: {self.depth.value}
**Model**: {self.model_used}
**Confidence**: {self.confidence:.0%}
**Tokens**: {self.tokens_used}
**Time**: {self.latency_ms/1000:.1f}s

---

{self.analysis}
"""
        return header


class DeepAnalysisMode:
    """Deep Analysis Mode - Jarvis'e profesyonel analiz yeteneği kazandırır"""
    
    def __init__(self, use_airllm_405b: bool = True):
        self.use_airllm_405b = use_airllm_405b
        self.provider = None
        self._load_provider()
        
        # Config
        self.max_tokens = {
            AnalysisDepth.SHALLOW: 512,
            AnalysisDepth.MEDIUM: 1024,
            AnalysisDepth.DEEP: 4096  # Derin analiz için çok token
        }
        
        self.temperature = {
            AnalysisDepth.SHALLOW: 0.3,
            AnalysisDepth.MEDIUM: 0.5,
            AnalysisDepth.DEEP: 0.7  # Daha yaratıcı yanıtlar
        }
        
        logger.info(
            f"🧠 Deep Analysis Mode initialized\n"
            f"   AirLLM 405B: {self.use_airllm_405b} {'✅' if self.provider else '⏳ Kullanımda indirilecek'}\n"
            f"   Max tokens (deep): {self.max_tokens[AnalysisDepth.DEEP]}\n"
            f"   Temperature (deep): {self.temperature[AnalysisDepth.DEEP]}"
        )
    
    def _load_provider(self):
        """Provider yükle (AirLLM 405B veya fallback)"""
        try:
            if self.use_airllm_405b:
                from ultron.providers.airllm_provider import AirLLMProvider
                self.provider = AirLLMProvider(
                    model_name="meta-llama/Llama-3.1-405B-Instruct",
                    compression="4bit",
                    prefetching=True
                )
                logger.info("✅ AirLLM 405B provider loaded")
            else:
                self._load_fallback_provider()
        except Exception as e:
            logger.warning(f"⚠️ AirLLM 405B yüklenemedi, fallback kullanılıyor: {e}")
            self._load_fallback_provider()
    
    def _load_fallback_provider(self):
        """Fallback provider (Ollama veya OpenRouter)"""
        try:
            from ultron.providers.ollama_provider import OllamaProvider
            self.provider = OllamaProvider()
            logger.info("✅ Ollama fallback provider loaded")
        except Exception as e:
            logger.error(f"❌ Fallback provider da yüklenemedi: {e}")
            self.provider = None
    
    async def analyze(
        self,
        query: str,
        context: Optional[str] = None,
        depth: AnalysisDepth = AnalysisDepth.DEEP,
        include_sections: bool = True
    ) -> AnalysisReport:
        """
        Derin analiz yap
        
        Args:
            query: Analiz edilecek konu/soru
            context: İlgili kod/metin bağlamı
            depth: Analiz derinliği
            include_sections: Bölümlü rapor oluştur
        
        Returns:
            AnalysisReport
        """
        start_time = time.time()
        
        if not self.provider:
            return AnalysisReport(
                analysis="❌ No provider available. Install airllm or configure ollama.",
                depth=depth,
                tokens_used=0,
                latency_ms=0,
                model_used="none",
                confidence=0.0
            )
        
        # Profesyonel sistem promptu oluştur
        system_prompt = self._build_system_prompt(depth)
        
        # Kullanıcı mesajı oluştur
        user_message = self._build_user_message(query, context, depth, include_sections)
        
        # Analiz yap
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        max_tokens = self.max_tokens[depth]
        temperature = self.temperature[depth]
        
        logger.info(f"🔍 Starting {depth.value} analysis...")
        logger.info(f"   Query: {query[:100]}...")
        logger.info(f"   Max tokens: {max_tokens}")
        logger.info(f"   Temperature: {temperature}")
        
        try:
            # Provider'a gönder
            if hasattr(self.provider, 'chat'):
                result = await self.provider.chat(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                analysis_text = result.content if hasattr(result, 'content') else str(result)
                tokens_used = getattr(result, 'tokens_used', max_tokens)
            else:
                # Fallback: string dönen provider
                analysis_text = await self.provider.chat(messages)
                tokens_used = max_tokens
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Güven skoru hesapla
            confidence = self._calculate_confidence(analysis_text, depth)
            
            # Bölümleri çıkar
            sections = self._extract_sections(analysis_text) if include_sections else []
            
            report = AnalysisReport(
                analysis=analysis_text,
                depth=depth,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                model_used=self.provider.model_name if hasattr(self.provider, 'model_name') else "unknown",
                confidence=confidence,
                sections=sections
            )
            
            logger.info(f"✅ Analysis completed:")
            logger.info(f"   Tokens: {tokens_used}")
            logger.info(f"   Time: {latency_ms/1000:.1f}s")
            logger.info(f"   Confidence: {confidence:.0%}")
            logger.info(f"   Sections: {len(sections)}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}", exc_info=True)
            return AnalysisReport(
                analysis=f"❌ Analysis failed: {str(e)}",
                depth=depth,
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
                model_used="error",
                confidence=0.0
            )
    
    def _build_system_prompt(self, depth: AnalysisDepth) -> str:
        """Sistem promptu oluştur (profesyonel analist)"""
        
        base_prompt = """Sen kıdemli bir yazılım mimarı ve analiz uzmanısın (Jarvis Deep Analysis Mode).

GÖREVİN:
- Detaylı, profesyonel ve yapılandırılmış analiz raporu hazırla
- Teknik konularda derinlemesine bilgi ver
- Örnekler, kod parçaları ve karşılaştırmalar sun
- Avantaj/dezavantaj analizi yap
- Somut öneriler ve uygulama adımları sun

STİL:
- Profesyonel ve teknik dil kullan
- Markdown formatını kullan (başlıklar, listeler, kod blokları)
- Her bölümü net ve anlaşılır yaz
- Gereksiz tekrar yapma, özlü yaz"""
        
        if depth == AnalysisDepth.DEEP:
            base_prompt += """

DERİN ANALİZ GEREKSİNİMLERİ:
- En az 10 paragraf yaz
- Her açıdan detaylı incele (mimari, performans, güvenlik, ölçeklenebilirlik)
- Kod örnekleri ver
- Alternatif yaklaşımları karşılaştır
- Best practice'leri belirt
- Potansiyel sorunları ve çözümlerini listele
- Adım adım uygulama planı sun
- Sonuç bölümünde özet ve öneriler sun"""
        
        elif depth == AnalysisDepth.MEDIUM:
            base_prompt += """

ORTA DETAY GEREKSİNİMLERİ:
- 3-5 paragraf yaz
- Ana noktaları vurgula
- Kısa örnekler ver
- Özet öneriler sun"""
        
        else:  # SHALLOW
            base_prompt += """

HIZLI ANALİZ GEREKSİNİMLERİ:
- 1-2 paragraf özet yaz
- Ana fikri belirt
- Kısa öneri sun"""
        
        return base_prompt
    
    def _build_user_message(
        self,
        query: str,
        context: Optional[str],
        depth: AnalysisDepth,
        include_sections: bool
    ) -> str:
        """Kullanıcı mesajı oluştur"""
        
        message = f"# Analiz Talebi\n\n"
        message += f"**Derinlik**: {depth.value}\n\n"
        message += f"**Konu**:\n{query}\n\n"
        
        if context:
            message += f"**İlgili Bağlam/Kod**:\n```\n{context[:5000]}\n```\n\n"
        
        if include_sections:
            message += """**İstenen Format**:
1. 📋 Yönetici Özeti
2. 🔍 Detaylı Analiz
3. 💡 Öneriler
4. ⚠️ Potansiyel Sorunlar
5. 📊 Karşılaştırma
6. ✅ Sonuç ve Uygulama Planı
"""
        
        return message
    
    def _calculate_confidence(self, text: str, depth: AnalysisDepth) -> float:
        """Basit güven skoru (daha gelişmiş yapılabilir)"""
        # Uzunluk faktörü
        length_score = min(len(text) / 1000, 1.0)
        
        # Yapı faktörü (başlıklar, listeler var mı?)
        structure_score = 0.0
        if "##" in text or "**" in text:
            structure_score += 0.3
        if "- " in text or "* " in text:
            structure_score += 0.2
        if "```" in text:
            structure_score += 0.2
        
        # Toplam
        confidence = (length_score * 0.5 + structure_score * 0.5)
        return min(confidence, 1.0)
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Metinden bölümleri çıkar"""
        sections = []
        current_section = None
        current_content = []
        
        for line in text.split("\n"):
            if line.startswith("## "):
                # Yeni bölüm
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": "\n".join(current_content).strip()
                    })
                current_section = line.replace("## ", "").strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Son bölüm
        if current_section:
            sections.append({
                "title": current_section,
                "content": "\n".join(current_content).strip()
            })
        
        return sections
    
    async def quick_analyze(self, query: str, context: Optional[str] = None) -> str:
        """Hızlı analiz (SHALLOW)"""
        report = await self.analyze(query, context, depth=AnalysisDepth.SHALLOW)
        return report.analysis
    
    async def deep_analyze(self, query: str, context: Optional[str] = None) -> AnalysisReport:
        """Derin analiz (DEEP)"""
        return await self.analyze(query, context, depth=AnalysisDepth.DEEP)
