"""Fail closed on CLI release builds when the Node API bundle is not embedded."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "cli/src/api_proxy.rs").read_text(encoding="utf8")
BUILD = (ROOT / "cli/build.rs").read_text(encoding="utf8")


class EmbeddedBundleOnlyReleaseTests(unittest.TestCase):
    def test_release_script_has_no_override_or_legacy_fallback(self):
        assert SOURCE.count("fn find_script() -> Result<PathBuf, ApiProxyError> {") == 2
        release = SOURCE.split("#[cfg(not(debug_assertions))]\nfn find_script()", 1)[1]
        release = release.split("}\n", 1)[0]
        self.assertIn("resolve_release_script(EMBEDDED_API_CLI_BUNDLE, default_install_dir().as_deref())", release)
        self.assertNotIn("POSTHOG_API_CLI_PATH", release)
        self.assertNotIn("resolve_script(", release)
        self.assertNotIn("legacy_bundle_candidates", release)
        self.assertNotIn("std::process::Command", release)

    def test_debug_override_is_kept_only_in_debug_builds(self):
        self.assertIn("#[cfg(debug_assertions)]\nfn find_script()", SOURCE)
        debug = SOURCE.split("#[cfg(debug_assertions)]\nfn find_script()", 1)[1]
        self.assertIn('env::var_os("POSTHOG_API_CLI_PATH")', debug)
        self.assertIn("resolve_script(", debug)
        self.assertIn("materialize_embedded_script(bundle, install_dir)", SOURCE)

    def test_release_helper_and_native_negative_synthetic_regression(self):
        self.assertRegex(SOURCE, r"fn resolve_release_script\(\s*bundle: Option<&\[u8\]>,\s*install_dir: Option<&Path>,\s*\)")
        self.assertIn("release_script_refuses_unembedded_legacy_files_even_when_a_fallback_exists", SOURCE)
        self.assertIn("Err(ApiProxyError::BundleNotEmbedded)", SOURCE)
        self.assertIn("release_script_uses_exact_build_embedded_bytes", SOURCE)
        self.assertIn("assert_eq!(fs::read(&resolved)", SOURCE)

    def test_build_embeds_source_exactly_and_absent_bundle_is_none(self):
        self.assertIn("include_bytes!", BUILD)
        self.assertIn("EMBEDDED_API_CLI_BUNDLE: Option<&[u8]> = None", BUILD)
        self.assertIn("lib/posthog-api-cli.mjs", BUILD)
        self.assertNotIn("releases.posthog.com", BUILD)

    def test_release_error_messages_never_offer_unqualified_bundle_workarounds(self):
        errors = SOURCE.split('pub enum ApiProxyError {', 1)[1].split('impl ApiProxyError {', 1)[0]
        self.assertIn('The Flind CLI was built without an independently qualified', errors)
        self.assertIn('release builds never fall back', errors.lower())
        self.assertNotIn('Reinstall posthog-cli from an official release', errors)
        self.assertNotIn('or set POSTHOG_API_CLI_PATH to a trusted bundle', errors)


if __name__ == "__main__":
    unittest.main()
