"""Tests for RPA Sandbox."""

import pytest
from pathlib import Path
from ultron.security.rpa_sandbox import RPASandbox, DEFAULT_WHITELIST


@pytest.fixture
def sandbox(tmp_path):
    return RPASandbox(db_path=str(tmp_path / "test_rpa.db"))


class TestRPASandbox:
    def test_whitelisted_app_allowed(self, sandbox):
        assert sandbox.is_app_whitelisted("chrome.exe") is True

    def test_unknown_app_blocked(self, sandbox):
        assert sandbox.is_app_whitelisted("malware.exe") is False

    def test_action_allowed_for_whitelisted(self, sandbox):
        assert sandbox.is_action_allowed("chrome.exe", "click") is True

    def test_action_blocked_for_unknown_app(self, sandbox):
        assert sandbox.is_action_allowed("evil.exe", "click") is False

    def test_dangerous_action_blocked(self, sandbox):
        assert sandbox.is_action_allowed("chrome.exe", "delete_file") is False
        assert sandbox.is_action_allowed("chrome.exe", "shutdown") is False

    def test_path_allowed(self, sandbox):
        import os
        assert sandbox.is_path_allowed(os.path.abspath(".")) is True

    def test_path_outside_boundary(self, sandbox):
        assert sandbox.is_path_allowed("C:\\Windows\\System32") is False

    def test_audit_log_written(self, sandbox):
        sandbox.log_action("chrome.exe", "click", {"x": 100, "y": 200})
        log = sandbox.get_audit_log(limit=5)
        assert len(log) == 1
        assert log[0]["application"] == "chrome.exe"
        assert log[0]["action"] == "click"

    def test_blocked_action_logged(self, sandbox):
        sandbox.is_action_allowed("evil.exe", "click")
        log = sandbox.get_audit_log()
        assert len(log) == 1
        assert log[0]["result"] == "blocked"

    def test_add_to_whitelist(self, sandbox):
        sandbox.add_to_whitelist("custom_app.exe")
        assert sandbox.is_app_whitelisted("custom_app.exe") is True

    def test_remove_from_whitelist(self, sandbox):
        sandbox.remove_from_whitelist("chrome.exe")
        assert sandbox.is_app_whitelisted("chrome.exe") is False

    def test_approval_flow(self, sandbox):
        req_id = sandbox.request_approval("chrome.exe", "delete_file", reason="test")
        assert sandbox.approve(req_id) is True
        assert sandbox._pending_approvals[req_id]["status"] == "approved"

    def test_deny_flow(self, sandbox):
        req_id = sandbox.request_approval("chrome.exe", "shutdown")
        assert sandbox.deny(req_id) is True
        assert sandbox._pending_approvals[req_id]["status"] == "denied"

    def test_stats(self, sandbox):
        stats = sandbox.get_stats()
        assert "whitelisted_apps" in stats
        assert stats["status"] == "active"
