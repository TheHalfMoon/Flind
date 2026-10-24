# Flind Mobile Studio

An unpublished Flind Studio Expo client for a locally controlled stack.

## Local stack

In the Flind checkout, once:

```bash
echo 'ALLOW_DEV_API_KEY_REVEAL=1' >> .env
echo 'SANDBOX_PROVIDER=docker' >> .env
flox activate -- bash -c "python manage.py setup_local_api_key"
```

Then restart the stack. The login screen posts email and password to `/api/login/`, reads the seeded local dev personal API key, and uses it as a bearer token from then on.

## Run

```bash
cd products/desktop
pnpm install
pnpm --filter @flind/mobile-studio ios     # first build
pnpm --filter @flind/mobile-studio start   # afterwards
```

The host lives in `src/config.ts`. Use your LAN IP instead of `localhost` on a real phone.

See [Flind Mobile Studio qualification limits](../../../../docs/flind/F3_MOBILE_STUDIO_NATIVE_IDENTITY_WAVE30.md). Do not publish or share an unqualified build.
