"""RPA Sandbox — Whitelist, audit log, and approval gate for RPA actions.

Ensures that the RPAOperatorAgent can only interact with approved applications
and logs every action for security review.

Usage:
    sandbox = RPASandbox()
    if sandbox.is_action_allowed("chrome.exe", "click"):
        sandbox.log_action("chrome.exe", "click", {"x": 100, "y": 200})
        # ... execute RPA action ...
"""

import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("ultron.security.rpa_sandbox")

# ── Default allowed applications ─────────────────────────────────────────
DEFAULT_WHITELIST: Set[str] = {
    # Browsers
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    # Productivity
    "notepad.exe", "notepad++.exe", "code.exe",
    "explorer.exe", "cmd.exe", "powershell.exe",
    # Media
    "spotify.exe", "vlc.exe",
    # Communication
    "discord.exe", "slack.exe", "teams.exe",
    # Development
    "terminal.exe", "windowsterminal.exe",
}

# ── Actions that require explicit user confirmation ──────────────────────
DANGEROUS_ACTIONS: Set[str] = {
    "delete_file",
    "format_drive",
    "install_software",
    "modify_registry",
    "disable_security",
    "send_email",
    "execute_script",
    "admin_command",
    "shutdown",
    "restart",
}


class RPASandbox:
    """Sandboxed execution environment for RPA agent actions.

    Features:
        - Application whitelist (only allowed processes can be targeted)
        - Action audit logging to SQLite
        - Dangerous action approval gate
        - File system boundary enforcement
    """

    def __init__(
        self,
        db_path: str = "data/rpa_audit.db",
        whitelist: Optional[Set[str]] = None,
        allowed_paths: Optional[List[str]] = None,
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.whitelist = whitelist or DEFAULT_WHITELIST.copy()
        self.allowed_paths = [
            os.path.abspath(p)
            for p in (allowed_paths or [os.path.abspath(".")])
        ]
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}
        self._init_db()
        logger.info(
            "RPASandbox initialized: %d whitelisted apps, %d allowed paths",
            len(self.whitelist), len(self.allowed_paths),
        )

    def _init_db(self) -> None:
        """Initialize the audit log database."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rpa_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                application TEXT NOT NULL,
                action TEXT NOT NULL,
                params TEXT,
                result TEXT DEFAULT 'pending',
                blocked_reason TEXT,
                session_id TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rpa_audit_ts 
            ON rpa_audit_log(timestamp)
        """)
        conn.commit()
        conn.close()

    def is_app_whitelisted(self, app_name: str) -> bool:
        """Check if an application is in the allowed list.

        Args:
            app_name: Process name (e.g., 'chrome.exe').

        Returns:
            True if the application is whitelisted.
        """
        normalized = app_name.lower().strip()
        return normalized in {w.lower() for w in self.whitelist}

    def is_path_allowed(self, path: str) -> bool:
        """Check if a file path is within the allowed boundaries.

        Args:
            path: Absolute or relative file path.

        Returns:
            True if the path is within allowed directories.
        """
        try:
            abs_path = os.path.abspath(path)
            return any(abs_path.startswith(root) for root in self.allowed_paths)
        except Exception:
            return False

    def is_action_allowed(
        self,
        app_name: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if an RPA action is permitted.

        Args:
            app_name: Target application.
            action: Action type (e.g., 'click', 'type', 'delete_file').
            params: Action parameters for additional validation.

        Returns:
            True if the action is allowed.
        """
        # 1. App whitelist check
        if not self.is_app_whitelisted(app_name):
            self.log_action(
                app_name, action, params,
                result="blocked",
                blocked_reason=f"Application '{app_name}' not in whitelist",
            )
            logger.warning("RPA BLOCKED: App '%s' not whitelisted", app_name)
            return False

        # 2. Dangerous action check
        if action.lower() in DANGEROUS_ACTIONS:
            self.log_action(
                app_name, action, params,
                result="blocked",
                blocked_reason=f"Dangerous action '{action}' requires approval",
            )
            logger.warning(
                "RPA BLOCKED: Dangerous action '%s' on '%s' — requires approval",
                action, app_name,
            )
            return False

        # 3. File path boundary check (if params contain paths)
        if params:
            for key in ("path", "file", "target", "destination"):
                path_val = params.get(key)
                if path_val and isinstance(path_val, str):
                    if not self.is_path_allowed(path_val):
                        self.log_action(
                            app_name, action, params,
                            result="blocked",
                            blocked_reason=f"Path '{path_val}' outside allowed boundaries",
                        )
                        return False

        return True

    def request_approval(
        self,
        app_name: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        reason: str = "",
    ) -> str:
        """Request user approval for a dangerous action.

        Returns:
            Approval request ID.
        """
        approval_id = f"rpa_{int(time.time())}_{action}"
        self._pending_approvals[approval_id] = {
            "app_name": app_name,
            "action": action,
            "params": params,
            "reason": reason,
            "requested_at": datetime.now().isoformat(),
            "status": "pending",
        }
        logger.info(
            "RPA approval requested: %s — %s on %s",
            approval_id, action, app_name,
        )
        return approval_id

    def approve(self, approval_id: str) -> bool:
        """Approve a pending RPA action request."""
        if approval_id in self._pending_approvals:
            self._pending_approvals[approval_id]["status"] = "approved"
            return True
        return False

    def deny(self, approval_id: str) -> bool:
        """Deny a pending RPA action request."""
        if approval_id in self._pending_approvals:
            self._pending_approvals[approval_id]["status"] = "denied"
            return True
        return False

    def log_action(
        self,
        app_name: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        result: str = "executed",
        blocked_reason: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log an RPA action to the audit database.

        Args:
            app_name: Target application name.
            action: Action type performed.
            params: Action parameters.
            result: Outcome ('executed', 'blocked', 'failed').
            blocked_reason: Why the action was blocked (if applicable).
            session_id: Optional session identifier for grouping.
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                """INSERT INTO rpa_audit_log 
                   (timestamp, application, action, params, result, blocked_reason, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(),
                    app_name,
                    action,
                    json.dumps(params or {}),
                    result,
                    blocked_reason,
                    session_id,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to log RPA action: %s", e)

    def get_audit_log(
        self,
        limit: int = 100,
        app_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent audit log entries.

        Args:
            limit: Maximum number of entries to return.
            app_filter: Optional application name filter.

        Returns:
            List of audit log entries as dictionaries.
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            if app_filter:
                rows = conn.execute(
                    "SELECT * FROM rpa_audit_log WHERE application = ? ORDER BY id DESC LIMIT ?",
                    (app_filter, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM rpa_audit_log ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to read audit log: %s", e)
            return []

    def add_to_whitelist(self, app_name: str) -> None:
        """Add an application to the whitelist."""
        self.whitelist.add(app_name.lower().strip())
        logger.info("RPA whitelist updated: added '%s'", app_name)

    def remove_from_whitelist(self, app_name: str) -> None:
        """Remove an application from the whitelist."""
        self.whitelist.discard(app_name.lower().strip())
        logger.info("RPA whitelist updated: removed '%s'", app_name)

    def get_stats(self) -> Dict[str, Any]:
        """Return sandbox statistics for the dashboard."""
        return {
            "whitelisted_apps": sorted(self.whitelist),
            "allowed_paths": self.allowed_paths,
            "pending_approvals": len(self._pending_approvals),
            "status": "active",
        }
