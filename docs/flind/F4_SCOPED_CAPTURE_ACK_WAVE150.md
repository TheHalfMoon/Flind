# Wave 150 — Do not checkpoint a capture without an SDK client

## Regression found after making Flind capture opt-in

Wave 149 correctly removed inherited public analytics project tokens and cloud hosts and made `get_client()` return `None` when no Flind-controlled regional destination exists.

However, the `raise_on_error=True` contract of `ph_scoped_capture()` previously **yielded an inert `ScopedCapture(None)`** when the SDK was absent. A real caller, `products/tasks/backend/logic/stream/budget_steer.py` (`BudgetSteerCapture.capture`), uses:

```python
with ph_scoped_capture(raise_on_error=True) as capture:
    capture(...)

redis.set(captured_key, "1", ex=...)
```

Silently returning a no-op from a strict capture context would write a durable Redis `captured` marker **without attempting any event delivery**, preventing retries. The previous removal of inherited endpoints makes this a realistic default configuration.

## Production fix

In `posthog/ph_client.py`, when `raise_on_error=True` and `get_client()` cannot construct an owner-controlled Flind analytics client, **raise `RuntimeError("Flind analytics capture is not configured")` before yielding**. The caller therefore cannot reach its capture-success Redis statement. The default `raise_on_error=False` remains a harmless no-op for optional fire-and-forget analytics without a configured destination.

Do not create a vendor SDK client or invent a first-party project token to satisfy this requirement.

## Executed verification (2026-10-26)

Downloaded the exact private GitHub PR-branch files into isolated Mac test fixture and ran `tools/flind/test_scoped_capture_ack_wave150.py` using the installed pinned Python 3.14.7 runtime. This test executes the **actual source-defined `ScopedCapture` class**, `ph_scoped_capture()` context manager and the production `BudgetSteerCapture.capture()` function, with a local stub Redis and fake client (no real DB, event, provider or network calls).

**4/4 PASS, exit 0:**

1. Strict scoped capture refuses missing analytics client **before yielding**.
2. Actual BudgetSteer path with no configured client throws and makes **zero Redis writes**.
3. Default non-strict capture remains a safe no-op.
4. Actual BudgetSteer path with fake configured Flind client records the synthetic event, shuts down the fake client and then writes exactly one Redis acknowledgement.

This is a focused source-backed unit qualification, not full Celery/Redis integration or durable provider delivery proof. The original Django/Celery and full app E2E tests remain blocked by missing partial/sparse source and real isolated product stack (issue #82). More source/SDK naming and endpoint migration remains issue #5. Repo private, inherited GitHub Actions disabled; no deploy/publish/paid services, legal attribution preserved.
