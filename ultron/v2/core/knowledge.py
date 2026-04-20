import os
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LocalKnowledgeEngine:
    """Core engine for indexing and retrieving local technical knowledge."""
    
    def __init__(self, memory_engine: Any, index_dir: str = "./data/knowledge_base"):
        self.memory = memory_engine
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._indexed_paths: List[str] = []

    async def index_directory(self, directory_path: str, file_extensions: List[str] = [".py", ".md", ".txt", ".js", ".ts", ".html"]):
        """Index all text-based files in a directory for semantic search."""
        path = Path(directory_path)
        if not path.is_dir():
            logger.error(f"Cannot index non-existent directory: {directory_path}")
            return

        logger.info(f"Indexing directory: {directory_path}...")
        count = 0
        for ext in file_extensions:
            for file_path in path.rglob(f"*{ext}"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    if not content.strip(): continue
                    
                    # Store in long-term memory (ChromaDB)
                    await self.memory.add_fact(
                        content=content,
                        metadata={
                            "source": str(file_path),
                            "filename": file_path.name,
                            "type": "technical_doc",
                            "extension": ext
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"Failed to index {file_path}: {e}")
        
        self._indexed_paths.append(directory_path)
        logger.info(f"Finished indexing {count} files from {directory_path}")

    async def index_dataset(self, file_path: str):
        """Index a structured dataset (CSV/JSON) for data-aware retrieval."""
        path = Path(file_path)
        if not path.is_file():
            logger.error(f"Dataset file not found: {file_path}")
            return

        logger.info(f"Indexing structured dataset: {file_path}...")
        try:
            if path.suffix == ".csv":
                with open(path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        content = " | ".join([f"{k}: {v}" for k, v in row.items()])
                        await self.memory.add_fact(
                            content=content,
                            metadata={"source": str(path), "row": i, "type": "dataset_row"}
                        )
            elif path.suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for i, item in enumerate(data):
                        await self.memory.add_fact(
                            content=json.dumps(item),
                            metadata={"source": str(path), "index": i, "type": "dataset_item"}
                        )
            logger.info(f"Successfully indexed dataset: {path.name}")
        except Exception as e:
            logger.error(f"Failed to index dataset {file_path}: {e}")

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the local knowledge base for relevant technical info."""
        results = await self.memory.search_facts(query, limit=limit)
        return results

    def get_indexed_paths(self) -> List[str]:
        return self._indexed_paths
