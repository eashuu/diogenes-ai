"""
URL validation utilities to prevent SSRF attacks.

Validates URLs before crawling to block requests to private/internal
networks, cloud metadata endpoints, and other dangerous targets.
"""

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Blocked hostnames that should never be crawled
_BLOCKED_HOSTNAMES = frozenset({
    "metadata.google.internal",
    "metadata.google",
    "169.254.169.254",  # AWS/GCP/Azure metadata
    "metadata",
})

# Blocked TLDs that indicate internal/corporate networks
_BLOCKED_TLDS = frozenset({
    ".internal",
    ".local",
    ".corp",
    ".lan",
    ".intranet",
})

# Allowed schemes
_ALLOWED_SCHEMES = frozenset({"http", "https"})


def validate_url_for_ssrf(url: str) -> Optional[str]:
    """
    Validate a URL to prevent SSRF attacks.

    Returns None if the URL is safe, or an error message if blocked.

    Checks:
    - Scheme must be http or https
    - Hostname must not resolve to a private/reserved IP
    - Hostname must not be a known cloud metadata endpoint
    - Hostname must not be empty or localhost
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return f"Invalid URL: {url}"

    # Check scheme
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return f"Blocked scheme '{parsed.scheme}' — only http/https allowed"

    hostname = parsed.hostname
    if not hostname:
        return "URL has no hostname"

    # Check blocked hostnames
    hostname_lower = hostname.lower()
    if hostname_lower in _BLOCKED_HOSTNAMES:
        return f"Blocked hostname: {hostname}"

    # Check blocked TLDs (internal/corporate networks)
    for tld in _BLOCKED_TLDS:
        if hostname_lower.endswith(tld):
            return f"Blocked internal TLD: {hostname}"

    # Check if hostname is a raw IP address
    try:
        addr = ipaddress.ip_address(hostname)
        if _is_dangerous_ip(addr):
            return f"Blocked private/reserved IP: {hostname}"
        # Public IP — safe
        return None
    except ValueError:
        pass  # Not a raw IP — resolve it

    # Resolve hostname to IP and check
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _type, _proto, _canonname, sockaddr in infos:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
                if _is_dangerous_ip(addr):
                    logger.warning(
                        f"SSRF blocked: {hostname} resolves to private IP {ip_str}"
                    )
                    return f"Blocked: {hostname} resolves to private/reserved IP"
            except ValueError:
                continue
    except socket.gaierror:
        # DNS resolution failed — let the crawler handle the connection error
        return None

    return None


def _is_dangerous_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address is private, loopback, link-local, or otherwise reserved."""
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )
