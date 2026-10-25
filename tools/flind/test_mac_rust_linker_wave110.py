"""Wave 110 — workspace Rust config must build on stock Apple Clang.

No compiler/linker substitution and no paid build service. Proves the config
does not force an uninstalled optional linker, and keeps Tokio/SQLx settings.
"""
from pathlib import Path
import platform
import os
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "rust" / ".cargo" / "config.toml"


class MacRustLinkerWave110(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = tomllib.loads(CONFIG.read_text())

    def test_tokio_unstable_remains_workspace_wide(self):
        self.assertEqual(self.config["build"]["rustflags"], ["--cfg", "tokio_unstable"])

    def test_default_macos_linker_not_overridden_by_build_config(self):
        self.assertFalse(any(
            "lld" in str(flag)
            for flag in self.config.get("build", {}).get("rustflags", [])
        ))

    def test_no_macos_target_forces_optional_lld_linker(self):
        for target, settings in self.config.get("target", {}).items():
            if "macos" in target or "darwin" in target:
                with self.subTest(target=target):
                    for flag in settings.get("rustflags", []):
                        self.assertNotIn("fuse-ld=lld", str(flag))
                        self.assertNotIn("ld64.lld", str(flag))

    def test_sqlx_offline_and_aws_entropy_guards_preserved(self):
        self.assertEqual(self.config["env"]["SQLX_OFFLINE"], "true")
        self.assertEqual(self.config["env"]["AWS_LC_SYS_NO_JITTER_ENTROPY"], "1")

    def test_mac_stock_clang_can_link_without_lld(self):
        if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
            self.skipTest("Native Apple Silicon test only")
        clang = subprocess.run(
            ["xcrun", "--find", "clang"],
            capture_output=True, text=True, timeout=7,
        )
        self.assertEqual(clang.returncode, 0)
        # Compiles/links a *standalone* Rust binary to a private temp dir
        # with the same cfg as workspace defaults, using stock Apple Clang.
        # This is not cargo check or a build of capture-rs.
        with tempfile.TemporaryDirectory(prefix="flind-rust-linker-") as work:
            source = Path(work) / "link_probe.rs"
            result = Path(work) / "link_probe"
            source.write_text('fn main() { println!("flind linker probe"); }')
            built = subprocess.run(
                ["rustc", "--cfg", "tokio_unstable", str(source), "-o", str(result)],
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(built.returncode, 0, built.stderr[-850:])
            executed = subprocess.run(
                [str(result)], capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(executed.returncode, 0)
            self.assertEqual(executed.stdout.strip(), "flind linker probe")

    def test_macos_sdk_cplusplus_headers_compile_and_link(self):
        if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
            self.skipTest("Native Apple Silicon test only")
        sdk = subprocess.run(
            ["xcrun", "--show-sdk-path"], capture_output=True, text=True, timeout=7,
        )
        self.assertEqual(sdk.returncode, 0)
        include = Path(sdk.stdout.strip()) / "usr/include/c++/v1"
        self.assertTrue((include / "iostream").is_file())
        with tempfile.TemporaryDirectory(prefix="flind-cxx-headers-") as work:
            source = Path(work) / "headers.cpp"
            target = Path(work) / "headers"
            source.write_text('#include <iostream>\nint main() { std::cout << "flind c++"; }\n')
            env = os.environ.copy()
            env["SDKROOT"] = sdk.stdout.strip()
            env["CPLUS_INCLUDE_PATH"] = str(include)
            built = subprocess.run(
                ["/usr/bin/g++", str(source), "-o", str(target)],
                capture_output=True, text=True, timeout=35, env=env,
            )
            self.assertEqual(built.returncode, 0, built.stderr[-850:])
            executed = subprocess.run([str(target)], capture_output=True, text=True, timeout=5)
            self.assertEqual(executed.returncode, 0)
            self.assertEqual(executed.stdout, "flind c++")

    def test_local_wrapper_uses_offline_cargo_and_explicit_sdk_headers(self):
        wrapper = ROOT / "tools/flind/check_capture_rust_macos_wave110.sh"
        source = wrapper.read_text()
        for expected in (
            'CPLUS_INCLUDE_PATH=', 'SDKROOT=', 'CARGO_NET_OFFLINE=true',
            'cargo check --locked --offline -p capture --lib --bin capture',
            'FLIND_RUST_ROOT',
        ):
            self.assertIn(expected, source)

    def test_settings_in_workspace_cargo_source_are_understood(self):
        source = CONFIG.read_text()
        self.assertIn("platform's default linker", source)
        self.assertNotIn('link-arg=-fuse-ld=lld', source)


if __name__ == "__main__":
    unittest.main()
