"""Flind-owned security.txt generation without inherited contacts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit


def security_txt_content(contact: str, expires: str, *, now: datetime | None = None) -> str | None:
    """Return a valid, current RFC 9116-style record or nothing.

    A contact is not inferred or invented: the operator must configure it.
    """
    if not isinstance(contact, str) or not isinstance(expires, str):
        return None
    if not contact or not expires or any(ch.isspace() for ch in contact):
        return None
    if any(ch in expires for ch in "\r\n\x00"):
        return None
    if contact.startswith("mailto:"):
        address = contact[7:]
        if address.count("@") != 1 or not all(address.split("@")) or "/" in address or "?" in address:
            return None
    elif contact.startswith("https://"):
        try:
            url = urlsplit(contact)
            if not url.hostname or url.username or url.password or url.fragment or url.port not in (None, 443):
                return None
        except ValueError:
            return None
    else:
        return None

    try:
        expiration = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except ValueError:
        return None
    if expiration.tzinfo is None or expiration.utcoffset() is None:
        return None
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or not (current < expiration <= current + timedelta(days=365)):
        return None
    return f"Contact: {contact}\nExpires: {expiration.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')}\n"
