use anyhow::{Context, Result};
use inquire::{
    validator::{ErrorMessage, Validation},
    CustomUserError,
};
use posthog_rs::Event;
use reqwest::blocking::Client;
use std::{
    io::{self, IsTerminal},
    path::PathBuf,
    sync::{Mutex, OnceLock},
    thread::JoinHandle,
    time::Duration,
};
use tracing::debug;
use uuid::Uuid;

/**
 * Flind has not qualified an independently owned CLI telemetry destination.
 * Inherited posthog-rs defaults must never receive invocation IDs, API project
 * identifiers, command usage or error metadata, including on a failed command.
 * Keep this fail-closed until a separate reviewed, owned endpoint is available.
 */
pub fn external_telemetry_allowed() -> bool {
    false
}

use crate::{
    api::client::PHClient,
    utils::auth::{env_id_validator, get_token, host_validator, token_validator},
};

// I've decided in my infinite wisdom that global state is fine, actually.
pub static INVOCATION_CONTEXT: OnceLock<InvocationContext> = OnceLock::new();

pub struct InvocationContext {
    pub config: InvocationConfig,
    pub client: PHClient,
    pub is_terminal: bool,

    handles: Mutex<Vec<JoinHandle<()>>>,
}

struct TelemetryContext {
    invocation_id: String,
    command_name: Option<String>,
    env_id: Option<String>,
    is_terminal: bool,
}

static TELEMETRY_CONTEXT: OnceLock<Mutex<TelemetryContext>> = OnceLock::new();

fn telemetry_context() -> &'static Mutex<TelemetryContext> {
    TELEMETRY_CONTEXT.get_or_init(|| {
        Mutex::new(TelemetryContext {
            invocation_id: Uuid::now_v7().to_string(),
            command_name: None,
            env_id: None,
            is_terminal: io::stdout().is_terminal(),
        })
    })
}

pub fn set_telemetry_command_name(command_name: &str) {
    if let Ok(mut context) = telemetry_context().lock() {
        context.command_name = Some(command_name.to_string());
    }
}

fn set_telemetry_env_id(env_id: &str) {
    if let Ok(mut context) = telemetry_context().lock() {
        context.env_id = Some(env_id.to_string());
    }
}

/// Attaches the project id from the environment to telemetry, for commands that
/// never load stored credentials (notably `api` with env-var auth). Values that
/// don't look like a real project id are ignored so telemetry can never pick up
/// an arbitrary string from a misconfigured environment.
pub fn set_telemetry_env_id_from_environment() {
    const ENV_ID_ENV_VARS: &[&str] = &[
        "POSTHOG_CLI_PROJECT_ID",
        "POSTHOG_CLI_ENV_ID",
        "POSTHOG_PROJECT_ID",
    ];

    let Some(env_id) = ENV_ID_ENV_VARS
        .iter()
        .find_map(|name| std::env::var(name).ok().filter(|value| !value.is_empty()))
    else {
        return;
    };

    if !matches!(env_id_validator(&env_id), Ok(Validation::Valid)) {
        return;
    }

    set_telemetry_env_id(&env_id);
}

/// Whether this event is a panic from std's `print!`/`eprintln!` machinery
/// failing on a closed pipe. These fire when the reader of stdout/stderr goes
/// away mid-command; the writer fix in `main.rs` keeps them from aborting the
/// command, and dropping them here keeps the residual noise out of error
/// tracking so a broken pipe never self-reports as an issue.
fn is_broken_pipe_panic(event: &Event) -> bool {
    if event.event_name() != "$exception" {
        return false;
    }

    let Some(items) = event
        .properties()
        .get("$exception_list")
        .and_then(|list| list.as_array())
    else {
        return false;
    };

    items.iter().any(|item| {
        item.get("value")
            .and_then(|value| value.as_str())
            .is_some_and(|message| {
                message.contains("failed printing to std") && message.contains("Broken pipe")
            })
    })
}

fn telemetry_invocation_id() -> String {
    telemetry_context()
        .lock()
        .map(|context| context.invocation_id.clone())
        .unwrap_or_else(|_| "unknown".to_string())
}

pub fn current_invocation_id() -> String {
    telemetry_invocation_id()
}

/// Captures the `posthog cli command run` usage event without requiring an
/// `InvocationContext` — the `api` command usually runs without one, which left
/// it with no usage telemetry at all. Callers must join the handle before the
/// process exits so the event reaches the queue ahead of the final flush.
pub fn capture_command_run_without_context() -> JoinHandle<()> {
    if !external_telemetry_allowed() {
        return std::thread::spawn(|| {});
    }
    std::thread::spawn(|| {
        debug!("Capturing command run event");
        posthog_rs::capture(Event::new_anon("posthog cli command run"));
        debug!("Event queued successfully");
    })
}

fn telemetry_command_name() -> Option<String> {
    telemetry_context()
        .lock()
        .ok()
        .and_then(|context| context.command_name.clone())
}

pub fn current_telemetry_command_name() -> Option<String> {
    telemetry_command_name()
}

fn telemetry_env_id() -> Option<String> {
    telemetry_context()
        .lock()
        .ok()
        .and_then(|context| context.env_id.clone())
}

fn telemetry_is_terminal() -> bool {
    telemetry_context()
        .lock()
        .map(|context| context.is_terminal)
        .unwrap_or_else(|_| io::stdout().is_terminal())
}

pub fn context() -> &'static InvocationContext {
    INVOCATION_CONTEXT.get().expect("Context has been set up")
}

fn configured_api_host(
    override_host: Option<String>,
    saved_host: Option<String>,
) -> Result<String> {
    override_host.or(saved_host).context(
        "Flind CLI API host is not configured. Specify an approved --host or store a Flind instance host.",
    )
}

pub fn init_context(
    host: Option<String>,
    skip_ssl: bool,
    rate_limit: Option<usize>,
    env_file: Option<PathBuf>,
) -> Result<()> {
    let token = get_token(env_file)?;
    let config = InvocationConfig {
        api_key: token.token.clone(),
        host: configured_api_host(host, token.host)?,
        env_id: token.env_id.clone(),
        skip_ssl,
        rate_limit: rate_limit.unwrap_or(480),
    };

    config.validate()?;
    set_telemetry_env_id(&config.env_id);

    let client: PHClient = PHClient::from_config(config.clone())?;

    INVOCATION_CONTEXT.get_or_init(|| InvocationContext::new(config, client));

    Ok(())
}

#[derive(Clone)]
pub struct InvocationConfig {
    pub api_key: String,
    pub host: String,
    pub env_id: String,
    pub skip_ssl: bool,
    pub rate_limit: usize, // max number of requests per minute
}

impl InvocationConfig {
    pub fn validate(&self) -> Result<()> {
        fn handle_validation(
            validation: Result<Validation, CustomUserError>,
            context: &str,
        ) -> Result<()> {
            let validation = validation.map_err(|err| anyhow::anyhow!("{context}: {err}"))?;
            if let Validation::Invalid(ErrorMessage::Custom(msg)) = validation {
                anyhow::bail!("{context}: {msg:?}");
            }
            Ok(())
        }

        handle_validation(token_validator(&self.api_key), "Invalid Personal API key")?;
        handle_validation(host_validator(&self.host), "Invalid Host")?;
        handle_validation(env_id_validator(&self.env_id), "Invalid Environment ID")?;
        Ok(())
    }
}

impl InvocationContext {
    pub fn new(config: InvocationConfig, client: PHClient) -> Self {
        Self {
            config,
            client,
            is_terminal: io::stdout().is_terminal(),
            handles: Default::default(),
        }
    }

    pub fn build_http_client(&self) -> Result<Client> {
        let client = Client::builder()
            .danger_accept_invalid_certs(self.config.skip_ssl)
            .build()?;
        Ok(client)
    }

    /// Upload client: fails fast on unreachable hosts so retries can reroute to
    /// the fallback endpoint quickly. Downloads keep the default timeouts
    /// because they have no retry or fallback path, and a slow connect there is
    /// better than a failed one.
    pub fn build_upload_http_client(&self) -> Result<Client> {
        let client = Client::builder()
            .danger_accept_invalid_certs(self.config.skip_ssl)
            .connect_timeout(Duration::from_secs(5))
            .build()?;
        Ok(client)
    }

    pub fn capture_command_invoked(&self, command: &str) {
        set_telemetry_command_name(command);
        self.capture_event("posthog cli command run", Vec::new());
    }

    pub fn capture_event(&self, event_name: &str, props: Vec<(&str, serde_json::Value)>) {
        if !external_telemetry_allowed() {
            return;
        }
        let event_name = event_name.to_string();
        let props: Vec<(String, serde_json::Value)> =
            props.into_iter().map(|(k, v)| (k.to_string(), v)).collect();

        let handle = std::thread::spawn(move || {
            let mut event = Event::new_anon(event_name);

            for (key, value) in &props {
                event
                    .insert_prop(key, value)
                    .expect("Inserting prop succeeds");
            }

            debug!("Capturing event");
            posthog_rs::capture(event);
            debug!("Event queued successfully");
        });

        self.handles.lock().unwrap().push(handle);
    }

    pub fn finish(&self) {
        self.handles
            .lock()
            .unwrap()
            .drain(..)
            .for_each(|handle| handle.join().unwrap());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn exception_event(message: &str) -> Event {
        let mut event = Event::new_anon("$exception");
        event
            .insert_prop(
                "$exception_list",
                serde_json::json!([{ "type": "Panic", "value": message }]),
            )
            .unwrap();
        event
    }

    #[test]
    fn telemetry_stays_disabled_without_a_qualified_flind_endpoint() {
        assert!(!external_telemetry_allowed());
        // The API proxy has no InvocationContext, yet its usage hook must
        // remain a no-op and must not instantiate an upstream telemetry client.
        capture_command_run_without_context().join().unwrap();
    }

    #[test]
    fn api_host_never_defaults_to_inherited_ingestion_endpoint() {
        assert!(configured_api_host(None, None).is_err());
        assert_eq!(
            configured_api_host(Some("https://my.flind.example".into()), None).unwrap(),
            "https://my.flind.example"
        );
        assert_eq!(
            configured_api_host(None, Some("http://localhost:8000".into())).unwrap(),
            "http://localhost:8000"
        );
    }

    #[test]
    fn detects_broken_pipe_printing_panics() {
        assert!(is_broken_pipe_panic(&exception_event(
            "failed printing to stderr: Broken pipe (os error 32)"
        )));
        assert!(is_broken_pipe_panic(&exception_event(
            "failed printing to stdout: Broken pipe (os error 32)"
        )));
    }

    #[test]
    fn ignores_other_events() {
        assert!(!is_broken_pipe_panic(&exception_event(
            "index out of bounds"
        )));
        assert!(!is_broken_pipe_panic(&Event::new_anon(
            "posthog cli command run"
        )));
    }
}
