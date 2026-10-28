"""Wave220: safe actionable classes for unexpected first-party Django startup errors."""
import unittest

from tools.flind.qualify_sparse_django_registry_wave147 import safe_exception_class


class Wave220Diagnostics(unittest.TestCase):
    def test_unexpected_django_backend_error_is_actionable(self):
        InvalidCacheBackendError = type("InvalidCacheBackendError", (Exception,), {})
        error = InvalidCacheBackendError("password=secret://private-host")
        self.assertEqual(safe_exception_class(error), "InvalidCacheBackendError")

    def test_never_exposes_error_text_or_secrets(self):
        error = RuntimeError("SECRET_KEY=private-value, /Users/another-person")
        result = safe_exception_class(error)
        self.assertEqual(result, "RuntimeError")
        self.assertNotIn("private", result)
        self.assertNotIn("/Users", result)

    def test_rejects_non_identifier_exception_class(self):
        malformed = type("Danger/path\nsecret=value", (Exception,), {})
        self.assertEqual(
            safe_exception_class(malformed("password=sensitive")),
            "Unhandled first-party registry error",
        )

    def test_rejects_unbounded_exception_class_name(self):
        malformed = type("X" * 1000, (Exception,), {})
        self.assertEqual(
            safe_exception_class(malformed("secret")),
            "Unhandled first-party registry error",
        )


if __name__ == "__main__":
    unittest.main()
