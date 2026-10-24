"""Flind browser instrumentation is opt-in and restricted to this instance.

No SaaS telemetry token or endpoint is shipped in the source. The bootstrap
keys are kept temporarily as a frontend protocol compatibility boundary.
"""
from __future__ import annotations


def browser_capture_context(
    *,
    e2e_testing: bool = False,
    self_capture: bool = False,
    e2e_token: str = "",
    self_token: str = "",
) -> dict[str, str]:
    """Return a same-origin browser capture bootstrap or an empty mapping.

    Test capture uses a dedicated fixture token, never an ambient self-capture
    account. Real self-capture requires an existing local team token. Ordinary
    Flind installs send no browser usage events unless they opt into self-capture.
    """
    token = e2e_token if e2e_testing else self_token if self_capture else ""
    if not isinstance(token, str) or not token.strip():
        return {}
    return {
        "js_posthog_api_key": token,
        "js_posthog_host": "",  # UI resolves to window.location.origin.
    }
