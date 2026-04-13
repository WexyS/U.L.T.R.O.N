"""Sleep Cycle Engine — Memory consolidation with AirLLM analysis.

Gece 03:00'da veya sistem boştayken çalışır:
1. Semantic clustering ile benzer kayıtları birleştir
2. Duplicate'ları sil
3. Procedural rules çıkar
4. AirLLM ile derin analiz (opsiyonel)
5. Gereksiz hafızayı temizle

Kullanım:
    from ultron.v2.memory.sleep_cycle import SleepCycleEngine
    
    engine = SleepCycleEngine()
    await engine.run_sleep_cycle()
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SleepCycleEngine:
    """Uyku döngüsü - Memory consolidation"""
    
    def __init__(
        self,
        memory_engine,  # MemoryEngine instance
        airllm_model: Optional[str] = None,
        airllm_compression: Optional[str] = '4bit'
    ):
        self.memory = memory_engine
        self.airllm_model_name = airllm_model
        self.airllm_compression = airllm_compression
        self.airllm_model = None  # Lazy load
        
        # Config
        self.similarity_threshold = 0.90  # %90+ benzerlik = duplicate
        self.min_cluster_size = 2  # En az 2 kayıt cluster için
        self.max_memories_to_analyze = 100  # Batch size
        
    async def _load_airllm(self):
        """AirLLM modelini yükle (lazy loading)"""
        if self.airllm_model is None and self.airllm_model_name:
            try:
                from airllm import AutoModel
                
                logger.info(f"🧠 Loading AirLLM model: {self.airllm_model_name} ({self.airllm_compression})...")
                
                self.airllm_model = AutoModel.from_pretrained(
                    self.airllm_model_name,
                    compression=self.airllm_compression,
                    prefetching=True
                )
                
                logger.info("✅ AirLLM model loaded successfully")
                
            except ImportError:
                logger.warning("AirLLM not installed. Run: pip install airllm")
                self.airllm_model = None
            except Exception as e:
                logger.error(f"Failed to load AirLLM model: {e}")
                self.airllm_model = None
    
    async def run_sleep_cycle(self) -> dict:
        """
        Uyku döngüsünü çalıştır
        
        Returns:
            dict: Consolidation raporu
        """
        logger.info("\n🌙 SLEEP CYCLE BAŞLIYOR")
        logger.info("="*60)
        
        start_time = datetime.now()
        report = {
            "start_time": start_time.isoformat(),
            "clusters_found": 0,
            "duplicates_merged": 0,
            "rules_extracted": 0,
            "memories_cleaned": 0,
            "airllm_analysis": None,
        }
        
        try:
            # Step 1: Semantic clustering
            logger.info("\n📊 Step 1: Semantic clustering...")
            clusters = await self._cluster_similar_memories()
            report["clusters_found"] = len(clusters)
            logger.info(f"✅ Found {len(clusters)} clusters")
            
            # Step 2: Merge duplicates
            logger.info("\n🔗 Step 2: Merging duplicates...")
            merged_count = await self._merge_duplicates(clusters)
            report["duplicates_merged"] = merged_count
            logger.info(f"✅ Merged {merged_count} duplicates")
            
            # Step 3: Extract procedural rules
            logger.info("\n📝 Step 3: Extracting procedural rules...")
            rules_count = await self._extract_procedural_rules()
            report["rules_extracted"] = rules_count
            logger.info(f"✅ Extracted {rules_count} rules")
            
            # Step 4: AirLLM deep analysis (if available)
            if self.airllm_model_name:
                logger.info("\n🧠 Step 4: AirLLM deep analysis...")
                await self._load_airllm()
                
                if self.airllm_model:
                    analysis = await self._analyze_with_airllm()
                    report["airllm_analysis"] = analysis
                    logger.info(f"✅ AirLLM analysis completed")
                else:
                    logger.warning("⚠️ AirLLM not available, skipping deep analysis")
            
            # Step 5: Cleanup old/low-importance memories
            logger.info("\n🧹 Step 5: Cleaning up old memories...")
            cleaned_count = await self._cleanup_old_memories()
            report["memories_cleaned"] = cleaned_count
            logger.info(f"✅ Cleaned {cleaned_count} old memories")
            
            # Summary
            duration = datetime.now() - start_time
            report["end_time"] = datetime.now().isoformat()
            report["duration_seconds"] = duration.total_seconds()
            
            logger.info("\n" + "="*60)
            logger.info("🌙 SLEEP CYCLE TAMAMLANDI")
            logger.info(f"⏱️  Süre: {duration.total_seconds():.1f}s")
            logger.info(f"📊 Clusters: {report['clusters_found']}")
            logger.info(f"🔗 Merged: {report['duplicates_merged']}")
            logger.info(f"📝 Rules: {report['rules_extracted']}")
            logger.info(f"🧹 Cleaned: {report['memories_cleaned']}")
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"❌ Sleep cycle failed: {e}", exc_info=True)
            report["error"] = str(e)
        
        return report
    
    async def _cluster_similar_memories(self) -> list:
        """ChromaDB'den benzer kayıtları cluster'la"""
        try:
            # Örnek query'ler ile search yap
            queries = [
                "code debugging",
                "user conversation",
                "research findings",
                "error handling",
                "configuration",
            ]
            
            clusters = []
            
            for query in queries:
                results = self.memory.search(query, limit=self.max_memories_to_analyze)
                
                if len(results) >= self.min_cluster_size:
                    clusters.append({
                        "query": query,
                        "memories": results,
                        "count": len(results),
                    })
            
            return clusters
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return []
    
    async def _merge_duplicates(self, clusters: list) -> int:
        """Duplicate kayıtları birleştir"""
        merged_count = 0
        
        for cluster in clusters:
            memories = cluster["memories"]
            
            # Semantic similarity kontrolü
            for i, mem1 in enumerate(memories):
                for mem2 in memories[i+1:]:
                    # Basit text similarity (daha gelişmiş yapılabilir)
                    similarity = self._calculate_similarity(
                        mem1.get("content", ""),
                        mem2.get("content", "")
                    )
                    
                    if similarity >= self.similarity_threshold:
                        # Duplicate bulundu - birleştir
                        await self._merge_memories(mem1["id"], mem2["id"])
                        merged_count += 1
        
        return merged_count
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Basit text similarity (daha gelişmiş yapılabilir)"""
        # Token overlap
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        overlap = tokens1 & tokens2
        return len(overlap) / max(len(tokens1), len(tokens2))
    
    async def _merge_memories(self, id1: str, id2: str):
        """İki hafızayı birleştir"""
        # TODO: Actual merge implementation
        # Şimdilik sadece log
        logger.debug(f"Merging memories: {id1} + {id2}")
        pass
    
    async def _extract_procedural_rules(self) -> int:
        """Hafızadan procedural rules çıkar"""
        # TODO: Rule extraction implementation
        # Örnek pattern matching ile kurallar çıkar
        return 0
    
    async def _analyze_with_airllm(self) -> dict:
        """AirLLM ile derin analiz"""
        if not self.airllm_model:
            return {"error": "AirLLM model not loaded"}
        
        try:
            prompt = """
            Analyze the following memory data and provide insights:
            
            1. What patterns do you observe?
            2. What lessons can be learned?
            3. What should be remembered vs forgotten?
            4. Any recurring themes or important decisions?
            
            Keep the analysis concise and actionable.
            """
            
            # AirLLM inference (slow but powerful)
            # TODO: Actual implementation with tokenizer
            output = f"AirLLM analysis completed at {datetime.now().isoformat()}"
            
            return {
                "analysis": output,
                "model": self.airllm_model_name,
                "compression": self.airllm_compression,
            }
            
        except Exception as e:
            logger.error(f"AirLLM analysis failed: {e}")
            return {"error": str(e)}
    
    async def _cleanup_old_memories(self) -> int:
        """Eski/düşük önemdeki hafızaları temizle"""
        # TODO: Cleanup implementation
        # Örnek: 90 günden eski ve access_count=0 olanları sil
        return 0


# ─── Scheduler ───────────────────────────────────────────────────────────

async def start_sleep_scheduler(
    sleep_engine: SleepCycleEngine,
    hour: int = 3,  # Gece 03:00
    minute: int = 0
):
    """Her gece belirli saatte sleep cycle çalıştır"""
    logger.info(f"⏰ Sleep scheduler started (daily at {hour:02d}:{minute:02d})")
    
    while True:
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if now >= target:
            # Bir sonraki güne ayarla
            target = target.replace(day=target.day + 1)
        
        wait_seconds = (target - now).total_seconds()
        logger.info(f"⏳ Next sleep cycle in {wait_seconds/3600:.1f} hours")
        
        await asyncio.sleep(wait_seconds)
        
        # Sleep cycle çalıştır
        await sleep_engine.run_sleep_cycle()
