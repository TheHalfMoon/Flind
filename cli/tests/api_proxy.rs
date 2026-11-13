use std::fs;
use std::process::Command;

#[test]
fn api_forwards_all_arguments_to_the_script() {
    let dir = tempfile::tempdir().unwrap();
    let preloaded = dir.path().join("preloaded");
    let preload = dir.path().join("preload.cjs");
    fs::write(
        &preload,
        format!(
            "require('fs').writeFileSync({}, '')",
            serde_json::to_string(preloaded.to_str().unwrap()).unwrap()
        ),
    )
    .unwrap();
    let env_file = dir.path().join("node.env");
    fs::write(
        &env_file,
        format!("NODE_OPTIONS=--require={}\n", preload.display()),
    )
    .unwrap();
    let received = dir.path().join("received.json");
    let script = dir.path().join("api-cli.mjs");
    fs::write(
        &script,
        format!(
            "import {{ writeFileSync }} from 'node:fs'\nwriteFileSync({}, JSON.stringify(process.argv.slice(2)))\n",
            serde_json::to_string(received.to_str().unwrap()).unwrap()
        ),
    )
    .unwrap();

    let status = Command::new(env!("CARGO_BIN_EXE_posthog-cli"))
        .args(["api", "--env-file"])
        .arg(&env_file)
        .env("POSTHOG_API_CLI_PATH", &script)
        .env("POSTHOG_HOME", dir.path())
        .env("POSTHOG_CLI_HOST", "http://127.0.0.1:8000")
        .env_remove("POSTHOG_HOST")
        .env("NODE_OPTIONS", format!("--require={}", preload.display()))
        .status()
        .expect("run posthog-cli");

    assert!(status.success());
    let args: Vec<String> = serde_json::from_slice(&fs::read(&received).unwrap()).unwrap();
    assert_eq!(args, ["--env-file", env_file.to_str().unwrap()]);
    assert!(!preloaded.exists(), "the preload ran before the API tools");
}

#[test]
fn api_rejects_unowned_host_before_the_node_child_runs() {
    let dir = tempfile::tempdir().unwrap();
    let marker = dir.path().join("child-executed");
    let script = dir.path().join("api-cli.mjs");
    fs::write(
        &script,
        format!(
            "import {{ writeFileSync }} from 'node:fs'\nwriteFileSync({}, 'should-not-run')\n",
            serde_json::to_string(marker.to_str().unwrap()).unwrap(),
        ),
    )
    .unwrap();

    let output = Command::new(env!("CARGO_BIN_EXE_posthog-cli"))
        .args(["api", "tools"])
        .env("POSTHOG_API_CLI_PATH", &script)
        .env("POSTHOG_CLI_HOST", "https://us.posthog.com")
        .env("POSTHOG_API_KEY", "phx_synthetic_do_not_log")
        .env_remove("POSTHOG_HOST")
        .output()
        .unwrap();

    assert!(!output.status.success());
    assert!(
        !marker.exists(),
        "Node must not run with an inherited cloud API host"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("Flind API proxy rejected invalid"));
    assert!(!stderr.contains("phx_synthetic_do_not_log"));
}

#[test]
fn api_without_explicit_host_refuses_unqualified_embedded_defaults() {
    let output = Command::new(env!("CARGO_BIN_EXE_posthog-cli"))
        .args(["api", "tools"])
        .env_remove("POSTHOG_HOST")
        .env_remove("POSTHOG_CLI_HOST")
        .env_remove("POSTHOG_API_KEY")
        .env_remove("POSTHOG_CLI_API_KEY")
        .env_remove("POSTHOG_CLI_TOKEN")
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr)
        .contains("requires an explicit, approved instance host"));
}

#[test]
fn api_nested_host_override_is_denied_before_embedded_node_starts() {
    let dir = tempfile::tempdir().unwrap();
    let marker = dir.path().join("node-started");
    let script = dir.path().join("api-cli.mjs");
    fs::write(
        &script,
        format!(
            "import {{ writeFileSync }} from 'node:fs'\\nwriteFileSync({}, 'executed')\\n",
            serde_json::to_string(marker.to_str().unwrap()).unwrap()
        ),
    )
    .unwrap();

    let output = Command::new(env!("CARGO_BIN_EXE_posthog-cli"))
        .args([
            "--host",
            "http://127.0.0.1:8000",
            "api",
            "tools",
            "--host=https://us.posthog.com",
        ])
        .env("POSTHOG_API_CLI_PATH", &script)
        .env_remove("POSTHOG_HOST")
        .env_remove("POSTHOG_CLI_HOST")
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(
        !marker.exists(),
        "unqualified Node bundle must not execute on nested host override"
    );
    assert!(String::from_utf8_lossy(&output.stderr)
        .contains("rejected a nested server/config override"));
}

#[test]
fn api_conflicting_host_aliases_fail_before_launch() {
    let output = Command::new(env!("CARGO_BIN_EXE_posthog-cli"))
        .args(["--host", "https://flind.example", "api", "tools"])
        .env("POSTHOG_HOST", "https://other.example")
        .env_remove("POSTHOG_CLI_HOST")
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("rejected conflicting"));
}
