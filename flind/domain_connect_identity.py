"""Flind-owned identity validation for Domain Connect.

Domain Connect templates must be independently registered with DNS providers.
A source-control JSON draft does not make a provider identity operational.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def valid_provider_id(value: str | None) -> bool:
    """Accept lowercase ASCII DNS domains, not URLs, ports, IPs or local hosts."""
    if not value or not isinstance(value, str) or len(value) > 253 or value.lower() != value:
        return False
    labels = value.split(".")
    if len(labels) < 2 or labels[-1].isdigit():
        return False
    return all(_LABEL.fullmatch(label) is not None for label in labels)


def allowed_flind_callback(uri: str, site_url: str) -> bool:
    """Allow redirects only back to this configured Flind web origin."""
    if not uri or not site_url or any(ch in uri for ch in ("\\", "\r", "\n", "\t")):
        return False
    try:
        destination, site = urlsplit(uri), urlsplit(site_url)
        if (
            not site.hostname
            or site.username or site.password
            or destination.username or destination.password
            or destination.fragment
            or destination.hostname != site.hostname
            or destination.scheme != site.scheme
            or destination.netloc != site.netloc
            or destination.scheme not in ("http", "https")
            or (destination.scheme == "http" and site.hostname not in ("localhost", "127.0.0.1"))
            or not destination.path.startswith("/")
        ):
            return False
        _ = destination.port
        _ = site.port
    except ValueError:
        return False
    return True
