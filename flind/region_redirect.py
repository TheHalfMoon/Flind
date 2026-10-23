"""Validate first-party region redirects without trusting user-controlled cookies.

A cookie cannot opt its own hostname into the allowed set. Region hosts are
configured exclusively by the operator and are empty by default.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit


_HOST = re.compile(r"(?=.{1,253}\Z)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")


def valid_region_hostname(hostname: str | None) -> str | None:
    """Return a canonical DNS hostname or None (never an arbitrary URL)."""
    if not isinstance(hostname, str) or not hostname:
        return None
    host = hostname.lower()
    if host != hostname or not _HOST.fullmatch(host) or ".." in host:
        return None
    if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in host.split(".")):
        return None
    return host


def allowed_region_host(cookie_value: str | None, region_hosts: tuple[str, ...]) -> str | None:
    """Resolve an HTTPS instance cookie only if its host is explicitly allowlisted.

    No userinfo, port, path, query or fragment is allowed. The cookie is *never*
    sufficient to authorize a new destination.
    """
    if not cookie_value:
        return None
    allowed = {host for value in region_hosts if (host := valid_region_hostname(value)) is not None}
    if not allowed:
        return None
    try:
        url = urlsplit(cookie_value.strip('"'))
        if (
            url.scheme != "https"
            or url.username is not None
            or url.password is not None
            or url.port is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            return None
        hostname = valid_region_hostname(url.hostname)
    except (ValueError, TypeError):
        return None
    return hostname if hostname in allowed else None
