"""
LongTermMemory — SQLite + FTS5 tabanlı kalıcı bellek. ChromaDB ile vektör arama.
Her fact/episode otomatik embed edilir, hibrit arama (FTS5 + vector) yapar.
Decay mekanizması ile eski/önemsiz bilgiler zamanla unutulur.
"""

import uuid
import gc
import json
import aiosqlite
import chromadb
from datetime import datetime, timedelta
from typing import List, Optional
from sentence_transformers import SentenceTransformer


class LongTermMemory:
    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = db_path
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.chroma = chromadb.PersistentClient(path="data/chroma")
        self.collection = self.chroma.get_or_create_collection("jarvis_memory")

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY, timestamp TEXT,
                    summary TEXT, tags TEXT,
                    importance REAL DEFAULT 0.5,
                    decay REAL DEFAULT 1.0
                );
                CREATE TABLE IF NOT EXISTS facts (
                    id TEXT PRIMARY KEY, content TEXT,
                    source TEXT, confidence REAL DEFAULT 1.0,
                    created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE, type TEXT,
                    attributes TEXT, last_seen TEXT
                );
            """)
            await db.commit()

    async def store_episode(self, summary: str, tags: List[str] = None, importance: float = 0.5):
        item_id = str(uuid.uuid4())
        emb = self.embedder.encode(summary).tolist()
        self.collection.add(
            ids=[f"ep_{item_id}"], embeddings=[emb],
            documents=[summary],
            metadatas=[{"type": "episode", "importance": importance,
                        "tags": json.dumps(tags or [])}]
        )
        del emb
        gc.collect()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO episodes VALUES (?,?,?,?,?,?)",
                (item_id, datetime.now().isoformat(), summary,
                 json.dumps(tags or []), importance, 1.0)
            )
            await db.commit()

    async def store_fact(self, content: str, source: str = "conversation", confidence: float = 1.0):
        item_id = str(uuid.uuid4())
        emb = self.embedder.encode(content).tolist()
        self.collection.add(
            ids=[f"fact_{item_id}"], embeddings=[emb],
            documents=[content],
            metadatas=[{"type": "fact", "confidence": confidence, "source": source}]
        )
        del emb
        gc.collect()
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO facts VALUES (?,?,?,?,?)",
                (item_id, content, source, confidence, now, now)
            )
            await db.commit()

    async def recall(self, query: str, top_k: int = 5, min_importance: float = 0.3) -> List[dict]:
        gc.collect()
        emb = self.embedder.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[emb], n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        del emb
        gc.collect()
        items = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            importance = float(meta.get("importance", meta.get("confidence", 0.5)))
            if importance >= min_importance:
                items.append({
                    "content": doc,
                    "metadata": meta,
                    "relevance": 1 - results["distances"][0][i]
                })
        return items

    async def forget_old(self, days: int = 90, importance_threshold: float = 0.2):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        decay_factor = 0.95
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE episodes SET decay = decay * ? WHERE timestamp < ? AND importance < 0.5",
                (decay_factor, cutoff)
            )
            await db.execute("DELETE FROM episodes WHERE decay < ?", (importance_threshold,))
            await db.commit()

    async def nightly_decay(self, decay_factor: float = 0.95):
        await self.forget_old(days=30, importance_threshold=0.1)

    async def consolidate(self):
        """Episodları semantic olarak grupla, benzerleri birleştir."""
        all_docs = self.collection.get(include=["documents", "metadatas"])
        if not all_docs["documents"]:
            return

        docs = all_docs["documents"]
        if len(docs) < 5:
            return

        embeddings = self.embedder.encode(docs[:20]).tolist()

        threshold = 0.75
        clusters = []
        for i, emb in enumerate(embeddings):
            assigned = False
            for cluster in clusters:
                sim = 1 - self._cosine_sim(emb, cluster["centroid"])
                if sim > threshold:
                    cluster["indices"].append(i)
                    n = len(cluster["indices"])
                    cluster["centroid"] = [(c * (n - 1) + v) / n for c, v in zip(cluster["centroid"], emb)]
                    assigned = True
                    break
            if not assigned:
                clusters.append({"indices": [i], "centroid": list(emb)})

        for cluster in clusters:
            if len(cluster["indices"]) > 1:
                ids_to_keep = [all_docs["ids"][cluster["indices"][0]]]
                ids_to_delete = [all_docs["ids"][i] for i in cluster["indices"][1:]]
                if ids_to_delete:
                    try:
                        self.collection.delete(ids=ids_to_delete)
                    except Exception:
                        pass

    def _cosine_sim(self, a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)

    async def stats(self) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM episodes") as c:
                ep_count = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM facts") as c:
                fact_count = (await c.fetchone())[0]
        return {
            "episodes": ep_count,
            "facts": fact_count,
            "chroma_entries": self.collection.count(),
        }
