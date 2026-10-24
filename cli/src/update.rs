use std::path::{Path, PathBuf};

use anyhow::Result;

// No inherited release server is trusted by Flind. Updating is disabled
// until a first-party, authenticated release channel is implemented and
// verified; it must never download and run a vendor-owned shell script.

/// Classifies historical install layouts. This remains for migration tests;
/// it does not authorize an updater or contact a release server.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InstallMethod {
    /// Installed by install.sh, which leaves an install receipt. Ours to
    /// replace in place.
    Script,
    /// Installed by install.ps1. Also ours by ownership, but Windows will not
    /// let the installer overwrite the executable that is running it, so the
    /// user has to run the installer themselves.
    ScriptWindows,
    Homebrew,
    /// Anything under a node_modules: a global install, a project dependency,
    /// one pulled in by a plugin or SDK, or an npx cache. npm owns the file in
    /// every case, so they get one message. The path is carried because it is
    /// the part that tells someone which copy they just ran.
    Npm(PathBuf),
    Cargo,
    Unknown,
}

/// What to tell someone whose install we do not own.
pub enum Guidance {
    /// Run this command.
    Command(String),
    /// No single command applies; explain instead.
    Explain(String),
}

impl InstallMethod {
    /// Explains the historical install method; this never authorizes updates.
    pub fn guidance(&self) -> Option<Guidance> {
        match self {
            InstallMethod::Script => None,
            // Do not suggest executing an inherited installer, on Windows or elsewhere.
            InstallMethod::ScriptWindows => Some(Guidance::Explain(
                "Flind CLI updates are not yet available. Do not run inherited installers.".into(),
            )),
            InstallMethod::Homebrew | InstallMethod::Cargo => Some(Guidance::Explain(
                "Flind CLI packages have not been released through this package manager.".into(),
            )),
            InstallMethod::Npm(path) => Some(Guidance::Explain(format!(
                "this copy is managed by npm, at\n\n    {}\n\n\
                 No verified Flind CLI package is published. Do not update from a vendor registry.",
                path.display()
            ))),
            InstallMethod::Unknown => Some(Guidance::Explain(
                "No independently published Flind CLI update channel is configured.".into(),
            )),
        }
    }
}

/// The prefix the install script recorded as this install's home, if a receipt
/// exists and names one.
///
/// Presence of a receipt is not enough on its own. It describes whatever the
/// script installed last, which may be a different binary from the one running:
/// a developer's debug build, or a copy since replaced by a package manager.
/// Updating on that basis runs the installer over an install the caller is not
/// using.
fn receipt_install_prefix() -> Option<PathBuf> {
    let raw = std::fs::read_to_string(receipt_path()?).ok()?;
    let receipt: serde_json::Value = serde_json::from_str(&raw).ok()?;
    receipt["install_prefix"].as_str().map(PathBuf::from)
}

/// Where the install receipt lives, following the same search order the
/// generated installer writes it in.
fn receipt_path() -> Option<PathBuf> {
    // Both generated installers try XDG_CONFIG_HOME first. install.ps1 falls
    // back to LOCALAPPDATA, install.sh to ~/.config. Checking only LOCALAPPDATA
    // on Windows would miss a script install made with XDG_CONFIG_HOME set.
    let home = std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| {
            if cfg!(windows) {
                std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
            } else {
                dirs::home_dir().map(|h| h.join(".config"))
            }
        })?;
    Some(home.join("posthog-cli").join("posthog-cli-receipt.json"))
}

/// Classify this binary by where it actually lives on disk.
///
/// Path wins over the receipt on purpose. A machine can carry several installs
/// at once, and a receipt left by an earlier install.sh run says nothing about
/// the binary currently executing. Trusting it first would "update" a copy that
/// is not the one on PATH, and report success having changed nothing.
pub fn detect_install_method() -> InstallMethod {
    // The rule guards against trusting current_exe for a security decision.
    // This one is not: it picks which message to print, and whether to run the
    // official installer over the caller's own install. A caller who forges the
    // path gets their own CLI reinstalled from an inherited release host, which is
    // what the command does anyway. No privilege boundary and no other user is
    // involved.
    // nosemgrep: rust.lang.security.current-exe.current-exe
    let Ok(exe) = std::env::current_exe() else {
        return InstallMethod::Unknown;
    };
    // canonicalize, not read_link: Homebrew's symlinks are relative
    // (../Cellar/...), so a single read_link never matches an absolute prefix.
    let resolved = std::fs::canonicalize(&exe).unwrap_or(exe);
    // Owned by the script only when the receipt's prefix actually contains this
    // binary, so a receipt left by another install cannot claim it.
    let owned_by_script = receipt_install_prefix()
        .and_then(|prefix| std::fs::canonicalize(prefix).ok())
        .is_some_and(|prefix| resolved.starts_with(prefix));
    classify_path(&resolved, owned_by_script)
}

fn classify_path(resolved: &Path, owned_by_script: bool) -> InstallMethod {
    let has = |needle: &str| {
        resolved
            .components()
            .any(|c| c.as_os_str().to_string_lossy() == needle)
    };

    if has("Cellar") {
        return InstallMethod::Homebrew;
    }
    // The npm bin entry is a JS shim, so every npm case resolves to
    // run-posthog-cli.js inside node_modules rather than to a binary. Which
    // node_modules it is decides what the user should do about it.
    // Global, project dependency, plugin or SDK dependency, and npx cache all
    // land here. Telling them apart was tried and dropped: the layouts differ
    // per platform and per package manager, and npm owns the file either way,
    // so a wrong guess would send someone to the wrong copy.
    if has("node_modules") {
        return InstallMethod::Npm(resolved.to_path_buf());
    }
    if resolved
        .parent()
        .is_some_and(|p| p.ends_with(Path::new(".cargo").join("bin")))
    {
        return InstallMethod::Cargo;
    }
    if owned_by_script {
        return if cfg!(windows) {
            InstallMethod::ScriptWindows
        } else {
            InstallMethod::Script
        };
    }
    InstallMethod::Unknown
}

pub fn update() -> Result<()> {
    // Fail before URL resolution, install-method detection, network I/O or
    // invoking a shell. A future updater must verify Flind-owned releases.
    anyhow::bail!(
        "Flind CLI self-update is disabled until a verified Flind release channel is available."
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn self_update_fails_closed_without_a_release_channel() {
        let message = update().unwrap_err().to_string();
        assert!(message.contains("Flind CLI self-update is disabled"));
    }

    #[test]
    fn classifies_install_layouts() {
        // Paths measured on a machine carrying several installs at once.
        // The flag is varied because it is the other input. It means "the
        // receipt's install_prefix contains this binary", not "a receipt
        // exists", so a debug build or a package-manager copy cannot be claimed
        // by a receipt left behind by an earlier install.sh run.
        let npm_plugin =
            "/w/app/node_modules/@posthog/vite-plugin/node_modules/@posthog/cli/run-posthog-cli.js";
        let cases: &[(&str, bool, InstallMethod)] = &[
            // Homebrew symlinks are relative, so this is what breaks if
            // canonicalize is ever swapped back to read_link.
            (
                "/opt/homebrew/Cellar/posthog-cli/0.18.5/bin/posthog-cli",
                true,
                InstallMethod::Homebrew,
            ),
            (
                "/usr/local/Cellar/posthog-cli/0.18.5/bin/posthog-cli",
                false,
                InstallMethod::Homebrew,
            ),
            // Global, npx cache and a plugin's nested copy are all npm's to
            // update. Re-splitting them on a path heuristic would send the last
            // two to a copy they never ran.
            (
                "/Users/x/.nvm/versions/node/v26.2.0/lib/node_modules/@posthog/cli/run-posthog-cli.js",
                true,
                InstallMethod::Npm(PathBuf::from(
                    "/Users/x/.nvm/versions/node/v26.2.0/lib/node_modules/@posthog/cli/run-posthog-cli.js",
                )),
            ),
            (
                "/Users/x/.npm/_npx/6d80974bf710451e/node_modules/@posthog/cli/run-posthog-cli.js",
                true,
                InstallMethod::Npm(PathBuf::from(
                    "/Users/x/.npm/_npx/6d80974bf710451e/node_modules/@posthog/cli/run-posthog-cli.js",
                )),
            ),
            (npm_plugin, true, InstallMethod::Npm(PathBuf::from(npm_plugin))),
            ("/Users/x/.cargo/bin/posthog-cli", true, InstallMethod::Cargo),
            // Only a binary living under the receipt's own prefix is ours to
            // update in place.
            (
                "/Users/x/.posthog/posthog-cli",
                true,
                InstallMethod::Script,
            ),
            (
                "/Users/x/.posthog/posthog-cli",
                false,
                InstallMethod::Unknown,
            ),
        ];

        for (path, owned, expected) in cases {
            assert_eq!(
                classify_path(Path::new(path), *owned),
                *expected,
                "{path} (owned: {owned})"
            );
        }
    }

    #[test]
    fn only_a_script_install_updates_itself() {
        assert!(InstallMethod::Script.guidance().is_none());
        for method in [
            // Owned by us, but Windows cannot replace a running executable, so
            // it still has to hand the user a command.
            InstallMethod::ScriptWindows,
            InstallMethod::Homebrew,
            InstallMethod::Npm(PathBuf::from("/w/app/node_modules/x")),
            InstallMethod::Cargo,
            InstallMethod::Unknown,
        ] {
            assert!(method.guidance().is_some(), "{method:?}");
        }
    }
}
