"""Tests for SSRF Guard v2."""

import pytest
from unittest.mock import patch
from ultron.core.ssrf_guard import SSRFGuard


@pytest.fixture
def guard():
    return SSRFGuard()


class TestSSRFGuard:
    def test_safe_url(self, guard):
        safe, _ = guard.check_url("https://example.com")
        assert safe is True

    def test_block_private_ip_127(self, guard):
        safe, reason = guard.check_url("http://127.0.0.1:8080")
        assert safe is False
        assert "forbidden" in reason.lower() or "127" in reason

    def test_block_private_ip_10(self, guard):
        safe, _ = guard.check_url("http://10.0.0.1/admin")
        assert safe is False

    def test_block_private_ip_192(self, guard):
        safe, _ = guard.check_url("http://192.168.1.1")
        assert safe is False

    def test_block_metadata_endpoint(self, guard):
        safe, _ = guard.check_url("http://169.254.169.254/latest/meta-data/")
        assert safe is False

    def test_block_non_http_scheme(self, guard):
        safe, reason = guard.check_url("ftp://example.com/file")
        assert safe is False
        assert "scheme" in reason.lower()

    def test_block_file_scheme(self, guard):
        safe, _ = guard.check_url("file:///etc/passwd")
        assert safe is False

    def test_no_hostname(self, guard):
        safe, _ = guard.check_url("http://")
        assert safe is False

    def test_ipv6_loopback(self, guard):
        safe, _ = guard.check_url("http://[::1]:8080")
        assert safe is False

    def test_blocked_hostname(self, guard):
        safe, _ = guard.check_url("http://metadata.google.internal")
        assert safe is False

    def test_dangerous_port_ssh(self, guard):
        safe, reason = guard.check_url("http://example.com:22")
        assert safe is False
        assert "port" in reason.lower()

    def test_dangerous_port_mysql(self, guard):
        safe, _ = guard.check_url("http://example.com:3306")
        assert safe is False

    def test_backward_compat_is_url_safe(self, guard):
        assert guard.is_url_safe("https://google.com") is True
        assert guard.is_url_safe("http://127.0.0.1") is False

    def test_domain_whitelist(self):
        guard = SSRFGuard(allowed_domains={"api.example.com"})
        safe, _ = guard.check_url("https://api.example.com/v1")
        assert safe is True
        safe, _ = guard.check_url("https://evil.com")
        assert safe is False

    @patch("socket.getaddrinfo")
    def test_dns_rebinding_detection(self, mock_dns, guard):
        """Simulate DNS rebinding: first resolve safe, second resolve private."""
        mock_dns.side_effect = [
            [(2, 1, 6, '', ('93.184.216.34', 0))],   # First: safe IP
            [(2, 1, 6, '', ('127.0.0.1', 0))],        # Second: private IP
        ]
        safe, reason = guard.check_url("http://rebinding-test.example.com")
        assert safe is False
        assert "rebinding" in reason.lower()
