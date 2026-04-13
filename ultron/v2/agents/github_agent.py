"""GitHub Agent — Otonom Git işlemleri.

Bu agent:
- Otomatik git add, commit, push
- Branch oluşturma/yönetimi
- PR oluşturma
- Commit mesajı üretme
- GitHub API ile repo yönetimi

Kullanım:
    from ultron.v2.agents.github_agent import GitHubAgent
    
    agent = GitHubAgent()
    await agent.commit_changes("feat: Add new feature")
    await agent.create_branch("feature/new-stuff")
"""

import os
import logging
import subprocess
from typing import Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class GitHubAgent:
    """Otonom Git işlemleri agent'ı"""
    
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.github_repo = os.environ.get("GITHUB_REPO")  # owner/repo
        
    async def execute(self, payload: dict) -> dict:
        """Agent execute interface"""
        action = payload.get("action", "status")
        
        actions = {
            "status": self.get_status,
            "commit": lambda: self.commit_changes(payload.get("message", "")),
            "push": lambda: self.push_changes(),
            "commit_and_push": lambda: self.commit_and_push(payload.get("message", "")),
            "create_branch": lambda: self.create_branch(payload.get("branch_name", "")),
            "create_pr": lambda: self.create_pr(
                payload.get("title", ""),
                payload.get("body", ""),
                payload.get("base", "main")
            ),
        }
        
        if action not in actions:
            return {"error": f"Unknown action: {action}"}
        
        try:
            result = await actions[action]()
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"GitHub Agent error: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> dict:
        """Git durumu"""
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=self.repo_path
        )
        
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=self.repo_path
        )
        
        return {
            "changed_files": status.stdout.strip().split("\n") if status.stdout else [],
            "current_branch": branch.stdout.strip(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def commit_changes(self, message: Optional[str] = None) -> dict:
        """Değişiklikleri commit et"""
        # Git add
        subprocess.run(
            ["git", "add", "."],
            cwd=self.repo_path, check=True
        )
        
        # Status kontrol
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=self.repo_path
        )
        
        if not status.stdout.strip():
            return {"message": "No changes to commit"}
        
        # Commit mesajı üret (eğer yoksa)
        if not message:
            message = await self._generate_commit_message()
        
        # Git commit
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, cwd=self.repo_path
        )
        
        if commit_result.returncode != 0:
            raise Exception(f"Commit failed: {commit_result.stderr}")
        
        logger.info(f"✅ Committed: {message}")
        return {"message": message, "success": True}
    
    async def push_changes(self, branch: Optional[str] = None) -> dict:
        """Değişiklikleri push et"""
        cmd = ["git", "push", "origin"]
        if branch:
            cmd.append(branch)
        
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, cwd=self.repo_path
        )
        
        if result.returncode != 0:
            raise Exception(f"Push failed: {result.stderr}")
        
        logger.info("✅ Pushed to GitHub")
        return {"success": True}
    
    async def commit_and_push(self, message: Optional[str] = None) -> dict:
        """Commit ve push birlikte"""
        commit_result = await self.commit_changes(message)
        
        if commit_result.get("success"):
            push_result = await self.push_changes()
            return {**commit_result, **push_result}
        
        return commit_result
    
    async def create_branch(self, branch_name: str) -> dict:
        """Yeni branch oluştur"""
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True, text=True, cwd=self.repo_path
        )
        
        if result.returncode != 0:
            raise Exception(f"Branch creation failed: {result.stderr}")
        
        logger.info(f"✅ Created branch: {branch_name}")
        return {"branch": branch_name, "success": True}
    
    async def create_pr(self, title: str, body: str, base: str = "main") -> dict:
        """Pull Request oluştur (GitHub CLI ile)"""
        if not self.github_token:
            return {"error": "GITHUB_TOKEN environment variable required"}
        
        cmd = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", base
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, cwd=self.repo_path
        )
        
        if result.returncode != 0:
            raise Exception(f"PR creation failed: {result.stderr}")
        
        logger.info(f"✅ Created PR: {title}")
        return {"title": title, "success": True}
    
    async def _generate_commit_message(self) -> str:
        """Otomatik commit mesajı üret"""
        status = await self.get_status()
        changed_files = status.get("changed_files", [])
        
        if not changed_files:
            return "chore: No changes"
        
        # Basit mesaj üretimi (daha akıllı yapılabilir)
        file_count = len(changed_files)
        first_file = changed_files[0].split()[-1] if changed_files else "unknown"
        
        return f"feat: Update {file_count} file(s) including {first_file}"


# ─── Autonomous Evolution için yardımcı fonksiyonlar ────────────────────

async def auto_commit_with_message(changes_description: str) -> dict:
    """Autonomous Evolution için otomatik commit
    
    Args:
        changes_description: Ne değişti?
    
    Returns:
        dict: Commit sonucu
    """
    agent = GitHubAgent()
    
    message = (
        f"Auto-Evolution: {changes_description}\n\n"
        f"Generated by Ultron Autonomous System\n"
        f"Date: {datetime.now().isoformat()}"
    )
    
    return await agent.commit_and_push(message)
