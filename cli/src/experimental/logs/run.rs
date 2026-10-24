use std::net::IpAddr;
use std::path::Path;
use std::thread::sleep;
use std::time::{Duration, Instant};

use anyhow::{bail, Context, Result};
use reqwest::blocking::Client;

use super::checkpoint::Checkpoint;
use super::config::LokiImportConfig;
use super::emit::{batch_records, Batch};
use super::loki::{Entry, LokiClient, Page, INSTANT_LIMIT};
use super::mapping::Mapper;
use super::retention::retention_cutoff;
use super::send::{backoff, classify, Disposition};
use super::shard::shards;

/// The intake rejects a personal API token, so the import takes the project write key. That key is
/// already public-facing, which keeps a long unattended run off the user's personal credential.
pub const PROJECT_KEY_VAR: &str = "POSTHOG_PROJECT_API_KEY";

const MAX_ATTEMPTS: u32 = 8;

/// Paces sending so an import cannot saturate the intake, which has no rate limiting of its own.
struct Pacer {
    per_second: u32,
    window_start: Instant,
    sent_in_window: u32,
}

impl Pacer {
    fn new(per_second: u32) -> Self {
        Self {
            per_second,
            window_start: Instant::now(),
            sent_in_window: 0,
        }
    }

    /// Sleeps out the rest of the current second once the allowance is spent, repeating while the
    /// carried debt still exceeds one second's worth.
    fn record(&mut self, records: u32) {
        self.sent_in_window = self.sent_in_window.saturating_add(records);

        while self.sent_in_window >= self.per_second {
            let elapsed = self.window_start.elapsed();
            if elapsed < Duration::from_secs(1) {
                sleep(Duration::from_secs(1) - elapsed);
            }
            self.window_start = Instant::now();
            // Subtract rather than reset, so a batch larger than the allowance is paid for over
            // the seconds that follow instead of being forgiven.
            self.sent_in_window = self.sent_in_window.saturating_sub(self.per_second);
        }
    }
}

#[derive(Default)]
struct ShardTally {
    records: u64,
    bytes: u64,
}

pub struct Importer<'a> {
    pub config: &'a LokiImportConfig,
    pub loki: &'a LokiClient,
    pub mapper: &'a Mapper,
    pub http: &'a Client,
    pub intake_url: String,
    pub project_key: String,
    pub checkpoint_path: &'a Path,
    /// The project's default logs retention. Each shard starts at the retention cutoff when it
    /// begins before it, because intake would drop the records before the cutoff.
    pub retention_days: Option<i64>,
}

pub fn project_key_from_env() -> Result<String> {
    resolve_project_key(std::env::var(PROJECT_KEY_VAR).ok())
}

/// Split from the environment read so the message can be tested without mutating process globals.
fn resolve_project_key(raw: Option<String>) -> Result<String> {
    match raw.filter(|key| !key.is_empty()) {
        Some(key) => Ok(key),
        None => bail!(
            "set {PROJECT_KEY_VAR} to the project API key for the project you are importing into. \
             The intake rejects a personal API token."
        ),
    }
}

impl Importer<'_> {
    pub fn run(&self) -> Result<()> {
        let mut checkpoint = Checkpoint::load(self.checkpoint_path)?;
        let width = self.config.tuning.shard.seconds();
        let mut pacer = Pacer::new(self.config.tuning.max_records_per_second.get());

        let from_ns = self
            .config
            .range
            .from
            .timestamp_nanos_opt()
            .context("range.from is outside the nanosecond range")?;
        let to_ns = self
            .config
            .range
            .to
            .timestamp_nanos_opt()
            .context("range.to is outside the nanosecond range")?;
        if checkpoint.reconcile_range(from_ns, to_ns) {
            eprintln!(
                "the configured range now starts earlier than the checkpoint covers, so previous \
                 progress was discarded and the whole range will be imported"
            );
        }

        for selector in &self.config.range.select {
            let windows = shards(
                self.config.range.from,
                self.config.range.to,
                width,
                checkpoint.resume_from(selector),
            );

            for window in windows {
                // Starts at the cutoff when the shard begins before it, so no record intake would
                // drop is sent. Rechecked per shard, because the cutoff moves forward during a run.
                let start = match self.retention_days {
                    Some(days) => window.start.max(retention_cutoff(days, chrono::Utc::now())),
                    None => window.start,
                };
                if start >= window.end {
                    continue;
                }
                let mut cursor = start
                    .timestamp_nanos_opt()
                    .context("shard start is outside the nanosecond range")?;
                let mut tally = ShardTally::default();

                loop {
                    cursor = match self.loki.query_page(selector, cursor, window.end)? {
                        Page::Last(entries) => {
                            self.send_entries(&entries, &mut pacer, &mut tally)?;
                            break;
                        }
                        Page::More { entries, resume_at } => {
                            // Loki answering with entries before the requested start would
                            // otherwise re-fetch and re-send the same page forever.
                            if resume_at <= cursor {
                                bail!(
                                    "Loki returned entries before the requested start for {selector}; \
                                     refusing to re-send the same page"
                                );
                            }
                            self.send_entries(&entries, &mut pacer, &mut tally)?;
                            resume_at
                        }
                        Page::Crowded(at) => {
                            if at < cursor {
                                bail!(
                                    "Loki returned entries before the requested start for {selector}; \
                                     refusing to re-send the same page"
                                );
                            }
                            let Some(instant) = self.loki.query_instant(selector, at)? else {
                                bail!(
                                    "{INSTANT_LIMIT} or more entries for {selector} share the \
                                     timestamp {at}, and Loki cannot page within one instant. \
                                     Narrow the selector, with more label matchers or a line \
                                     filter, so fewer entries share that timestamp"
                                );
                            };
                            self.send_entries(&instant, &mut pacer, &mut tally)?;
                            at + 1
                        }
                    };
                }

                // Only after every batch in the window is acknowledged, so a crash re-sends this
                // shard rather than skipping it.
                let end = window
                    .end
                    .timestamp_nanos_opt()
                    .context("shard end is outside the nanosecond range")?;
                checkpoint.complete_shard(selector, end, tally.records, tally.bytes);
                checkpoint.save(self.checkpoint_path)?;
            }
        }

        println!(
            "Imported {} records ({} bytes sent). Checkpoint: {}",
            checkpoint.records_sent,
            checkpoint.bytes_sent,
            self.checkpoint_path.display()
        );
        Ok(())
    }

    fn send_entries(
        &self,
        entries: &[Entry],
        pacer: &mut Pacer,
        tally: &mut ShardTally,
    ) -> Result<()> {
        let mapped: Vec<_> = entries.iter().map(|e| self.mapper.map(e)).collect();
        for batch in batch_records(&mapped, self.config.tuning.max_request_bytes) {
            self.send(&batch)?;
            pacer.record(batch.records as u32);
            tally.records += batch.records as u64;
            tally.bytes += batch.body.len() as u64;
        }
        Ok(())
    }

    fn send(&self, batch: &Batch) -> Result<()> {
        let mut last_transport_error = None;

        for attempt in 0..MAX_ATTEMPTS {
            let sent = self
                .http
                .post(&self.intake_url)
                .header("Content-Type", "application/json")
                .bearer_auth(&self.project_key)
                .body(batch.body.clone())
                .send();

            let disposition = match sent {
                Ok(response) => {
                    let retry_after = response
                        .headers()
                        .get(reqwest::header::RETRY_AFTER)
                        .and_then(|value| value.to_str().ok())
                        .map(str::to_string);
                    classify(response.status(), retry_after.as_deref(), attempt)
                }
                // A reset connection, a DNS blip or a client timeout is transient. Failing the
                // whole run on one costs a shard of duplicates when it restarts.
                Err(error) if error.is_timeout() || error.is_connect() => {
                    last_transport_error = Some(error.to_string());
                    Disposition::Retry(backoff(attempt))
                }
                Err(error) => {
                    return Err(error).context("failed to reach the configured Flind logs intake")
                }
            };

            match disposition {
                Disposition::Accepted => return Ok(()),
                Disposition::Permanent(message) => bail!(message),
                Disposition::Retry(wait) => {
                    // Sleeping before giving up wastes up to five minutes on a doomed run.
                    if attempt + 1 == MAX_ATTEMPTS {
                        break;
                    }
                    eprintln!(
                        "retrying in {}s (attempt {}/{MAX_ATTEMPTS})",
                        wait.as_secs(),
                        attempt + 1
                    );
                    sleep(wait);
                }
            }
        }

        match last_transport_error {
            Some(error) => bail!(
                "gave up after {MAX_ATTEMPTS} attempts against the logs intake; last error: {error}"
            ),
            None => bail!("gave up after {MAX_ATTEMPTS} attempts against the logs intake"),
        }
    }
}

/// The intake route, carrying the backfill window the range needs.
/// Construct the logs destination from an explicitly configured Flind host.
/// Never append a bearer-authenticated route to an unrelated vendor, a URL with
/// hidden path/query components, or an insecure public HTTP endpoint.
pub fn intake_url(host: &str, from: chrono::DateTime<chrono::Utc>) -> Result<String> {
    let mut base =
        reqwest::Url::parse(host).context("Flind logs intake requires an explicit URL")?;
    let hostname = base
        .host_str()
        .context("Flind logs intake URL has no hostname")?;
    let hostname = hostname.to_ascii_lowercase();
    let hostname = hostname.trim_end_matches('.');
    if hostname == "posthog.com" || hostname.ends_with(".posthog.com") {
        bail!("Flind logs intake must not send a project key to the inherited cloud provider");
    }
    let unbracketed = hostname.trim_start_matches('[').trim_end_matches(']');
    let loopback = hostname == "localhost"
        || hostname.ends_with(".localhost")
        || unbracketed
            .parse::<IpAddr>()
            .is_ok_and(|ip| ip.is_loopback());
    if !(base.scheme() == "https" || (base.scheme() == "http" && loopback)) {
        bail!("Flind logs intake requires HTTPS, except for loopback development hosts");
    }
    if !base.username().is_empty()
        || base.password().is_some()
        || base.path() != "/"
        || base.query().is_some()
        || base.fragment().is_some()
    {
        bail!("Flind logs intake host must be an origin without credentials, path, query, or fragment");
    }
    let days = (chrono::Utc::now() - from).num_days().max(1) + 1;
    base.set_path("/i/v1/logs");
    base.query_pairs_mut()
        .append_pair("backfill_days", &days.to_string());
    Ok(base.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{Duration, Utc};

    #[test]
    fn the_backfill_window_covers_the_oldest_record_in_the_range() {
        // Asking for exactly the age of the oldest record loses it to rounding, so the window is
        // one day wider than the range's age.
        let from = Utc::now() - Duration::days(540);

        let url = intake_url("https://flind.example", from).unwrap();

        assert!(url.contains("backfill_days=541"), "got {url}");
    }

    #[test]
    fn a_trailing_slash_on_the_host_does_not_double_up() {
        let url = intake_url("https://flind.example/", Utc::now() - Duration::days(1)).unwrap();

        assert!(
            url.starts_with("https://flind.example/i/v1/logs?"),
            "got {url}"
        );
    }

    #[test]
    fn intake_refuses_upstream_hosts_and_url_ambiguity() {
        let from = Utc::now() - Duration::days(1);
        for host in [
            "https://posthog.com",
            "https://us.i.posthog.com",
            "https://us.i.posthog.com.",
            "https://flind.example/path",
            "https://flind.example/?token=secret",
            "https://flind.example/#fragment",
            "https://user:password@flind.example",
            "https://posthog.com.attacker.example/path",
            "http://flind.example",
            "file:///tmp/logs",
            "ftp://flind.example",
        ] {
            // Only the attacker-lookalike *hostname* is permitted. The path
            // on that lookalike URL remains invalid on its own merits.
            assert!(intake_url(host, from).is_err(), "{host} should not qualify");
        }
    }

    #[test]
    fn intake_supports_explicit_tls_and_loopback_development() {
        let from = Utc::now() - Duration::days(1);
        for host in [
            "https://flind.example:8443",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://[::1]:8000",
        ] {
            let url = intake_url(host, from).unwrap();
            assert!(url.contains("/i/v1/logs?backfill_days="), "{url}");
        }
        assert!(intake_url("https://notposthog.com", from).is_ok());
    }

    #[test]
    fn a_missing_project_key_says_which_variable_to_set_and_why() {
        for (case, raw) in [("unset", None), ("set but empty", Some(String::new()))] {
            let error = resolve_project_key(raw).expect_err(case);

            let rendered = format!("{error:#}");
            assert!(rendered.contains(PROJECT_KEY_VAR), "{case}: {rendered}");
            assert!(
                rendered.contains("personal API token"),
                "{case}: {rendered}"
            );
        }
    }
}
