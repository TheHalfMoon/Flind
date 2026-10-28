"""Wave 221: the child Django runtime sees only owned first-party Python roots."""
import os
from pathlib import Path
import unittest

from tools.flind.qualify_sparse_django_registry_wave147 import registry_pythonpath


class WorkspaceProtoRegistryTests(unittest.TestCase):
    def test_exact_first_party_workspace_paths(self):
        root = Path("/tmp/flind-wave221-source")
        self.assertEqual(registry_pythonpath(root).split(os.pathsep), [
            str(root), str(root / "packages/personhog-proto")])

    def test_untrusted_parent_pythonpath_is_not_inherited(self):
        root = Path("/tmp/flind-wave221-source")
        previous = os.environ.get("PYTHONPATH")
        try:
            os.environ["PYTHONPATH"] = "/tmp/untrusted-imports"
            self.assertNotIn("/tmp/untrusted-imports", registry_pythonpath(root))
        finally:
            if previous is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = previous


if __name__ == "__main__":
    unittest.main()
