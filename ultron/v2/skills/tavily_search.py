"""Tavily Deep Search Skill — AI-optimized web search."""
import os
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

async def search_tavily(query: str, search_depth: str = "advanced", max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Performs a deep search using Tavily API.
    
    Args:
        query: The search query.
        search_depth: "basic" or "advanced".
        max_results: Number of results to return.
        
    Returns:
        List of dicts containing 'title', 'href' (url), and 'body' (content).
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.debug("Tavily API key not found in environment.")
        return []

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "include_answer": True,
        "include_raw_content": False,
        "max_results": max_results
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for res in data.get("results", []):
                results.append({
                    "title": res.get("title", ""),
                    "href": res.get("url", ""),
                    "body": res.get("content", ""),
                    "score": res.get("score", 0)
                })
            
            # If Tavily provided a direct answer, inject it as a special result
            if data.get("answer"):
                results.insert(0, {
                    "title": "Tavily AI Summary",
                    "href": "#",
                    "body": data["answer"],
                    "score": 1.0
                })
                
            return results
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []
