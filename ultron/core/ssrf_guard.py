"""SSRF Guard — Protect against Server-Side Request Forgery.

Ensures that agents cannot access internal infrastructure, local services, 
or forbidden cloud metadata endpoints.
"""

import logging
import socket
import ipaddress
from urllib.parse import urlparse
from typing import List, Set, Optional

logger = logging.getLogger("ultron.security.ssrf")

class SSRFGuard:
    """Blocks requests to internal, private, or sensitive IP ranges."""

    def __init__(self, allowed_domains: Optional[List[str]] = None):
        self.allowed_domains = set(allowed_domains or [])
        self.blocked_ips = {
            ipaddress.ip_network("127.0.0.0/8"),    # Loopback
            ipaddress.ip_network("10.0.0.0/8"),     # Private
            ipaddress.ip_network("172.16.0.0/12"),  # Private
            ipaddress.ip_network("192.168.0.0/16"), # Private
            ipaddress.ip_network("169.254.169.254/32"), # AWS/GCP Metadata
            ipaddress.ip_network("::1/128"),        # IPv6 Loopback
            ipaddress.ip_network("fc00::/7"),       # IPv6 Unique Local
        }

    def is_url_safe(self, url: str) -> bool:
        """Check if a URL is safe to request."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or parsed.scheme not in ("http", "https"):
                logger.warning("SSRF: Blocked non-http/https scheme: %s", parsed.scheme)
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            # Check domain whitelist if active
            if self.allowed_domains and hostname not in self.allowed_domains:
                logger.warning("SSRF: Domain not in whitelist: %s", hostname)
                return False

            # Resolve IP and check against blocked ranges
            try:
                ip_address = socket.gethostbyname(hostname)
                addr = ipaddress.ip_address(ip_address)
                
                for blocked_range in self.blocked_ips:
                    if addr in blocked_range:
                        logger.warning("SSRF: Blocked internal IP access: %s (%s)", hostname, ip_address)
                        return False
            except Exception as e:
                logger.debug("SSRF: Could not resolve hostname %s: %s", hostname, e)
                # If we can't resolve it, we might still block it if it looks like an IP
                try:
                    addr = ipaddress.ip_address(hostname)
                    for blocked_range in self.blocked_ips:
                        if addr in blocked_range:
                            return False
                except ValueError:
                    pass

            return True
        except Exception as e:
            logger.error("SSRF Guard error: %s", e)
            return False

ssrf_guard = SSRFGuard()
