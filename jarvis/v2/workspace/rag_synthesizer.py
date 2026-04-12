"""RAGSynthesizer — ChromaDB'den şablon bul, LLM ile sentezle."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List

import httpx

from .models import SynthesizeRequest, WorkspaceItem

if TYPE_CHECKING:
    from .workspace_manager import WorkspaceManager


class RAGSynthesizer:
    def __init__(self, manager: "WorkspaceManager"):
        self.manager = manager
        self.workspace_root = Path("workspace/generated_apps")
        self.ollama_url = "http://localhost:11434/api/generate"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def synthesize(self, req: SynthesizeRequest) -> WorkspaceItem:
        import gc
        import uuid

        # 1. Semantic arama — ilgili şablonları bul
        if req.source_templates:
            templates = [
                {
                    "metadata": {
                        "name": t,
                        "file_path": f"workspace/cloned_templates/{t}",
                    }
                }
                for t in req.source_templates
            ]
        else:
            templates = await self.manager.search_templates(req.user_command, top_k=3)

        # 2. Şablon içeriklerini yükle (memory-safe)
        context_parts: list[str] = []
        for t in templates:
            meta = t.get("metadata", {})
            name = meta.get("name", "unknown")
            file_path = meta.get("file_path", "")
            html_file = Path(file_path) / "index.html"
            meta_file = Path(file_path) / "metadata.json"

            content = ""
            if html_file.exists():
                content = html_file.read_text(encoding="utf-8")
                content = content[:6000]  # RAM koruma

            meta_info = {}
            if meta_file.exists():
                meta_info = json.loads(meta_file.read_text(encoding="utf-8"))

            context_parts.append(
                f"=== ŞABLON: {name} ===\n"
                f"Açıklama: {meta_info.get('summary', '')}\n"
                f"Bileşenler: {', '.join(meta_info.get('components', []))}\n"
                f"Kod (kısaltılmış):\n{content}\n"
            )

        context = "\n\n".join(context_parts)

        # 3. LLM ile sentezle
        prompt = (
            f"Sen kıdemli bir frontend geliştiricisisin.\n"
            f'Kullanıcı komutu: "{req.user_command}"\n'
            f"Hedef proje adı: {req.target_project}\n\n"
            f"Mevcut şablonlardan ilham alarak yeni bir web projesi oluştur:\n\n"
            f"{context}\n\n"
            f"Kurallar:\n"
            f"- Şablonları birebir kopyalama, sadece ilham al\n"
            f"- Yeni, özgün ve çalışan bir uygulama üret\n"
            f"- Tek HTML dosyası (CSS ve JS dahil)\n"
            f"- Modern, profesyonel tasarım\n"
            f"- Sadece kodu döndür\n\n"
            f"Hedef: {req.user_command}"
        )

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                self.ollama_url,
                json={
                    "model": "qwen2.5:14b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_ctx": 32768, "temperature": 0.4},
                },
            )
            generated = resp.json().get("response", "")

        # Kodu temizle
        code_match = re.search(r"```(?:html)?\n?(.*?)```", generated, re.DOTALL)
        if code_match:
            generated = code_match.group(1)

        # Kaydet
        target_dir = self.workspace_root / req.target_project
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "index.html").write_text(generated, encoding="utf-8")

        log = {
            "command": req.user_command,
            "target": req.target_project,
            "sources": [t.get("metadata", {}).get("name") for t in templates],
            "synthesized_at": datetime.now().isoformat(),
        }
        (target_dir / "synthesis_log.json").write_text(
            json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        gc.collect()

        item_id = str(uuid.uuid4())
        item = WorkspaceItem(
            id=item_id,
            name=req.target_project,
            type="synthesized",
            created_at=datetime.now(),
            description=req.user_command,
            file_path=str(target_dir),
        )
        await self.manager._save_item(item)
        return item
