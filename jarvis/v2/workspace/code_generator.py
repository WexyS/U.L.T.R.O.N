"""CodeGenerator — Fikir veya şablondan uygulama üretir (Ollama/qwen2.5:14b)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx


class CodeGenerator:
    def __init__(self, workspace_root: str = "workspace/generated_apps"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.ollama_url = "http://localhost:11434/api/generate"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def generate(
        self,
        idea: str,
        project_name: Optional[str] = None,
        tech_stack: str = "html-css-js",
        template_context: Optional[str] = None,
    ) -> dict:
        """Fikir metninden uygulama üretir."""
        if not project_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"project_{ts}"

        target_dir = self.workspace_root / project_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # Prompt oluştur
        template_section = ""
        if template_context:
            tc = template_context[:8000]  # RAM koruma
            template_section = (
                f"\n\nReferans şablon (bu koddan ilham al, kopyalama):\n"
                f"```html\n{tc}\n```"
            )

        prompt = (
            f"Sen kıdemli bir {tech_stack} geliştiricisisin.\n"
            f"Aşağıdaki fikri tam çalışan bir web uygulamasına dönüştür."
            f"{template_section}\n\n"
            f"Fikir: {idea}\n\n"
            f"Kurallar:\n"
            f"- Tek dosya çözüm (index.html içinde CSS ve JS)\n"
            f"- Modern, responsive, karanlık tema\n"
            f"- Türkçe yorum satırları\n"
            f"- Sadece kodu döndür, açıklama yazma\n\n"
            f"Çıktı formatı: sadece kod bloğu, başka hiçbir şey"
        )

        generated_code = await self._call_llm(prompt)

        # Markdown bloklarını sıyır
        code_match = re.search(r"```(?:html|css|js)?\n?(.*?)```", generated_code, re.DOTALL)
        if code_match:
            generated_code = code_match.group(1)

        # Dosyaya yaz
        (target_dir / "index.html").write_text(generated_code, encoding="utf-8")

        log = {
            "idea": idea,
            "tech_stack": tech_stack,
            "project_name": project_name,
            "generated_at": datetime.now().isoformat(),
            "template_used": template_context is not None,
            "file_size_bytes": len(generated_code),
        }
        (target_dir / "generation_log.json").write_text(
            json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {"path": str(target_dir), "project_name": project_name, "log": log}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    async def _call_llm(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.ollama_url,
                json={
                    "model": "qwen2.5:14b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_ctx": 16384, "temperature": 0.3},
                },
            )
            return resp.json().get("response", "")
