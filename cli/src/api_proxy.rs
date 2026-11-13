use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::{env, fs};

use inquire::validator::Validation;
use reqwest::Url;
use thiserror::Error;

use crate::error::CapturedError;
use crate::invocation_context::InvocationContext;
use crate::utils::auth::host_validator;
use crate::utils::homedir::posthog_home_dir_if_available;

const API_CLI_BUNDLE: &str = "posthog-api-cli.mjs";

include!(concat!(env!("OUT_DIR"), "/api_cli_bundle.rs"));

/// Which step of writing the embedded bundle to disk failed. Variant names are
/// sent to telemetry (they carry no paths or user data), so keep them stable.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MaterializeStep {
    CreateDir,
    Write,
    Canonicalize,
}

impl MaterializeStep {
    fn as_str(self) -> &'static str {
        match self {
            MaterializeStep::CreateDir => "create_dir",
            MaterializeStep::Write => "write",
            MaterializeStep::Canonicalize => "canonicalize",
        }
    }
}

#[derive(Error, Debug)]
pub enum ApiProxyError {
    #[error("POSTHOG_API_CLI_PATH is set but empty.")]
    ConfiguredPathEmpty,
    #[error("POSTHOG_API_CLI_PATH is set to `{path}`, but that file could not be found.")]
    ConfiguredPathMissing {
        path: String,
        #[source]
        source: io::Error,
    },
    #[error("POSTHOG_API_CLI_PATH is set to `{path}`, but it is not a file.")]
    ConfiguredPathNotAFile { path: String },
    #[error(
        "The Flind CLI was built without an independently qualified embedded API tool bundle. \
         The `api` command is disabled in this build; external JavaScript bundle fallbacks are \
         not permitted for releases."
    )]
    BundleNotEmbedded,
    #[error(
        "The Flind CLI could not locate a local writable home directory for the embedded API \
         tool bundle. Configure a secure CLI home directory; release builds cannot use \
         external script fallbacks."
    )]
    HomeDirUnavailable,
    #[error(
        "Failed to materialize the Flind embedded API tool bundle at `{path}`. Make the CLI \
         home directory writable. Release builds never fall back to an external script."
    )]
    MaterializeFailed {
        step: MaterializeStep,
        path: String,
        #[source]
        source: io::Error,
    },
    #[error("Failed to execute `node`. The `api` command needs Node.js installed and on PATH.")]
    NodeSpawnFailed {
        #[source]
        source: io::Error,
    },
}

impl ApiProxyError {
    /// Coarse failure class for telemetry. Never contains paths or user data.
    pub fn telemetry_kind(&self) -> &'static str {
        match self {
            ApiProxyError::ConfiguredPathEmpty
            | ApiProxyError::ConfiguredPathMissing { .. }
            | ApiProxyError::ConfiguredPathNotAFile { .. } => "configured_path_invalid",
            ApiProxyError::BundleNotEmbedded => "bundle_not_embedded",
            ApiProxyError::HomeDirUnavailable => "home_dir_unavailable",
            ApiProxyError::MaterializeFailed { .. } => "materialize_failed",
            ApiProxyError::NodeSpawnFailed { .. } => "node_spawn_failed",
        }
    }

    pub fn telemetry_step(&self) -> Option<&'static str> {
        match self {
            ApiProxyError::MaterializeFailed { step, .. } => Some(step.as_str()),
            _ => None,
        }
    }

    /// The underlying `io::ErrorKind` as a stable identifier (e.g. `PermissionDenied`).
    pub fn telemetry_io_error_kind(&self) -> Option<String> {
        let source = match self {
            ApiProxyError::ConfiguredPathMissing { source, .. } => source,
            ApiProxyError::MaterializeFailed { source, .. } => source,
            ApiProxyError::NodeSpawnFailed { source } => source,
            _ => return None,
        };
        Some(format!("{:?}", source.kind()))
    }
}

// This module canonicalizes through `dunce` because `std::fs::canonicalize`
// returns `\\?\`-prefixed verbatim paths on Windows, and Node cannot load a
// main script from such a path (it exits with `EISDIR: illegal operation on a
// directory, lstat 'C:'` before any script code runs).
fn canonicalize_file(path: &Path) -> Option<PathBuf> {
    let resolved = dunce::canonicalize(path).ok()?;
    if resolved.is_file() {
        Some(resolved)
    } else {
        None
    }
}

fn default_install_dir() -> Option<PathBuf> {
    posthog_home_dir_if_available()
}

fn embedded_bundle_path(install_dir: &Path) -> PathBuf {
    install_dir
        .join("api-cli")
        .join(env!("CARGO_PKG_VERSION"))
        .join(API_CLI_BUNDLE)
}

fn materialize_embedded_script(
    bundle: Option<&[u8]>,
    install_dir: Option<&Path>,
) -> Result<PathBuf, ApiProxyError> {
    let Some(bundle) = bundle else {
        return Err(ApiProxyError::BundleNotEmbedded);
    };
    let Some(install_dir) = install_dir else {
        return Err(ApiProxyError::HomeDirUnavailable);
    };
    let path = embedded_bundle_path(install_dir);
    let materialize_failed =
        |step: MaterializeStep, source: io::Error| ApiProxyError::MaterializeFailed {
            step,
            path: path.display().to_string(),
            source,
        };

    let parent = path
        .parent()
        .expect("embedded bundle path always has a parent directory");
    // Create and check the managed API directory *before* the version
    // directory. Otherwise create_dir_all(version) could follow an existing
    // API-directory symlink and create directories at an unrelated location.
    let api_dir = parent.parent().expect("bundle version has a parent");
    fs::create_dir_all(api_dir)
        .map_err(|source| materialize_failed(MaterializeStep::CreateDir, source))?;
    if fs::symlink_metadata(api_dir)
        .map_err(|source| materialize_failed(MaterializeStep::CreateDir, source))?
        .file_type()
        .is_symlink()
    {
        return Err(materialize_failed(
            MaterializeStep::CreateDir,
            io::Error::new(
                io::ErrorKind::InvalidData,
                "embedded API bundle directory is a symlink",
            ),
        ));
    }
    fs::create_dir_all(parent)
        .map_err(|source| materialize_failed(MaterializeStep::CreateDir, source))?;
    // Reject either version directory or the API bundle directory when
    // symlinked. The designated CLI home can itself be user-approved,
    // but neither of these newly managed descendants may redirect writes.
    // Installation ownership still matters against directory-swap races.
    for checked_dir in [
        parent,
        parent.parent().expect("bundle version has a parent"),
    ] {
        if fs::symlink_metadata(checked_dir)
            .map_err(|source| materialize_failed(MaterializeStep::CreateDir, source))?
            .file_type()
            .is_symlink()
        {
            return Err(materialize_failed(
                MaterializeStep::CreateDir,
                io::Error::new(
                    io::ErrorKind::InvalidData,
                    "embedded API bundle directory is a symlink",
                ),
            ));
        }
    }
    // Do not write a predictable final file: fs::write would follow a
    // preexisting symlink, potentially truncating another file. Persisting
    // a random same-directory temporary file replaces the directory entry.
    let mut staging = tempfile::NamedTempFile::new_in(parent)
        .map_err(|source| materialize_failed(MaterializeStep::Write, source))?;
    staging
        .write_all(bundle)
        .map_err(|source| materialize_failed(MaterializeStep::Write, source))?;
    staging
        .as_file()
        .sync_all()
        .map_err(|source| materialize_failed(MaterializeStep::Write, source))?;
    staging
        .persist(&path)
        .map_err(|error| materialize_failed(MaterializeStep::Write, error.error))?;
    let resolved = dunce::canonicalize(&path)
        .map_err(|source| materialize_failed(MaterializeStep::Canonicalize, source))?;
    if !resolved.is_file() {
        return Err(materialize_failed(
            MaterializeStep::Canonicalize,
            io::Error::new(
                io::ErrorKind::InvalidData,
                "materialized bundle is not a regular file",
            ),
        ));
    }
    Ok(resolved)
}

fn legacy_bundle_candidates(install_dir: Option<&Path>, development_dir: &Path) -> Vec<PathBuf> {
    let mut candidates = Vec::new();

    if let Some(install_dir) = install_dir {
        candidates.extend([
            install_dir.join("lib").join(API_CLI_BUNDLE),
            install_dir.join("cli/lib").join(API_CLI_BUNDLE),
            install_dir.join("api-cli").join(API_CLI_BUNDLE),
            install_dir.join(API_CLI_BUNDLE),
        ]);
    }

    candidates.push(development_dir.join("lib").join(API_CLI_BUNDLE));
    candidates
}

/// Resolves the bundle: prefer the embedded copy, fall back to legacy install
/// layouts, and if everything misses report the materialization failure (the
/// specific cause) rather than a generic not-found error.
fn resolve_script(
    bundle: Option<&[u8]>,
    install_dir: Option<&Path>,
    development_dir: &Path,
) -> Result<PathBuf, ApiProxyError> {
    let materialize_error = match materialize_embedded_script(bundle, install_dir) {
        Ok(resolved) => return Ok(resolved),
        Err(error) => error,
    };

    for candidate in legacy_bundle_candidates(install_dir, development_dir) {
        if let Some(resolved) = canonicalize_file(&candidate) {
            return Ok(resolved);
        }
    }

    Err(materialize_error)
}

/// Release binaries may only execute the API tool bundle embedded by the
/// same build. Legacy install paths and a configured JS file are useful for
/// isolated developer tests but are not a credential-safe release fallback.
fn resolve_release_script(
    bundle: Option<&[u8]>,
    install_dir: Option<&Path>,
) -> Result<PathBuf, ApiProxyError> {
    materialize_embedded_script(bundle, install_dir)
}

#[cfg(not(debug_assertions))]
fn find_script() -> Result<PathBuf, ApiProxyError> {
    resolve_release_script(EMBEDDED_API_CLI_BUNDLE, default_install_dir().as_deref())
}

/// Debug builds support injecting synthetic Node programs in test fixtures.
/// The release configuration above deliberately has no such code path.
#[cfg(debug_assertions)]
fn find_script() -> Result<PathBuf, ApiProxyError> {
    if let Some(path) = env::var_os("POSTHOG_API_CLI_PATH") {
        if path.is_empty() {
            return Err(ApiProxyError::ConfiguredPathEmpty);
        }
        let path = PathBuf::from(path);
        let resolved =
            dunce::canonicalize(&path).map_err(|source| ApiProxyError::ConfiguredPathMissing {
                path: path.display().to_string(),
                source,
            })?;
        if !resolved.is_file() {
            return Err(ApiProxyError::ConfiguredPathNotAFile {
                path: resolved.display().to_string(),
            });
        }
        return Ok(resolved);
    }

    resolve_script(
        EMBEDDED_API_CLI_BUNDLE,
        default_install_dir().as_deref(),
        Path::new(env!("CARGO_MANIFEST_DIR")),
    )
}

fn has_any_env(names: &[&str]) -> bool {
    names.iter().any(|name| env::var(name).is_ok())
}

fn inject_credentials(cmd: &mut Command, invocation_context: Option<&InvocationContext>) {
    let Some(invocation_context) = invocation_context else {
        return;
    };
    let config = &invocation_context.config;

    if !has_any_env(&[
        "POSTHOG_API_KEY",
        "POSTHOG_CLI_API_KEY",
        "POSTHOG_CLI_TOKEN",
    ]) {
        cmd.env("POSTHOG_CLI_API_KEY", &config.api_key);
    }

    if !has_any_env(&[
        "POSTHOG_PROJECT_ID",
        "POSTHOG_CLI_PROJECT_ID",
        "POSTHOG_CLI_ENV_ID",
        "POSTHOG_ORGANIZATION_ID",
        "POSTHOG_CLI_ORGANIZATION_ID",
    ]) {
        cmd.env("POSTHOG_CLI_PROJECT_ID", &config.env_id);
    }

    if !has_any_env(&["POSTHOG_HOST", "POSTHOG_CLI_HOST"]) {
        cmd.env("POSTHOG_CLI_HOST", &config.host);
    }
}

/// Never forward inherited analytics credentials or destinations to the
/// embedded Node CLI. This is not an outbound-network guarantee: the Node
/// bundle still needs an independent runtime egress audit before release.
fn isolate_inherited_analytics(cmd: &mut Command) {
    // A Node preload or alternate module search path can execute arbitrary
    // inherited JavaScript before our approved script receives API keys.
    cmd.env_remove("NODE_OPTIONS");
    cmd.env_remove("NODE_PATH");
    cmd.env_remove("POSTHOG_ANALYTICS_API_KEY");
    cmd.env_remove("POSTHOG_ANALYTICS_HOST");
    cmd.env_remove("POSTHOG_CLI_INVOCATION_ID");
}

/// Validate every possible Node API host before forwarding personal keys.
/// Resolve all aliases to a single origin to prevent the bundled Node tool
/// from silently prioritizing a different inherited provider destination.
/// No host means fail closed, including for metadata commands, because the
/// staged Node bundle has not passed a no-egress runtime audit.
fn approved_proxy_host(
    explicit_host: Option<&str>,
    legacy_host: Option<&str>,
    cli_host: Option<&str>,
    credential_host: Option<&str>,
) -> anyhow::Result<String> {
    let candidates = [
        ("--host", explicit_host),
        ("POSTHOG_HOST", legacy_host),
        ("POSTHOG_CLI_HOST", cli_host),
        ("stored CLI host", credential_host),
    ];
    for (label, value) in candidates {
        if let Some(value) = value {
            if !matches!(host_validator(value), Ok(Validation::Valid)) {
                anyhow::bail!("Flind API proxy rejected invalid {label}; use an explicitly approved Flind HTTPS origin or loopback HTTP");
            }
        }
    }
    let chosen = explicit_host
        .or(credential_host)
        .or(cli_host)
        .or(legacy_host)
        .ok_or_else(|| anyhow::anyhow!("Flind API proxy requires an explicit, approved instance host; no cloud default is allowed"))?;
    let chosen_origin = Url::parse(chosen)?.origin();
    for (label, value) in candidates {
        if let Some(value) = value {
            if Url::parse(value)?.origin() != chosen_origin {
                anyhow::bail!("Flind API proxy rejected conflicting {label}; remove conflicting host aliases before forwarding credentials");
            }
        }
    }
    Ok(chosen_origin.ascii_serialization())
}

/// Prevent the unqualified Node bundle's own command-line flags from
/// overriding the verified parent-level server origin or loading another
/// configuration file. The network egress of the bundle is still unqualified.
fn reject_nested_host_overrides(args: &[String]) -> anyhow::Result<()> {
    const FORBIDDEN: &[&str] = &[
        "--host",
        "--api-host",
        "--api-url",
        "--base-url",
        "--server-url",
        "--config",
        "--config-file",
    ];
    for arg in args {
        let flag = arg.split_once('=').map_or(arg.as_str(), |(name, _)| name);
        if FORBIDDEN.iter().any(|name| flag.eq_ignore_ascii_case(name)) {
            anyhow::bail!(
                "Flind API proxy rejected a nested server/config override. Set --host on the Flind CLI before api."
            );
        }
    }
    Ok(())
}

/// Runs the embedded Node API CLI. A non-zero child exit is returned as
/// `Ok(Some(code))` — not `process::exit` — so the caller can flush telemetry
/// and honor `--no-fail` before terminating with the same code.
pub fn run(
    args: Vec<String>,
    host_override: Option<String>,
    invocation_context: Option<&InvocationContext>,
) -> Result<Option<i32>, CapturedError> {
    // Do this before bundle materialization, Node execution, or credential
    // injection. In particular, the no-InvocationContext `api` route cannot
    // bypass hostname, TLS, vendor-domain or conflict validation.
    let approved_host = approved_proxy_host(
        host_override.as_deref(),
        env::var("POSTHOG_HOST").ok().as_deref(),
        env::var("POSTHOG_CLI_HOST").ok().as_deref(),
        invocation_context.map(|ctx| ctx.config.host.as_str()),
    )
    .map_err(CapturedError::from)?;
    reject_nested_host_overrides(&args).map_err(CapturedError::from)?;
    let script = find_script().map_err(|error| CapturedError::from(anyhow::Error::new(error)))?;
    let mut cmd = Command::new("node");
    cmd.arg("--");
    cmd.arg(script);
    cmd.args(args);
    cmd.env("POSTHOG_CLI_VERSION", env!("CARGO_PKG_VERSION"));
    inject_credentials(&mut cmd, invocation_context);
    isolate_inherited_analytics(&mut cmd);

    // The embedded Node CLI sees one validated host, never a mixture of
    // inherited alias/override values with ambiguous precedence.
    cmd.env_remove("POSTHOG_HOST");
    cmd.env("POSTHOG_CLI_HOST", approved_host);

    let status = cmd.status().map_err(|source| {
        CapturedError::from(anyhow::Error::new(ApiProxyError::NodeSpawnFailed {
            source,
        }))
    })?;

    if status.success() {
        Ok(None)
    } else {
        Ok(Some(status.code().unwrap_or(1)))
    }
}

#[cfg(test)]
mod tests {
    use std::ffi::OsString;
    use std::fs;
    use std::sync::Mutex;

    use super::*;

    static POSTHOG_HOME_ENV_LOCK: Mutex<()> = Mutex::new(());

    struct EnvVarGuard {
        name: &'static str,
        previous: Option<OsString>,
    }

    impl EnvVarGuard {
        fn set(name: &'static str, value: &Path) -> Self {
            let previous = env::var_os(name);
            env::set_var(name, value);
            Self { name, previous }
        }
    }

    impl Drop for EnvVarGuard {
        fn drop(&mut self) {
            match &self.previous {
                Some(value) => env::set_var(self.name, value),
                None => env::remove_var(self.name),
            }
        }
    }

    #[test]
    fn proxy_host_preflight_rejects_missing_unowned_and_conflicting_targets() {
        for (override_host, legacy_host, cli_host, stored_host) in [
            (None, None, None, None),
            (Some("https://us.posthog.com"), None, None, None),
            (None, None, Some("https://eu.posthog.com"), None),
            (None, Some("http://example.com"), None, None),
            (None, None, Some("http://localhost:8000/path"), None),
            (None, None, Some("https://user:secret@flind.example"), None),
            (
                Some("https://flind.example"),
                Some("https://other.example"),
                None,
                None,
            ),
            (
                None,
                Some("http://localhost:8010"),
                Some("http://127.0.0.1:8010"),
                None,
            ),
            (
                None,
                None,
                Some("https://example.invalid"),
                Some("http://localhost:8000"),
            ),
        ] {
            assert!(
                approved_proxy_host(override_host, legacy_host, cli_host, stored_host).is_err(),
                "proxy must reject hostless, inherited or conflicted configuration"
            );
        }
    }

    #[test]
    fn proxy_host_preflight_normalizes_matching_approved_origins() {
        assert_eq!(
            approved_proxy_host(
                Some("https://flind.example/"),
                None,
                Some("https://flind.example"),
                None
            )
            .unwrap(),
            "https://flind.example"
        );
        assert_eq!(
            approved_proxy_host(None, Some("http://127.0.0.1:8000"), None, None).unwrap(),
            "http://127.0.0.1:8000"
        );
        assert_eq!(
            approved_proxy_host(None, None, None, Some("https://my.flind.example:8443/")).unwrap(),
            "https://my.flind.example:8443"
        );
    }

    #[test]
    fn proxy_child_is_forced_to_a_single_approved_host() {
        let approved = approved_proxy_host(
            None,
            Some("https://flind.example"),
            Some("https://flind.example"),
            None,
        )
        .unwrap();
        let mut child = Command::new("node");
        child.env_remove("POSTHOG_HOST");
        child.env("POSTHOG_CLI_HOST", approved);
        let entries: Vec<_> = child.get_envs().collect();
        assert!(entries
            .iter()
            .any(|(name, value)| *name == "POSTHOG_HOST" && value.is_none()));
        assert!(entries.iter().any(|(name, value)| {
            *name == "POSTHOG_CLI_HOST" && value.is_some_and(|host| host == "https://flind.example")
        }));
    }

    #[test]
    fn nested_node_transport_and_config_flags_are_rejected_before_credentials() {
        for flag in [
            "--host",
            "--HOST=https://us.posthog.com",
            "--api-host",
            "--api-host=https://vendor.example",
            "--api-url",
            "--api-url=https://vendor.example",
            "--base-url",
            "--base-url=https://vendor.example",
            "--server-url",
            "--config",
            "--config-file=./untrusted.json",
        ] {
            let args = vec!["call".to_owned(), "some-tool".to_owned(), flag.to_owned()];
            assert!(
                reject_nested_host_overrides(&args).is_err(),
                "unqualified nested transport option: {flag}"
            );
        }
    }

    #[test]
    fn normal_agent_tool_arguments_and_payloads_still_pass() {
        for args in [
            vec!["tools", "--json"],
            vec!["info", "--json", "feature-flag-get-all"],
            vec![
                "call",
                "--json",
                "--dry-run",
                "feature-flag-get-all",
                r#"{"host":"https://my.flind.example"}"#,
            ],
            vec!["search", "host"],
        ] {
            let argv = args.iter().map(|s| s.to_string()).collect::<Vec<_>>();
            assert!(
                reject_nested_host_overrides(&argv).is_ok(),
                "ordinary agent arguments should pass: {argv:?}"
            );
        }
    }

    #[test]
    fn analytics_settings_are_explicitly_removed_from_node_child() {
        let mut child = Command::new("node");
        child.env("NODE_OPTIONS", "--require=/tmp/credential-hook.cjs");
        child.env("NODE_PATH", "/tmp/untrusted-modules");
        child.env("POSTHOG_ANALYTICS_API_KEY", "inherited-token");
        child.env("POSTHOG_ANALYTICS_HOST", "https://example.invalid");
        child.env("POSTHOG_CLI_INVOCATION_ID", "linked-session");
        child.env("POSTHOG_CLI_API_KEY", "user-api-key");
        isolate_inherited_analytics(&mut child);

        let entries: Vec<_> = child.get_envs().collect();
        for key in [
            "NODE_OPTIONS",
            "NODE_PATH",
            "POSTHOG_ANALYTICS_API_KEY",
            "POSTHOG_ANALYTICS_HOST",
            "POSTHOG_CLI_INVOCATION_ID",
        ] {
            assert!(
                entries
                    .iter()
                    .any(|(name, value)| *name == key && value.is_none()),
                "{key} must be removed from the Node child",
            );
        }
        assert!(entries.iter().any(|(name, value)| {
            *name == "POSTHOG_CLI_API_KEY" && value.is_some_and(|s| s == "user-api-key")
        }));
    }

    #[test]
    fn legacy_bundle_candidates_include_install_and_development_paths() {
        let install_dir = PathBuf::from("home").join(".posthog");
        let development_dir = PathBuf::from("repo").join("cli");

        let candidates = legacy_bundle_candidates(Some(&install_dir), &development_dir);

        assert_eq!(candidates[0], install_dir.join("lib").join(API_CLI_BUNDLE));
        assert_eq!(
            candidates[1],
            install_dir.join("cli/lib").join(API_CLI_BUNDLE)
        );
        assert_eq!(
            candidates.last(),
            Some(&development_dir.join("lib").join(API_CLI_BUNDLE))
        );
    }

    #[test]
    fn canonicalize_file_rejects_directories() {
        let temp_dir = tempfile::tempdir().expect("create temp dir");

        assert_eq!(canonicalize_file(temp_dir.path()), None);
    }

    #[test]
    fn default_install_dir_honors_posthog_home() {
        let _lock = POSTHOG_HOME_ENV_LOCK.lock().expect("lock POSTHOG_HOME");
        let temp_dir = tempfile::tempdir().expect("create temp dir");
        let _guard = EnvVarGuard::set("POSTHOG_HOME", temp_dir.path());

        assert_eq!(default_install_dir(), Some(temp_dir.path().to_path_buf()));
    }

    #[test]
    fn embedded_bundle_is_materialized_into_a_versioned_install_dir() {
        let temp_dir = tempfile::tempdir().expect("create temp dir");

        let resolved = materialize_embedded_script(Some(b"embedded bundle"), Some(temp_dir.path()))
            .expect("materialize embedded bundle");

        assert_eq!(
            resolved,
            dunce::canonicalize(
                temp_dir
                    .path()
                    .join("api-cli")
                    .join(env!("CARGO_PKG_VERSION"))
                    .join(API_CLI_BUNDLE),
            )
            .expect("canonicalize materialized bundle")
        );
        // Node rejects verbatim paths as a main script, so the resolved path
        // must stay in legacy `C:\...` form on Windows.
        #[cfg(windows)]
        assert!(!resolved.to_string_lossy().starts_with(r"\\?\"));
        assert_eq!(
            fs::read(resolved).expect("read materialized bundle"),
            b"embedded bundle"
        );
    }

    #[test]
    fn materialized_bundle_atomically_replaces_old_bytes_without_staging_leftovers() {
        let dir = tempfile::tempdir().expect("bundle test dir");
        let path = embedded_bundle_path(dir.path());
        fs::create_dir_all(path.parent().unwrap()).expect("create parent");
        fs::write(&path, b"stale script").expect("write stale version");
        let result =
            materialize_embedded_script(Some(b"approved embedded bytes"), Some(dir.path()))
                .expect("replace stale script");
        assert_eq!(result, dunce::canonicalize(&path).unwrap());
        assert_eq!(fs::read(&path).unwrap(), b"approved embedded bytes");
        let actual = fs::read_dir(path.parent().unwrap())
            .unwrap()
            .map(|entry| entry.unwrap().file_name())
            .collect::<Vec<_>>();
        assert_eq!(
            actual,
            vec![path.file_name().unwrap().to_os_string()],
            "no temp file may survive"
        );
    }

    #[cfg(unix)]
    #[test]
    fn materialized_bundle_replaces_file_symlink_without_touching_its_victim() {
        use std::os::unix::fs::symlink;
        let dir = tempfile::tempdir().expect("bundle test dir");
        let victim = dir.path().join("unrelated-sensitive-file");
        fs::write(&victim, b"preserve these bytes").expect("victim");
        let path = embedded_bundle_path(dir.path());
        fs::create_dir_all(path.parent().unwrap()).expect("version dir");
        symlink(&victim, &path).expect("symlink final file to unrelated file");
        let actual =
            materialize_embedded_script(Some(b"approved embedded bytes"), Some(dir.path()))
                .expect("install without following the symlink");
        assert_eq!(fs::read(&victim).unwrap(), b"preserve these bytes");
        assert_eq!(fs::read(actual).unwrap(), b"approved embedded bytes");
        assert!(!fs::symlink_metadata(&path)
            .unwrap()
            .file_type()
            .is_symlink());
    }

    #[cfg(unix)]
    #[test]
    fn materialized_bundle_refuses_symlinked_version_directory() {
        use std::os::unix::fs::symlink;
        let dir = tempfile::tempdir().expect("bundle test dir");
        let target_dir = dir.path().join("other-location");
        fs::create_dir_all(&target_dir).unwrap();
        let path = embedded_bundle_path(dir.path());
        fs::create_dir_all(path.parent().unwrap().parent().unwrap()).unwrap();
        symlink(&target_dir, path.parent().unwrap()).unwrap();
        let err = materialize_embedded_script(Some(b"approved embedded bytes"), Some(dir.path()))
            .expect_err("symlinked directory must fail closed");
        assert!(matches!(
            err,
            ApiProxyError::MaterializeFailed {
                step: MaterializeStep::CreateDir,
                ..
            }
        ));
        assert!(!target_dir.join(API_CLI_BUNDLE).exists());
    }

    #[cfg(unix)]
    #[test]
    fn materialized_bundle_refuses_symlinked_api_bundle_parent() {
        use std::os::unix::fs::symlink;
        let dir = tempfile::tempdir().expect("bundle test dir");
        let other = dir.path().join("external");
        fs::create_dir_all(&other).unwrap();
        let api_cli_parent = dir.path().join("api-cli");
        symlink(&other, &api_cli_parent).unwrap();
        let err = materialize_embedded_script(Some(b"approved embedded bytes"), Some(dir.path()))
            .expect_err("the API bundle parent must not be symlinked");
        assert!(matches!(
            err,
            ApiProxyError::MaterializeFailed {
                step: MaterializeStep::CreateDir,
                ..
            }
        ));
        assert!(
            !other.join(env!("CARGO_PKG_VERSION")).exists(),
            "must not even create the redirected version directory"
        );
    }

    #[test]
    fn release_script_refuses_unembedded_legacy_files_even_when_a_fallback_exists() {
        let dir = tempfile::tempdir().expect("release test dir");
        let lib = dir.path().join("lib");
        fs::create_dir_all(&lib).expect("create legacy lib");
        fs::write(lib.join(API_CLI_BUNDLE), b"malicious inherited JavaScript")
            .expect("legacy file");
        assert!(matches!(
            resolve_release_script(None, Some(dir.path())),
            Err(ApiProxyError::BundleNotEmbedded)
        ));
    }

    #[test]
    fn release_script_uses_exact_build_embedded_bytes() {
        let dir = tempfile::tempdir().expect("release test dir");
        let wanted = b"synthetic first-party Node tool";
        let resolved = resolve_release_script(Some(wanted), Some(dir.path()))
            .expect("materialize build bundle");
        assert_eq!(fs::read(&resolved).expect("read embedded tool"), wanted);
        assert_eq!(
            resolved,
            dunce::canonicalize(embedded_bundle_path(dir.path())).unwrap()
        );
    }

    #[test]
    fn embedded_bundle_is_ignored_when_it_was_not_built() {
        let temp_dir = tempfile::tempdir().expect("create temp dir");

        assert!(matches!(
            materialize_embedded_script(None, Some(temp_dir.path())),
            Err(ApiProxyError::BundleNotEmbedded)
        ));
    }

    #[test]
    fn missing_install_dir_reports_home_dir_unavailable() {
        assert!(matches!(
            materialize_embedded_script(Some(b"embedded bundle"), None),
            Err(ApiProxyError::HomeDirUnavailable)
        ));
    }

    #[test]
    fn materialize_failure_reports_step_and_io_error_kind() {
        let temp_dir = tempfile::tempdir().expect("create temp dir");
        // A file where the `api-cli` directory should go makes create_dir_all fail.
        fs::write(temp_dir.path().join("api-cli"), "not a directory").expect("write blocking file");

        let error = materialize_embedded_script(Some(b"embedded bundle"), Some(temp_dir.path()))
            .expect_err("materialization should fail");

        assert!(matches!(
            error,
            ApiProxyError::MaterializeFailed {
                step: MaterializeStep::CreateDir,
                ..
            }
        ));
        assert_eq!(error.telemetry_kind(), "materialize_failed");
        assert_eq!(error.telemetry_step(), Some("create_dir"));
        assert!(error.telemetry_io_error_kind().is_some());
    }

    #[test]
    fn resolve_script_falls_back_to_legacy_bundle_when_embedded_is_missing() {
        let temp_dir = tempfile::tempdir().expect("create temp dir");
        let install_dir = temp_dir.path().join("home").join(".posthog");
        let legacy_bundle = install_dir.join("lib").join(API_CLI_BUNDLE);
        fs::create_dir_all(legacy_bundle.parent().expect("legacy parent"))
            .expect("create legacy lib dir");
        fs::write(&legacy_bundle, "legacy").expect("write legacy bundle");

        let resolved = resolve_script(None, Some(&install_dir), Path::new("/nonexistent-dev-dir"))
            .expect("fall back to legacy bundle");

        assert_eq!(
            resolved,
            dunce::canonicalize(&legacy_bundle).expect("canonicalize legacy")
        );
    }

    #[test]
    fn resolve_script_reports_the_materialize_error_when_no_fallback_exists() {
        let temp_dir = tempfile::tempdir().expect("create temp dir");
        // Block materialization and provide no legacy bundle anywhere.
        fs::write(temp_dir.path().join("api-cli"), "not a directory").expect("write blocking file");

        let error = resolve_script(
            Some(b"embedded bundle"),
            Some(temp_dir.path()),
            Path::new("/nonexistent-dev-dir"),
        )
        .expect_err("resolution should fail");

        assert!(matches!(error, ApiProxyError::MaterializeFailed { .. }));
    }

    #[test]
    fn materialized_embedded_bundle_is_used_before_legacy_install() {
        let temp_dir = tempfile::tempdir().expect("create temp dir");
        let install_dir = temp_dir.path().join("home").join(".posthog");
        let legacy_bundle = install_dir.join("lib").join(API_CLI_BUNDLE);

        fs::create_dir_all(legacy_bundle.parent().expect("legacy parent"))
            .expect("create legacy lib dir");
        fs::write(&legacy_bundle, "legacy").expect("write legacy bundle");

        let resolved = materialize_embedded_script(Some(b"embedded bundle"), Some(&install_dir))
            .expect("materialize embedded bundle");

        assert_eq!(
            resolved,
            dunce::canonicalize(embedded_bundle_path(&install_dir))
                .expect("canonicalize embedded bundle")
        );
        assert_eq!(
            fs::read(resolved).expect("read materialized bundle"),
            b"embedded bundle"
        );
    }
}
