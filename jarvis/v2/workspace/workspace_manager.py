"""WorkspaceManager — Klonlama, üretme ve sentezleme işlemlerini koordine eder."""

from __future__ import annotations

import gc
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite
import chromadb
from sentence_transformers import SentenceTransformer

from .code_generator import CodeGenerator
from .models import CloneRequest, GenerateRequest, SynthesizeRequest, WorkspaceItem
from .playwright_agent import PlaywrightAgent
from .rag_synthesizer import RAGSynthesizer

DB_PATH = "workspace/workspace_index.db"
CHROMA_COLLECTION = "workspace_templates"


class WorkspaceManager:
    def __init__(self):
        self.playwright = PlaywrightAgent()
        self.generator = CodeGenerator()
        self.synthesizer = RAGSynthesizer(self)
        self.chroma = chromadb.PersistentClient(path="data/chroma")
        self.collection = self.chroma.get_or_create_collection(CHROMA_COLLECTION)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_items (
                    id TEXT PRIMARY KEY,
                    name TEXT, type TEXT, url TEXT,
                    created_at TEXT, description TEXT,
                    components TEXT, file_path TEXT, chroma_id TEXT
                )
                """
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------
    async def clone_site(self, req: CloneRequest) -> WorkspaceItem:
        result = await self.playwright.clone(req.url, req.site_name)
        if not result["success"]:
            raise ValueError(result["error"])

        meta = result["metadata"]
        item_id = str(uuid.uuid4())
        chroma_id = f"clone_{item_id}"

        # ChromaDB'ye ekle
        summary_text = (
            f"{meta['title']}. {meta['summary']}. "
            f"Bileşenler: {', '.join(meta['components'])}. URL: {meta['url']}"
        )
        embedding = self.embedder.encode(summary_text).tolist()
        self.collection.add(
            ids=[chroma_id],
            embeddings=[embedding],
            documents=[summary_text],
            metadatas=[
                {
                    "type": "cloned",
                    "name": meta["site_name"],
                    "url": meta["url"],
                    "file_path": meta["file_path"],
                    "components": json.dumps(meta["components"]),
                }
            ],
        )
        del embedding
        gc.collect()

        item = WorkspaceItem(
            id=item_id,
            name=meta["site_name"],
            type="cloned",
            url=meta["url"],
            created_at=datetime.now(),
            description=meta["summary"],
            components=meta["components"],
            file_path=meta["file_path"],
            chroma_id=chroma_id,
        )
        await self._save_item(item)
        return item

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------
    async def generate_app(self, req: GenerateRequest) -> WorkspaceItem:
        template_context = None
        if req.use_template:
            template_context = await self._get_template_content(req.use_template)

        result = await self.generator.generate(
            idea=req.idea,
            project_name=req.project_name,
            tech_stack=req.tech_stack,
            template_context=template_context,
        )
        item_id = str(uuid.uuid4())
        chroma_id = f"gen_{item_id}"

        summary_text = (
            f"Üretilen uygulama: {req.idea}. Proje: {result['project_name']}"
        )
        embedding = self.embedder.encode(summary_text).tolist()
        self.collection.add(
            ids=[chroma_id],
            embeddings=[embedding],
            documents=[summary_text],
            metadatas=[
                {
                    "type": "generated",
                    "name": result["project_name"],
                    "file_path": result["path"],
                }
            ],
        )
        del embedding
        gc.collect()

        item = WorkspaceItem(
            id=item_id,
            name=result["project_name"],
            type="generated",
            created_at=datetime.now(),
            description=req.idea,
            file_path=result["path"],
            chroma_id=chroma_id,
        )
        await self._save_item(item)
        return item

    # ------------------------------------------------------------------
    # Synthesize
    # ------------------------------------------------------------------
    async def synthesize(self, req: SynthesizeRequest) -> WorkspaceItem:
        return await self.synthesizer.synthesize(req)

    # ------------------------------------------------------------------
    # Search & List
    # ------------------------------------------------------------------
    async def search_templates(self, query: str, top_k: int = 5) -> List[dict]:
        """ChromaDB'de semantic arama yap."""
        import gc

        embedding = self.embedder.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        del embedding
        gc.collect()

        items = []
        for i, doc in enumerate(results["documents"][0]):
            items.append(
                {
                    "document": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )
        return items

    async def list_workspace(self) -> List[WorkspaceItem]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM workspace_items ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _save_item(self, item: WorkspaceItem):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO workspace_items VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    item.id,
                    item.name,
                    item.type,
                    item.url,
                    item.created_at.isoformat(),
                    item.description,
                    json.dumps(item.components),
                    item.file_path,
                    item.chroma_id,
                ),
            )
            await db.commit()

    async def _get_template_content(self, name: str) -> Optional[str]:
        path = Path(f"workspace/cloned_templates/{name}/index.html")
        if path.exists():
            content = path.read_text(encoding="utf-8")
            # Memory koruma: 5 MB'dan büyükse kırp
            if len(content) > 5_000_000:
                content = content[:50_000] + "\n<!-- truncated -->"
            return content
        return None

    def _row_to_item(self, row) -> WorkspaceItem:
        return WorkspaceItem(
            id=row[0],
            name=row[1],
            type=row[2],
            url=row[3],
            created_at=datetime.fromisoformat(row[4]),
            description=row[5],
            components=json.loads(row[6] or "[]"),
            file_path=row[7],
            chroma_id=row[8],
        )
