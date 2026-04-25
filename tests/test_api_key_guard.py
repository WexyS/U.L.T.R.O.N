"""Tests for API Key Guard and RPA Sandbox."""

import pytest
from ultron.security.api_key_guard import (
    mask_api_key, APIKeyMaskingProcessor, _deep_mask, scan_env_for_leaked_keys,
)


class TestMaskApiKey:
    def test_openai_key(self):
        result = mask_api_key("sk-1234567890abcdefghijklmnopqrstuvwxyz")
        assert "****" in result
        assert result.startswith("sk-1")

    def test_groq_key(self):
        result = mask_api_key("gsk_abcdefghij1234567890")
        assert "****" in result

    def test_gemini_key(self):
        result = mask_api_key("AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert "****" in result

    def test_short_string_untouched(self):
        assert mask_api_key("hello") == "hello"

    def test_safe_value_untouched(self):
        assert mask_api_key("http://localhost:11434") == "http://localhost:11434"

    def test_empty_string(self):
        assert mask_api_key("") == ""

    def test_non_string(self):
        assert mask_api_key(123) == 123


class TestDeepMask:
    def test_nested_dict(self):
        data = {"config": {"api_key": "sk-1234567890abcdefghijklmnopqr"}}
        result = _deep_mask(data)
        assert "****" in result["config"]["api_key"]

    def test_list(self):
        data = ["sk-1234567890abcdefghijklmnopqr", "safe"]
        result = _deep_mask(data)
        assert "****" in result[0]
        assert result[1] == "safe"

    def test_depth_limit(self):
        # Create deeply nested structure
        data = {"level": 0}
        current = data
        for i in range(15):
            current["child"] = {"level": i + 1}
            current = current["child"]
        current["key"] = "sk-1234567890abcdefghijklmnopqr"
        # Should not crash
        result = _deep_mask(data)
        assert result is not None


class TestAPIKeyMaskingProcessor:
    def test_process_event(self):
        proc = APIKeyMaskingProcessor()
        event = {
            "event": "api_call",
            "api_key": "sk-1234567890abcdefghijklmnopqr",
            "url": "http://localhost:11434",
        }
        result = proc(None, None, event)
        assert "****" in result["api_key"]
        assert result["url"] == "http://localhost:11434"


class TestScanEnv:
    def test_detect_keys(self):
        env = {
            "GROQ_API_KEY": "gsk_testkey1234567890",
            "HOME": "/home/user",
            "OPENAI_API_KEY": "sk-test1234567890",
        }
        suspicious = scan_env_for_leaked_keys(env)
        assert "GROQ_API_KEY" in suspicious
        assert "OPENAI_API_KEY" in suspicious
        assert "HOME" not in suspicious
