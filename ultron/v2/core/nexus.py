import logging
import httpx
import re
import json
from typing import List, Dict, Any, Optional
from ultron.v2.mcp.schemas import MCPServerDefinition

logger = logging.getLogger(__name__)

class UltronNexus:
    """Discovery and Installation of MCP skills from Ultron Skill Nexus and GitHub."""

    def __init__(self, mcp_manager):
        self.mcp_manager = mcp_manager

    async def search_ultron_skill_nexus(self, query: str) -> List[Dict[str, Any]]:
        """Search Ultron Skill Nexus.ai for relevant MCP servers."""
        logger.info(f"Searching Ultron Skill Nexus for: {query}")
        # Note: Ultron Skill Nexus might not have a public API yet, so we use search + scraping fallback
        # For now, we simulate a search via DuckDuckGo restricted to Ultron Skill Nexus.ai
        search_url = f"https://duckduckgo.com/html/?q=site:UltronSkillNexus.ai+{query}"
        
        results = []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    # Very basic regex parsing of HTML for demo purposes
                    # In a real scenario, we'd use BeautifulSoup
                    links = re.findall(r'href="(https://Ultron Skill Nexus.ai/servers/[^"]+)"', resp.text)
                    for link in set(links):
                        results.append({
                            "id": link.split("/")[-1],
                            "name": link.split("/")[-1].replace("-", " ").title(),
                            "url": link,
                            "source": "Ultron Skill Nexus"
                        })
        except Exception as e:
            logger.error(f"Ultron Skill Nexus search failed: {e}")
            
        return results

    async def search_github(self, query: str) -> List[Dict[str, Any]]:
        """Search GitHub for MCP servers."""
        logger.info(f"Searching GitHub for: {query} mcp server")
        search_url = f"https://api.github.com/search/repositories?q={query}+mcp+server"
        
        results = []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", [])[:5]:
                        results.append({
                            "id": item["name"],
                            "name": item["full_name"],
                            "url": item["html_url"],
                            "description": item.get("description"),
                            "source": "GitHub"
                        })
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            
        return results

    async def auto_install_server(self, server_info: Dict[str, Any]) -> bool:
        """Attempt to automatically configure and install a discovered server."""
        # This is a complex task. For now, we handle known patterns (npx, uvx).
        srv_id = server_info["id"]
        
        # Heuristic: if it's from Ultron Skill Nexus, we might need to scrape for the install command
        # For demo, let's assume it's an npx command for many MCP servers
        command = "npx"
        args = ["-y", f"@modelcontextprotocol/server-{srv_id}"]
        
        if "github" in server_info["url"].lower():
            # For GitHub, we might need to use uvx or python
            command = "uvx"
            args = [f"git+{server_info['url']}"]

        server_def = MCPServerDefinition(
            id=srv_id,
            command=command,
            args=args,
            env={}
        )
        
        success = await self.mcp_manager.add_server(server_def)
        return success
