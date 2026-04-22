"""Security Manager and SSRF Protection Utility."""

import ipaddress
import logging
import socket
import os
from urllib.parse import urlparse
from typing import Optional, List

logger = logging.getLogger("ultron.core.security")

class SecurityManager:
    """Manages path allowlists and general security policies."""
    
    def __init__(self, **kwargs):
        # Load allowed roots from env or default to current workspace
        self.audit_dir = kwargs.get("audit_dir", "./data/audit")
        env_roots = os.getenv("ULTRON_ALLOWED_ROOTS", "")
        self.allowed_roots = [
            os.path.abspath(p.strip()) 
            for p in env_roots.split(",") 
            if p.strip()
        ]
        if not self.allowed_roots:
            self.allowed_roots = [os.path.abspath(".")]
            
        logger.info(f"SecurityManager initialized with roots: {self.allowed_roots}")

    def is_path_allowed(self, path: str) -> bool:
        """Checks if the given path is within the allowed root directories."""
        try:
            abs_path = os.path.abspath(path)
            for root in self.allowed_roots:
                if abs_path.startswith(root):
                    return True
            return False
        except Exception:
            return False

class SSRFGuard:
    """Prevents Server-Side Request Forgery by validating target URLs and IPs."""

    FORBIDDEN_NETWORKS = [
        "127.0.0.0/8",      # Localhost
        "10.0.0.0/8",       # Private
        "172.16.0.0/12",    # Private
        "192.168.0.0/16",   # Private
        "169.254.0.0/16",   # Link-local / Cloud Metadata
        "0.0.0.0/8",        # Broadcast
        "::1/128",          # IPv6 Localhost
        "fc00::/7",         # IPv6 Private
        "fe80::/10",        # IPv6 Link-local
    ]

    @staticmethod
    def is_safe_url(url: str) -> bool:
        """Validates if a URL is safe to fetch."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            # 1. Check if hostname is an IP
            try:
                ip = ipaddress.ip_address(hostname)
                return SSRFGuard.is_safe_ip(str(ip))
            except ValueError:
                # Not an IP, resolve it
                return SSRFGuard.is_safe_hostname(hostname)

        except Exception as e:
            logger.warning(f"URL safety check failed for {url}: {e}")
            return False

    @staticmethod
    def is_safe_ip(ip_str: str) -> bool:
        """Checks if an IP address belongs to a forbidden network."""
        try:
            ip = ipaddress.ip_address(ip_str)
            for network in SSRFGuard.FORBIDDEN_NETWORKS:
                if ip in ipaddress.ip_network(network):
                    return False
            return True
        except ValueError:
            return False

    @staticmethod
    def is_safe_hostname(hostname: str) -> bool:
        """Resolves hostname and checks resulting IP addresses."""
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for info in addr_info:
                ip = info[4][0]
                if not SSRFGuard.is_safe_ip(ip):
                    return False
            return True
        except Exception:
            return False

# Global instances
security_manager = SecurityManager()
ssrf_guard = SSRFGuard()
# Export
__all__ = ["SecurityManager", "SSRFGuard", "ssrf_guard", "security_manager"]
