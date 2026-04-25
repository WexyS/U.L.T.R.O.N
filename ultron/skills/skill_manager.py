"""
SkillManager:
- skills/ klasöründeki SKILL.md dosyalarını tarar
- İçeriklerini ChromaDB'ye embed eder
- Agent bir görev alınca ilgili skill'i RAG ile bulur
- Bulunan skill içeriğini sistem promptuna enjekte eder
"""

import os
import gc
import json
import hashlib
import asyncio
import aiosqlite
import chromadb
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

SKILLS_DIR = Path("skills")
SKILL_DB = "data/skills_index.db"
CHROMA_COLL = "ultron_skills"
MAX_SKILL_LEN = 8000  # RAM koruması: 8KB/skill


class SkillManager:
    def __init__(self):
        self.embedder = None
        if SentenceTransformer:
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.chroma = chromadb.PersistentClient(path="data/chroma")
        self.collection = self.chroma.get_or_create_collection(CHROMA_COLL)

    async def init_db(self):
        async with aiosqlite.connect(SKILL_DB) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS skills (
                    id           TEXT PRIMARY KEY,
                    name         TEXT,
                    file_path    TEXT,
                    content_hash TEXT,
                    indexed_at   TEXT,
                    category     TEXT
                )
            """
            )
            await db.commit()

    async def index_all(self, skills_dir: Optional[str] = None) -> int:
        """
        skills/ altındaki tüm SKILL.md dosyalarını tara ve ChromaDB'ye ekle.
        Zaten indexlenmiş (hash aynı) olanları atla.
        Döndürür: yeni indexlenen skill sayısı
        """
        root = Path(skills_dir) if skills_dir else SKILLS_DIR
        if not root.exists():
            return 0

        skill_files = list(root.rglob("SKILL.md"))
        indexed = 0

        # 32GB RAM koruması: 50'şer batch işle
        for i in range(0, len(skill_files), 50):
            batch = skill_files[i : i + 50]
            for path in batch:
                try:
                    await self._index_one(path)
                    indexed += 1
                except Exception as e:
                    print(f"[SkillManager] Atlandı {path}: {e}")
            gc.collect()

        return indexed

    async def _index_one(self, path: Path):
        content = path.read_text(encoding="utf-8", errors="ignore")
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Zaten indexlendiyse atla
        async with aiosqlite.connect(SKILL_DB) as db:
            async with db.execute(
                "SELECT id FROM skills WHERE file_path=? AND content_hash=?",
                (str(path), content_hash),
            ) as cur:
                if await cur.fetchone():
                    return

        skill_name = path.parent.name
        category = path.parts[-3] if len(path.parts) >= 3 else "general"

        # Önce başlık + ilk 500 char embed et (hız için)
        short = content[:500].strip()
        if self.embedder:
            emb = self.embedder.encode(short).tolist()
        else:
            # Fallback: basit hash-based embedding
            emb = [float(hash(c) % 1000) / 1000.0 for c in short[:384]]

        uid = f"skill_{content_hash[:16]}"

        self.collection.upsert(
            ids=[uid],
            embeddings=[emb],
            documents=[content[:MAX_SKILL_LEN]],
            metadatas=[
                {"name": skill_name, "file_path": str(path), "category": category}
            ],
        )
        del emb
        gc.collect()

        async with aiosqlite.connect(SKILL_DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO skills VALUES (?,?,?,?,?,?)",
                (uid, skill_name, str(path), content_hash, datetime.now().isoformat(), category),
            )
            await db.commit()

    async def find_relevant(
        self, task: str, top_k: int = 3, min_score: float = 0.3
    ) -> list[dict]:
        """
        Görev metnine göre en uygun skill'leri bul.
        Döndürür: [{"name", "content", "score", "file_path"}, ...]
        """
        if self.embedder:
            emb = self.embedder.encode(task).tolist()
        else:
            emb = [float(hash(c) % 1000) / 1000.0 for c in task[:384]]

        results = self.collection.query(
            query_embeddings=[emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        del emb
        gc.collect()

        skills = []
        for i, doc in enumerate(results["documents"][0]):
            score = 1 - results["distances"][0][i]
            if score >= min_score:
                skills.append(
                    {
                        "name": results["metadatas"][0][i]["name"],
                        "content": doc[:MAX_SKILL_LEN],
                        "score": round(score, 3),
                        "file_path": results["metadatas"][0][i]["file_path"],
                    }
                )
        return skills

    def build_skill_prompt(self, skills: list[dict]) -> str:
        """
        Bulunan skill'leri sistem promptuna enjekte edilecek formata çevir.
        """
        if not skills:
            return ""
        parts = ["## Aktif Beceriler (Skill Context)\n"]
        for s in skills:
            parts.append(
                f"### {s['name']} (alaka: {s['score']})\n"
                f"{s['content'][:2000]}\n"
            )
        return "\n".join(parts)

    async def stats(self) -> dict:
        async with aiosqlite.connect(SKILL_DB) as db:
            async with db.execute("SELECT COUNT(*) FROM skills") as cur:
                total = (await cur.fetchone())[0]
            async with db.execute(
                "SELECT category, COUNT(*) FROM skills GROUP BY category"
            ) as cur:
                cats = await cur.fetchall()
        return {"total": total, "by_category": dict(cats)}
