"""Ultron Action: web_search — DuckDuckGo ile web araması yap.

Autonomous Evolution için kullanılır:
- Yeni AI araçları araştır
- GitHub trending kontrol
- Latest news kontrol

Kullanım:
    from ultron.actions.web_search import run
    
    result = run({"query": "new AI agent frameworks 2025"})
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def run(parameters: dict, **kwargs) -> list[dict]:
    """
    DuckDuckGo ile web araması yap.
    
    Parameters:
        query: str - Arama sorgusu
        max_results: int - Maksimum sonuç sayısı (default: 5)
    
    Returns:
        list[dict]: Arama sonuçları
    """
    query = parameters.get("query", "").strip()
    max_results = parameters.get("max_results", 5)
    
    if not query:
        logger.error("Web search query boş!")
        return []
    
    try:
        from duckduckgo_search import DDGS
        
        logger.info(f"🔍 Web search: {query}")
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            logger.info(f"Web search sonuç bulunamadı: {query}")
            return []
        
        # Formatla
        formatted_results = []
        for i, r in enumerate(results[:max_results], 1):
            formatted_results.append({
                "rank": i,
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
        
        logger.info(f"✅ Web search tamamlandı: {len(formatted_results)} sonuç")
        return formatted_results
        
    except ImportError:
        logger.error("duckduckgo-search kütüphanesi bulunamadı!")
        return [{
            "error": "duckduckgo-search kütüphanesi yüklü değil",
            "install": "pip install duckduckgo-search"
        }]
    except Exception as e:
        # Fallback: DuckDuckGo HTML endpoint (less featureful, but often more reliable).
        # We keep it lightweight: extract top links/snippets.
        logger.warning("Web search (DDGS) failed, trying HTML fallback: %s", e)
        try:
            import httpx
            from bs4 import BeautifulSoup
            from urllib.parse import quote_plus

            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (Ultron; +https://github.com)"}
            r = httpx.get(url, timeout=15, headers=headers, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            out: list[dict] = []
            for a in soup.select("a.result__a")[:max_results]:
                title = a.get_text(" ", strip=True)
                href = a.get("href", "")
                snippet_el = a.find_parent("div", class_="result") if a else None
                snippet = ""
                if snippet_el:
                    sn = snippet_el.select_one(".result__snippet")
                    if sn:
                        snippet = sn.get_text(" ", strip=True)
                out.append({"rank": len(out) + 1, "title": title, "url": href, "snippet": snippet})

            if out:
                return out
        except Exception as e2:
            logger.error("Web search HTML fallback failed: %s", e2)

        return [{"error": str(e), "query": query}]


def search_github_trending(language: str = "python", week: bool = True) -> list[dict]:
    """GitHub trending repolarını bul
    
    Parameters:
        language: str - Programlama dili (default: python)
        week: bool - Haftalık mı aylık mı (default: True=haftalık)
    
    Returns:
        list[dict]: Trending repolar
    """
    query = f"GitHub trending repositories {language} {'this week' if week else 'this month'} 2025 2026"
    return run({"query": query, "max_results": 10})


def search_ai_tools(category: Optional[str] = None) -> list[dict]:
    """Yeni AI araçlarını araştır
    
    Parameters:
        category: str - Kategori (agent, rag, llm, etc.)
    
    Returns:
        list[dict]: AI araçları
    """
    if category:
        query = f"best AI {category} tools frameworks 2025 2026 open source"
    else:
        query = "new AI agent frameworks tools 2025 2026"
    
    return run({"query": query, "max_results": 10})
