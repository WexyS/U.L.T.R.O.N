"""Knowledge Graph Agent — Managing entities and relations in a graph."""

import logging
import networkx as nx
import json
import os
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.knowledge.graph")

class KnowledgeGraphAgent(BaseAgent):
    agent_name = "KnowledgeGraphAgent"
    agent_description = "Specialized Genesis agent for KnowledgeGraph tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="KnowledgeGraph",
            agent_description="Maintains a graph of entities and their relationships extracted from conversations.",
            capabilities=["knowledge_graph", "entity_extraction", "graph_query"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.graph = nx.DiGraph()
        self.storage_path = "data/memory/knowledge_graph.json"
        self._load_graph()

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        action = task.task_type # 'add' or 'query'
        
        try:
            if action == "query":
                result = await self._query_graph(task.input_data)
            else:
                # Default: Extract and add
                result = await self._extract_and_add(task.input_data)
                self._save_graph()
                
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=result
            )
        except Exception as e:
            logger.error(f"Graph operation failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def _extract_and_add(self, text: str) -> str:
        prompt = [
            {"role": "system", "content": "Extract entities and relations from the text. Return JSON: {\"entities\": [{\"name\": \"...\", \"type\": \"...\"}], \"relations\": [{\"source\": \"...\", \"relation\": \"...\", \"target\": \"...\"}]}"},
            {"role": "user", "content": text}
        ]
        resp = await router.chat(prompt)
        import re
        match = re.search(r"\{[\s\S]*\}", resp.content)
        if match:
            data = json.loads(match.group())
            for ent in data.get("entities", []):
                self.graph.add_node(ent["name"], type=ent["type"])
            for rel in data.get("relations", []):
                self.graph.add_edge(rel["source"], rel["target"], relation=rel["relation"])
            return f"Added {len(data.get('entities', []))} entities and {len(data.get('relations', []))} relations."
        return "No entities extracted."

    async def _query_graph(self, question: str) -> str:
        # Simplified: Send graph summary to LLM to answer
        nodes = list(self.graph.nodes(data=True))[:50]
        edges = list(self.graph.edges(data=True))[:50]
        prompt = [
            {"role": "system", "content": "Based on the provided Knowledge Graph data, answer the user's question."},
            {"role": "user", "content": f"Graph: Nodes={nodes}, Edges={edges}\nQuestion: {question}"}
        ]
        resp = await router.chat(prompt)
        return resp.content

    def _load_graph(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
            except Exception as e:
                logger.error(f"Failed to load graph: {e}")

    def _save_graph(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                data = nx.node_link_data(self.graph)
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")

    async def health_check(self) -> bool:
        return True
