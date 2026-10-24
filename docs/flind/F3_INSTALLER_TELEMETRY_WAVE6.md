# Flind F3 Wave 6 — installer domain-telemetry isolation

## Risk
The imported Go hobby installer created a telemetry client at package
initialization using a source-project cloud ingest URL and a hardcoded project
API key. During installation it automatically submitted the installation
domain as both the distinct ID and an event property at start and completion.

This is incompatible with an independently operated, locally deployed Flind
installer and could disclose operators' deployment domains.

## Implementation
- Remove the vendor telemetry client module and its initialization.
- Remove both hidden telemetry steps from the installer flow.
- Remove the deferred telemetry close call from the entrypoint.
- Remove the imported analytics dependency from this installer's go.mod and
  tidy go.sum only using Go's dependency resolver.
- Preserve the existing setup, git, deployment and logging steps.

## Verification
- `go test ./core` validates the real installer core module.
- `go test ./...` is required to qualify the entire binary (may need fetching
  public Go dependencies not present in an offline module cache).
- Added Go runtime regression that inspects all installation step names.
- Added standard-library Python source guards so the domain telemetry path
  cannot accidentally be reintroduced by future copy-first migrations.

This change does not qualify other Go utilities, Rust CLI remote API/upgrade
functions, setup scripts or broader external network egress. Separately audit
those services and retain the required third-party licenses/provenance. No
release until application and distribution tests pass.
