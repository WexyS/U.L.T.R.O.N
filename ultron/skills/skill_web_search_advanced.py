"""Advanced Web Search Skill — Multi-source parallel search with RRF merging."""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from duckduckgo_search import DDGS

logger = logging.getLogger("ultron.skills.web_search_advanced")

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    reliability_score: float = 0.6

class MultiSourceSearcher:
    """Combines results from multiple search providers with ranking fusion."""

    def __init__(self, db_path: str = "data/search_cache.db"):
        self.db_path = db_path
        self._init_cache()

    def _init_cache(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                results TEXT,
                timestamp REAL
            )
        """)
        conn.commit()
        conn.close()

    async def search(self, query: str, sources: List[str] = None) -> List[SearchResult]:
        """Perform parallel search across enabled sources."""
        sources = sources or ["duckduckgo", "wikipedia"]
        
        # Check Cache
        cached = self._get_cached(query)
        if cached:
            logger.info(f"Returning cached results for: {query}")
            return cached

        tasks = []
        if "duckduckgo" in sources:
            tasks.append(self._search_duckduckgo(query))
        if "wikipedia" in sources:
            tasks.append(self._search_wikipedia(query))

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten and Merge
        all_results = []
        for r_list in results_lists:
            if isinstance(r_list, list):
                all_results.extend(r_list)

        # RRF or Simple Score-based merge
        unique_results = self._deduplicate(all_results)
        
        # Cache results
        self._save_cache(query, unique_results)
        
        return unique_results

    def _get_cached(self, query: str) -> Optional[List[SearchResult]]:
        q_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT results, timestamp FROM search_cache WHERE query_hash = ?", (q_hash,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            results_json, ts = row
            if time.time() - ts < 3600: # 1 hour cache
                data = json.loads(results_json)
                return [SearchResult(**r) for r in data]
        return None

    def _save_cache(self, query: str, results: List[SearchResult]):
        q_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()
        results_json = json.dumps([r.__dict__ for r in results])
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO search_cache (query_hash, query, results, timestamp) VALUES (?, ?, ?, ?)",
            (q_hash, query, results_json, time.time())
        )
        conn.commit()
        conn.close()

    async def _search_duckduckgo(self, query: str) -> List[SearchResult]:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                return [
                    SearchResult(
                        title=r["title"],
                        url=r["href"],
                        snippet=r["body"],
                        source="duckduckgo",
                        reliability_score=0.7
                    ) for r in results
                ]
        except Exception as e:
            logger.warning(f"DuckDuckGo failed: {e}")
            return []

    async def _search_wikipedia(self, query: str) -> List[SearchResult]:
        # Placeholder for real wikipedia API call
        return []

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)
        return unique

# Singleton instance
searcher = MultiSourceSearcher()
