"""Security Module — Permission model, audit logging, and anomaly detection.

Provides a centralized security layer for the AGI system:

1. Permission Model: Each agent has defined capabilities and restrictions
2. Audit Log: All actions are recorded immutably
3. Anomaly Detection: Detect unusual patterns in agent behavior
4. Rate Limiting: Per-agent and per-action rate limits
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Available permissions for agents."""
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    NETWORK_OUTBOUND = "network:outbound"
    NETWORK_INBOUND = "network:inbound"
    PROCESS_SPAWN = "process:spawn"
    PROCESS_KILL = "process:kill"
    SCREEN_CAPTURE = "screen:capture"
    SCREEN_INTERACT = "screen:interact"
    KEYBOARD_INPUT = "keyboard:input"
    MOUSE_INPUT = "mouse:input"
    CLIPBOARD_ACCESS = "clipboard:access"
    CODE_EXECUTE = "code:execute"
    SYSTEM_MONITOR = "system:monitor"
    LLM_CALL = "llm:call"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    SELF_MODIFY = "self:modify"


# Default permission profiles for agents
AGENT_PERMISSIONS: dict[str, set[Permission]] = {
    "orchestrator": {
        Permission.LLM_CALL, Permission.MEMORY_READ, Permission.MEMORY_WRITE,
    },
    "coder": {
        Permission.FILE_READ, Permission.FILE_WRITE, Permission.CODE_EXECUTE,
        Permission.LLM_CALL, Permission.MEMORY_READ,
    },
    "researcher": {
        Permission.NETWORK_OUTBOUND, Permission.FILE_WRITE,
        Permission.LLM_CALL, Permission.MEMORY_READ, Permission.MEMORY_WRITE,
    },
    "rpa_operator": {
        Permission.SCREEN_CAPTURE, Permission.SCREEN_INTERACT,
        Permission.KEYBOARD_INPUT, Permission.MOUSE_INPUT,
        Permission.PROCESS_SPAWN, Permission.LLM_CALL,
    },
    "sysmon": {
        Permission.SYSTEM_MONITOR, Permission.FILE_READ,
        Permission.LLM_CALL, Permission.MEMORY_WRITE,
    },
    "email": {
        Permission.NETWORK_OUTBOUND, Permission.LLM_CALL,
        Permission.MEMORY_READ,
    },
    "clipboard": {
        Permission.CLIPBOARD_ACCESS, Permission.LLM_CALL,
    },
    "files": {
        Permission.FILE_READ, Permission.FILE_WRITE, Permission.FILE_DELETE,
        Permission.LLM_CALL,
    },
    "memory_keeper": {
        Permission.MEMORY_READ, Permission.MEMORY_WRITE,
        Permission.LLM_CALL, Permission.FILE_READ,
    },
    "error_analyzer": {
        Permission.FILE_READ, Permission.FILE_WRITE, Permission.CODE_EXECUTE,
        Permission.LLM_CALL, Permission.MEMORY_READ, Permission.MEMORY_WRITE,
    },
}


@dataclass
class AuditEntry:
    """An immutable audit log entry."""
    timestamp: datetime
    agent: str
    action: str
    permission: str
    resource: str
    allowed: bool
    details: str = ""
    hash: str = ""  # Chain hash for tamper detection

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent": self.agent,
            "action": self.action,
            "permission": self.permission,
            "resource": self.resource,
            "allowed": self.allowed,
            "details": self.details[:500],
            "hash": self.hash,
        }


class SecurityManager:
    """Central security manager for the AGI system."""

    def __init__(
        self,
        audit_dir: str = "./data/audit",
        max_actions_per_minute: int = 60,
        enable_anomaly_detection: bool = True,
    ) -> None:
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._audit_file = self.audit_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"

        self._permissions = dict(AGENT_PERMISSIONS)
        self._rate_limits: dict[str, list[float]] = {}  # agent → list of timestamps
        self._max_actions_per_minute = max_actions_per_minute
        self._enable_anomaly = enable_anomaly_detection

        # Anomaly detection state
        self._action_history: dict[str, list[str]] = {}  # agent → recent actions
        self._anomaly_threshold = 10  # Flag if same action > N times in window

        # Chain hash for audit integrity
        self._last_hash = "genesis"
        self._lock = threading.Lock()

        # File path restrictions (whitelist roots for file operations)
        self._allowed_file_roots: list[Path] = [
            Path("./workspace"),
            Path("./data"),
            Path("./temp"),
        ]

        logger.info("SecurityManager initialized (audit_dir=%s)", self.audit_dir)

    # ── Permission Checks ────────────────────────────────────────────────

    def check_permission(
        self,
        agent_name: str,
        permission: Permission,
        resource: str = "",
        details: str = "",
    ) -> bool:
        """Check if an agent has permission to perform an action.

        Returns True if allowed, False if denied.
        Always logs the check in the audit trail.
        """
        agent_key = agent_name.lower().replace(" ", "_")
        agent_perms = self._permissions.get(agent_key, set())
        allowed = permission in agent_perms

        # Additional file path check for file operations
        if allowed and permission in (Permission.FILE_READ, Permission.FILE_WRITE, Permission.FILE_DELETE):
            allowed = self._is_path_allowed(resource)
            if not allowed:
                logger.warning(
                    "SECURITY: File path blocked for %s: %s (outside allowed roots)",
                    agent_name, resource
                )

        # Rate limit check
        if allowed and not self._check_rate_limit(agent_key):
            logger.warning("SECURITY: Rate limit exceeded for %s", agent_name)
            allowed = False

        # Anomaly detection
        if allowed and self._enable_anomaly:
            self._check_anomaly(agent_key, permission.value)

        # Audit log
        self._log_audit(
            agent=agent_name,
            action="permission_check",
            permission=permission.value,
            resource=resource,
            allowed=allowed,
            details=details,
        )

        if not allowed:
            logger.warning(
                "SECURITY: Permission DENIED — agent=%s, permission=%s, resource=%s",
                agent_name, permission.value, resource
            )

        return allowed

    def grant_permission(self, agent_name: str, permission: Permission) -> None:
        """Grant a permission to an agent (runtime only)."""
        agent_key = agent_name.lower().replace(" ", "_")
        if agent_key not in self._permissions:
            self._permissions[agent_key] = set()
        self._permissions[agent_key].add(permission)
        self._log_audit(agent_key, "grant_permission", permission.value, "", True)
        logger.info("Permission granted: %s → %s", agent_name, permission.value)

    def revoke_permission(self, agent_name: str, permission: Permission) -> None:
        """Revoke a permission from an agent."""
        agent_key = agent_name.lower().replace(" ", "_")
        if agent_key in self._permissions:
            self._permissions[agent_key].discard(permission)
        self._log_audit(agent_key, "revoke_permission", permission.value, "", True)
        logger.info("Permission revoked: %s ✕ %s", agent_name, permission.value)

    def get_agent_permissions(self, agent_name: str) -> set[Permission]:
        """Get all permissions for an agent."""
        agent_key = agent_name.lower().replace(" ", "_")
        return self._permissions.get(agent_key, set())

    # ── File Path Security ───────────────────────────────────────────────

    def _is_path_allowed(self, path_str: str) -> bool:
        """Check if a file path is within allowed roots."""
        if not path_str:
            return True  # No path specified — allow

        try:
            target = Path(path_str).resolve()
            for root in self._allowed_file_roots:
                if target.is_relative_to(root.resolve()):
                    return True
        except Exception:
            pass

        return False

    def add_allowed_path(self, path: str) -> None:
        """Add a path to the allowed file roots."""
        self._allowed_file_roots.append(Path(path))
        logger.info("Added allowed path: %s", path)

    # ── Rate Limiting ────────────────────────────────────────────────────

    def _check_rate_limit(self, agent_key: str) -> bool:
        """Check if agent is within rate limits."""
        now = time.monotonic()
        window = 60.0  # 1 minute

        if agent_key not in self._rate_limits:
            self._rate_limits[agent_key] = []

        # Clean old entries
        self._rate_limits[agent_key] = [
            t for t in self._rate_limits[agent_key] if now - t < window
        ]

        if len(self._rate_limits[agent_key]) >= self._max_actions_per_minute:
            return False

        self._rate_limits[agent_key].append(now)
        return True

    # ── Anomaly Detection ────────────────────────────────────────────────

    def _check_anomaly(self, agent_key: str, action: str) -> None:
        """Simple anomaly detection — flag repetitive patterns."""
        if agent_key not in self._action_history:
            self._action_history[agent_key] = []

        history = self._action_history[agent_key]
        history.append(action)

        # Keep last 100 actions
        if len(history) > 100:
            self._action_history[agent_key] = history[-100:]

        # Check for repetitive pattern
        recent = history[-self._anomaly_threshold:]
        if len(recent) >= self._anomaly_threshold and len(set(recent)) == 1:
            logger.warning(
                "ANOMALY: Agent '%s' executed '%s' %d times consecutively",
                agent_key, action, self._anomaly_threshold
            )

    # ── Audit Logging ────────────────────────────────────────────────────

    def _log_audit(
        self,
        agent: str,
        action: str,
        permission: str,
        resource: str,
        allowed: bool,
        details: str = "",
    ) -> None:
        """Append an entry to the audit log with chain hash for integrity."""
        with self._lock:
            # Create chain hash for tamper detection
            entry_data = f"{self._last_hash}|{agent}|{action}|{permission}|{resource}|{allowed}"
            entry_hash = hashlib.sha256(entry_data.encode()).hexdigest()[:16]

            entry = AuditEntry(
                timestamp=datetime.now(),
                agent=agent,
                action=action,
                permission=permission,
                resource=resource,
                allowed=allowed,
                details=details,
                hash=entry_hash,
            )

            self._last_hash = entry_hash

            # Append to JSONL file (one entry per line)
            try:
                with open(self._audit_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry.to_dict()) + "\n")
            except Exception as e:
                logger.error("Failed to write audit log: %s", e)

    def get_audit_trail(self, agent: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Read recent audit entries."""
        entries = []
        try:
            if self._audit_file.exists():
                lines = self._audit_file.read_text(encoding="utf-8").strip().split("\n")
                for line in reversed(lines[-limit * 2:]):  # Read extra in case of filtering
                    try:
                        entry = json.loads(line)
                        if agent and entry.get("agent") != agent:
                            continue
                        entries.append(entry)
                        if len(entries) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error("Failed to read audit log: %s", e)

        return entries

    # ── Statistics ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Security statistics."""
        return {
            "agents_with_permissions": len(self._permissions),
            "allowed_file_roots": [str(p) for p in self._allowed_file_roots],
            "rate_limit_per_minute": self._max_actions_per_minute,
            "anomaly_detection": self._enable_anomaly,
            "audit_file": str(self._audit_file),
        }
