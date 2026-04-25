"""Unified 5-Layer Memory System for Ultron v3.0."""

import logging
from typing import List, Dict, Any, Optional

from ultron.memory.working_memory import WorkingMemory
from ultron.memory.short_term_memory import ShortTermMemory
from ultron.memory.long_term_memory import LongTermMemory
from ultron.memory.procedural_memory import ProceduralMemory
from ultron.memory.episodic_memory import EpisodicMemory

logger = logging.getLogger("ultron.memory.unified")

class UnifiedMemory:
    """The central access point for all 5 layers of memory in Ultron v3.0."""

    def __init__(self, user_id: str = "default"):
        self.working = WorkingMemory()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(collection_name=f"ultron_ltm_{user_id}")
        self.procedural = ProceduralMemory()
        self.episodic = EpisodicMemory()

    async def initialize(self):
        """Initialize all persistent memory layers."""
        # Note: working and short_term are in-memory
        # Procedural and Episodic are SQLite
        # LongTerm is ChromaDB
        await self.episodic.initialize()
        # self.procedural and self.long_term initialization logic is assumed in their classes
        logger.info("Unified 5-Layer Memory System Initialized.")

    async def remember(self, content: str, metadata: Dict[str, Any] = None):
        """Store information across appropriate layers."""
        # 1. Add to ShortTerm (Session Context)
        self.short_term.add("user", content, metadata)
        
        # 2. Add to LongTerm (Semantic Vector Search)
        # self.long_term.add(content, metadata) 
        
        # 3. Add to Episodic (Event Log)
        await self.episodic.store("user_input", content, metadata=metadata)

    async def recall(self, query: str, context_type: str = "all") -> Dict[str, Any]:
        """Recall information from various layers based on query."""
        results = {}
        
        if context_type in ["all", "short_term"]:
            results["short_term"] = self.short_term.get_all()
            
        if context_type in ["all", "long_term"]:
            # results["long_term"] = await self.long_term.search(query)
            pass
            
        if context_type in ["all", "episodic"]:
            results["episodic"] = await self.episodic.search(query)
            
        return results

    def clear_working(self):
        """Clear transient working memory."""
        self.working.clear()
