"""Ensure Flind's embedded Node API tool is never written through a symlink."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "cli/src/api_proxy.rs").read_text(encoding="utf-8")


class NodeBundleMaterializationTests(unittest.TestCase):
    def test_version_dir_cannot_be_symlink(self):
        body = SOURCE.split("fn materialize_embedded_script(", 1)[1].split("fn legacy_bundle_candidates(", 1)[0]
        self.assertRegex(body, r"for checked_dir in \[\s*parent,\s*parent\.parent\(\)")
        self.assertIn("fs::symlink_metadata(checked_dir)", body)
        self.assertIn(".is_symlink()", body)
        self.assertIn("embedded API bundle directory is a symlink", body)
        self.assertLess(body.index("fs::symlink_metadata(checked_dir)"), body.index("NamedTempFile::new_in"))
        self.assertLess(body.index("fs::symlink_metadata(api_dir)"), body.index("fs::create_dir_all(parent)"))

    def test_atomically_persist_private_staging_file_before_execution(self):
        body = SOURCE.split("fn materialize_embedded_script(", 1)[1].split("fn legacy_bundle_candidates(", 1)[0]
        self.assertIn("tempfile::NamedTempFile::new_in(parent)", body)
        self.assertIn(".write_all(bundle)", body)
        self.assertIn(".sync_all()", body)
        self.assertIn(".persist(&path)", body)
        self.assertNotIn("fs::write(&path, bundle)", body)
        self.assertLess(body.index(".sync_all()"), body.index(".persist(&path)"))
        self.assertLess(body.index(".persist(&path)"), body.index("dunce::canonicalize(&path)"))

    def test_rust_unit_tests_cover_stale_bytes_symlink_victim_and_symlinked_dir(self):
        for testname in (
            "materialized_bundle_atomically_replaces_old_bytes_without_staging_leftovers",
            "materialized_bundle_replaces_file_symlink_without_touching_its_victim",
            "materialized_bundle_refuses_symlinked_version_directory",
            "materialized_bundle_refuses_symlinked_api_bundle_parent",
        ):
            self.assertIn("fn " + testname + "()", SOURCE)
        self.assertIn("assert_eq!(fs::read(&victim).unwrap(), b\"preserve these bytes\")", SOURCE)
        self.assertRegex(SOURCE, r"assert!\(!fs::symlink_metadata\(&path\)\s*\.unwrap\(\)\s*\.file_type\(\)\s*\.is_symlink\(\)\);")

    def test_no_external_script_override_is_restored_in_release(self):
        release = SOURCE.split("#[cfg(not(debug_assertions))]\nfn find_script()", 1)[1].split("}\n", 1)[0]
        self.assertIn("resolve_release_script(EMBEDDED_API_CLI_BUNDLE", release)
        self.assertNotIn("POSTHOG_API_CLI_PATH", release)
        self.assertNotIn("resolve_script(", release)


if __name__ == "__main__":
    unittest.main()
