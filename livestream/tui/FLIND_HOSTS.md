# Flind Live terminal access

The Flind Live terminal client never selects an external cloud host automatically. A token belongs to the Flind deployment that issued it.

For local development, choose the local app origin explicitly:

```sh
go run ./tui --host http://localhost:8000
```

Only local loopback app origins derive the local event-stream origin `http://localhost:8010`. For an independently hosted Flind deployment, configure both origins:

```sh
go run ./tui --host https://flind.example --livestream-host https://live.flind.example
```

Replace the example origins with the HTTPS origins actually controlled by your deployment. The `--token` flag also requires `--host`, and remote installations require `--livestream-host`. HTTP is accepted only on loopback. Legacy third-party hostnames are rejected, even when they appear in a saved configuration or are specified explicitly.

Credentials are stored with restrictive permissions in `~/.flind/livestream.json`. No legacy credentials are imported from the previous upstream application's configuration folder. When changing deployments, authenticate again rather than reusing a token issued by a different server.

These protections do not establish a public Flind streaming service, production authentication safety, or release readiness. Use only with an owned deployment you trust.
