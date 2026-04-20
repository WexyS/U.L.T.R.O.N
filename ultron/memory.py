"""Memory system for Ultron: response cache, persistent user memory, and self-learning."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from ultron.config import UltronConfig

logger = logging.getLogger(__name__)


# ─── Response Cache ───────────────────────────────────────────────────────────

class ResponseCache:
    """LRU cache for fast repeated queries with semantic similarity matching."""

    def __init__(self, max_size: int = 200, ttl_seconds: int = 86400, similarity_threshold: float = 0.85):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._persist_path: Optional[Path] = None

    def set_persist_path(self, path: Path) -> None:
        """Set path for persistent cache storage."""
        self._persist_path = path
        self._load()

    def _hash_query(self, query: str) -> str:
        """Create a hash of the normalized query."""
        normalized = self._normalize(query)
        return hashlib.md5(normalized.encode()).hexdigest()

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for cache key matching."""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        # Remove punctuation for fuzzy matching
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def _similarity(self, a: str, b: str) -> float:
        """Simple word-overlap similarity (fast, no embeddings needed)."""
        words_a = set(self._normalize(a).split())
        words_b = set(self._normalize(b).split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def get(self, query: str) -> Optional[str]:
        """Get cached response for a similar query."""
        # Exact match first
        key = self._hash_query(query)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                # Anti-loop: same query hit > 5 times = stale cache
                if entry.get("hits", 0) > 5:
                    logger.debug("Cache LOOP PREVENTED: %s hit %d times", query[:50], entry["hits"])
                    del self._cache[key]
                    return None
                entry["hits"] += 1
                self._cache.move_to_end(key)
                logger.debug("Cache HIT (exact): %s", query[:50])
                return entry["response"]
            else:
                del self._cache[key]

        # Fuzzy match: search for similar cached queries
        best_query = None
        best_score = 0.0
        best_response = None

        for k, entry in list(self._cache.items()):
            if time.time() - entry["timestamp"] >= self.ttl_seconds:
                continue
            score = self._similarity(query, entry["query"])
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_query = entry["query"]
                best_response = entry["response"]

        if best_response:
            logger.debug("Cache HIT (fuzzy %.2f): %s", best_score, query[:50])
            return best_response

        logger.debug("Cache MISS: %s", query[:50])
        return None

    def put(self, query: str, response: str) -> None:
        """Store a response in the cache."""
        key = self._hash_query(query)

        # Don't cache errors or very short responses
        if not response or len(response.strip()) < 10:
            return

        self._cache[key] = {
            "query": query,
            "response": response,
            "timestamp": time.time(),
            "hits": 0,
        }
        self._cache.move_to_end(key)

        # Evict oldest if over capacity
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

        self._save()
        logger.debug("Cache PUT: %s (total: %d)", query[:50], len(self._cache))

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
        self._save()
        logger.info("Response cache cleared")

    def stats(self) -> dict:
        """Get cache statistics."""
        total_hits = sum(e["hits"] for e in self._cache.values())
        total_entries = len(self._cache)
        expired = sum(
            1 for e in self._cache.values()
            if time.time() - e["timestamp"] >= self.ttl_seconds
        )
        return {
            "entries": total_entries,
            "hits": total_hits,
            "expired": expired,
            "hit_rate": total_hits / max(total_hits + total_entries, 1),
            "size_bytes": len(json.dumps(self._cache)),
        }

    def _save(self) -> None:
        """Persist cache to disk."""
        if self._persist_path:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "cache": dict(self._cache),
                "saved_at": datetime.now().isoformat(),
            }
            self._persist_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        """Load cache from disk."""
        if self._persist_path and self._persist_path.exists():
            try:
                content = self._persist_path.read_text(encoding="utf-8")
                if content.strip():
                    data = json.loads(content)
                    self._cache = OrderedDict(data.get("cache", {}))
                    logger.info("Loaded %d cached responses", len(self._cache))
            except Exception as e:
                logger.warning("Failed to load cache: %s", e)


# ─── User Memory (Persistent) ────────────────────────────────────────────────

class UserMemory:
    """Persistent memory about the user: preferences, facts, and patterns.

    Three memory types (CoALA framework):
    - Semantic: facts about the user (name, preferences, expertise level)
    - Episodic: notable events and conversation outcomes
    - Procedural: learned patterns about how to help this user
    """

    def __init__(self, persist_dir: str = "./data/memory"):
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._current_user = "default"

        # Semantic memory: structured user facts
        self._semantic = self._load_json("semantic.json")

        # Profiles: individual user profiles
        self._profiles = self._load_json("profiles.json")
        if not self._profiles.get("users"): self._profiles["users"] = {}

        # Episodic memory: notable events
        self._episodic = self._load_json("episodic.json")

        # Procedural memory: learned interaction patterns
        self._procedural = self._load_json("procedural.json")

        # Conversation summary (short-term context)
        self._summary = self._load_json("summary.json")

    @staticmethod
    def _load_json(filename: str) -> Any:
        path = Path("./data/memory") / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"items": []} if filename != "summary.json" else {}

    def _save_json(self, filename: str, data: Any) -> None:
        path = self._persist_dir / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_all(self) -> None:
        self._save_json("semantic.json", self._semantic)
        self._save_json("episodic.json", self._episodic)
        self._save_json("procedural.json", self._procedural)
        self._save_json("summary.json", self._summary)
        self._save_json("profiles.json", self._profiles)

    def set_user(self, user_name: str) -> None:
        """Switch current user context."""
        self._current_user = user_name
        if user_name not in self._profiles["users"]:
            self._profiles["users"][user_name] = {
                "first_seen": datetime.now().isoformat(),
                "interests": [],
                "traits": {},
                "last_active": datetime.now().isoformat()
            }
        self._save_all()

    def update_profile(self, user_name: str, key: str, value: Any) -> None:
        if user_name not in self._profiles["users"]: self.set_user(user_name)
        self._profiles["users"][user_name][key] = value
        self._profiles["users"][user_name]["last_active"] = datetime.now().isoformat()
        self._save_all()

    def get_profile(self, user_name: str) -> dict:
        return self._profiles["users"].get(user_name, {})

    # ─── Semantic Memory (facts about user) ──────────────────────────────

    def add_fact(self, category: str, key: str, value: str) -> None:
        """Store a fact about the user (e.g., preference, name, timezone)."""
        if "items" not in self._semantic:
            self._semantic["items"] = []

        # Remove any existing fact in the same category+key
        self._semantic["items"] = [
            item for item in self._semantic["items"]
            if not (item.get("category") == category and item.get("key") == key)
        ]

        self._semantic["items"].append({
            "category": category,
            "key": key,
            "value": value,
            "created_at": datetime.now().isoformat(),
            "access_count": 0,
        })
        self._save_all()
        logger.info("Memory fact: %s/%s = %s", category, key, value)

    def get_facts(self, category: Optional[str] = None) -> list[dict]:
        """Retrieve facts, optionally filtered by category."""
        items = self._semantic.get("items", [])
        if category:
            items = [i for i in items if i.get("category") == category]
        # Sort by access count (most used first)
        items.sort(key=lambda x: x.get("access_count", 0), reverse=True)
        for item in items:
            item["access_count"] = item.get("access_count", 0) + 1
        self._save_all()
        return items

    def get_facts_context(self) -> str:
        """Format all facts as context for LLM prompts."""
        facts = self.get_facts()
        profile = self.get_profile(self._current_user)
        
        lines = [f"Information about user '{self._current_user}':"]
        if profile:
            interests = ", ".join(profile.get("interests", []))
            if interests:
                lines.append(f"- Interests: {interests}")
            for k, v in profile.get("traits", {}).items():
                lines.append(f"- {k.capitalize()}: {v}")

        if facts:
            for f in facts:
                lines.append(f"- {f['category']}: {f['key']} = {f['value']}")
        return "\n".join(lines) if len(lines) > 1 else ""

    # ─── Episodic Memory (notable events) ────────────────────────────────

    def add_episode(self, topic: str, summary: str, outcome: str = "", key_insights: Optional[list[str]] = None) -> None:
        """Store a notable conversation/event."""
        if "items" not in self._episodic:
            self._episodic["items"] = []

        self._episodic["items"].append({
            "topic": topic,
            "summary": summary,
            "outcome": outcome,
            "key_insights": key_insights or [],
            "created_at": datetime.now().isoformat(),
        })

        # Keep only last 50 episodes (memory decay)
        self._episodic["items"] = self._episodic["items"][-50:]
        self._save_all()

    def search_episodes(self, query: str, limit: int = 3) -> list[dict]:
        """Find relevant past experiences."""
        items = self._episodic.get("items", [])
        query_words = set(query.lower().split())

        scored = []
        for item in items:
            text = f"{item.get('topic', '')} {item.get('summary', '')} {' '.join(item.get('key_insights', []))}"
            text_words = set(text.lower().split())
            overlap = len(query_words & text_words) / max(len(query_words | text_words), 1)
            if overlap > 0:
                scored.append((overlap, item))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [item for _, item in scored[:limit]]

    def get_recent_episodes(self, limit: int = 5) -> list[dict]:
        """Get most recent episodes."""
        items = self._episodic.get("items", [])
        return items[-limit:]

    # ─── Procedural Memory (learned patterns) ────────────────────────────

    def add_pattern(self, task_type: str, pattern: str, example: str = "") -> None:
        """Store a learned pattern about how to help the user."""
        if "items" not in self._procedural:
            self._procedural["items"] = []

        self._procedural["items"].append({
            "task_type": task_type,
            "pattern": pattern,
            "example": example,
            "created_at": datetime.now().isoformat(),
            "used_count": 0,
        })
        self._save_all()

    def get_relevant_patterns(self, task_type: str) -> list[dict]:
        """Get learned patterns for a task type."""
        items = self._procedural.get("items", [])
        matches = [i for i in items if i.get("task_type") == task_type]
        matches.sort(key=lambda x: x.get("used_count", 0), reverse=True)
        for m in matches:
            m["used_count"] = m.get("used_count", 0) + 1
        self._save_all()
        return matches

    # ─── Conversation Summary (short-term context) ───────────────────────

    def update_summary(self, summary: str) -> None:
        """Update the running conversation summary."""
        self._summary = {
            "content": summary,
            "updated_at": datetime.now().isoformat(),
        }
        self._save_all()

    def get_summary(self) -> str:
        return self._summary.get("content", "")

    # ─── Memory Statistics ────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "semantic_facts": len(self._semantic.get("items", [])),
            "episodic_events": len(self._episodic.get("items", [])),
            "procedural_patterns": len(self._procedural.get("items", [])),
            "has_summary": bool(self._summary.get("content")),
        }

    def clear_all(self) -> None:
        """Wipe all memory (nuclear option)."""
        self._semantic = {"items": []}
        self._episodic = {"items": []}
        self._procedural = {"items": []}
        self._summary = {}
        self._save_all()
        logger.warning("All user memory cleared")


# ─── Self-Learning ────────────────────────────────────────────────────────────

class SelfLearning:
    """Background memory formation - extracts and stores insights from conversations."""

    def __init__(self, user_memory: UserMemory, llm, batch_size: int = 5):
        self.user_memory = user_memory
        self.llm = llm
        self.batch_size = batch_size
        self._pending_conversations: list[dict] = []

    async def learn_from_conversation(self, user_input: str, assistant_response: str) -> None:
        """Extract and store insights from a conversation turn."""
        # Quick pattern extraction (no LLM needed)
        self._extract_patterns(user_input, assistant_response)

        # Batch conversations for background processing
        self._pending_conversations.append({
            "user": user_input,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat(),
        })

        # Process every N conversations (background memory formation)
        if len(self._pending_conversations) >= self.batch_size:
            await self._consolidate_memories()

    async def _consolidate_memories(self) -> None:
        """Background processing: extract deep insights from recent conversations."""
        if not self._pending_conversations:
            return

        conversations = self._pending_conversations[:]
        self._pending_conversations.clear()

        try:
            # Build analysis prompt
            conv_text = "\n\n".join(
                f"User: {c['user']}\nAssistant: {c['assistant'][:200]}"
                for c in conversations[-3:]  # Only last 3 for token budget
            )

            messages = [
                {"role": "system", "content": (
                    "You are a memory formation system. Analyze these conversations "
                    "and extract ONLY new, useful information about the user. "
                    "Focus on: preferences, habits, expertise level, goals, communication style. "
                    "Do NOT extract obvious or already-known information. "
                    "Return a JSON object with: facts (list of {category, key, value}), "
                    "patterns (list of {task_type, pattern}), and episode_summary."
                )},
                {"role": "user", "content": f"Analyze these conversations:\n\n{conv_text}"},
            ]

            response = await self.llm.chat(messages)

            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                insights = json.loads(json_match.group())

                # Store facts
                for fact in insights.get("facts", []):
                    self.user_memory.add_fact(
                        fact.get("category", "general"),
                        fact.get("key", ""),
                        fact.get("value", ""),
                    )

                # Store patterns
                for pattern in insights.get("patterns", []):
                    self.user_memory.add_pattern(
                        pattern.get("task_type", ""),
                        pattern.get("pattern", ""),
                    )

                # Store episode
                self.user_memory.add_episode(
                    topic="conversation_insights",
                    summary=insights.get("episode_summary", ""),
                )

                logger.info("Self-learning: extracted %d facts, %d patterns",
                           len(insights.get("facts", [])),
                           len(insights.get("patterns", [])))

        except Exception as e:
            logger.warning("Memory consolidation failed: %s", e)

    def _extract_patterns(self, user_input: str, assistant_response: str) -> None:
        """Quick pattern extraction without LLM."""
        user_lower = user_input.lower()

        # Detect expertise level from language
        if any(term in user_lower for term in ["what is", "how do i", "explain", "beginner"]):
            self.user_memory.add_fact("expertise", "level", "beginner")
        elif any(term in user_lower for term in ["optimize", "refactor", "architecture", "design pattern"]):
            self.user_memory.add_fact("expertise", "level", "advanced")

        # Detect communication style preference
        if any(term in user_lower for term in ["short", "brief", "concise", "quick"]):
            self.user_memory.add_fact("communication", "style", "prefers concise responses")
        elif any(term in user_lower for term in ["detailed", "explain more", "tell me more", "comprehensive"]):
            self.user_memory.add_fact("communication", "style", "prefers detailed responses")

        # Detect topic interests
        topics = {
            "coding": ["python", "javascript", "code", "function", "api", "debug", "yazılım", "kod"],
            "research": ["research", "study", "learn about", "paper", "article", "araştırma", "bilgi"],
            "productivity": ["schedule", "calendar", "email", "task", "organize", "plan", "ajanda"],
            "marvel": ["marvel", "ultron", "stark", "avengers", "iron man", "yenilmezler"],
        }
        for topic, keywords in topics.items():
            if any(kw in user_lower for kw in keywords):
                # Update profile interests
                profile = self.user_memory.get_profile(self.user_memory._current_user)
                interests = profile.get("interests", [])
                if topic not in interests:
                    interests.append(topic)
                    self.user_memory.update_profile(self.user_memory._current_user, "interests", interests)
                
                # Also track as fact
                existing = self.user_memory.get_facts("interests")
                for item in existing:
                    if item.get("key") == topic:
                        count = int(item.get("value", "0")) + 1
                        self.user_memory.add_fact("interests", topic, str(count))
                        return
                self.user_memory.add_fact("interests", topic, "1")

        # Detect User Name
        name_patterns = [r"benim adım ([\w\s]+)", r"ismin ([\w\s]+)", r"bana ([\w\s]+) de", r"i am ([\w\s]+)", r"call me ([\w\s]+)"]
        for pattern in name_patterns:
            match = re.search(pattern, user_lower)
            if match:
                name = match.group(1).strip()
                if len(name) < 20:
                    self.user_memory.set_user(name)
                    self.user_memory.add_fact("identity", "name", name)
                    logger.info("IDENTITY RECOGNIZED: User is %s", name)

    async def finalize(self) -> None:
        """Process any remaining pending conversations."""
        if self._pending_conversations:
            await self._consolidate_memories()


# ─── Memory Context Builder ───────────────────────────────────────────────────

def build_system_prompt(user_memory: UserMemory, base_prompt: str = "") -> str:
    """Build an enriched system prompt with user memory context."""
    parts = [base_prompt] if base_prompt else []

    # Add known user facts
    facts_context = user_memory.get_facts_context()
    if facts_context:
        parts.append(facts_context)

    # Add recent conversation summary
    summary = user_memory.get_summary()
    if summary:
        parts.append(f"\nRecent conversation context:\n{summary}")

    # Add relevant procedural patterns
    patterns = user_memory.get_relevant_patterns("general")
    if patterns:
        pattern_lines = ["Learned patterns from past interactions:"]
        for p in patterns[:3]:
            pattern_lines.append(f"- {p['pattern']}")
        parts.append("\n".join(pattern_lines))

    return "\n\n".join(parts)
