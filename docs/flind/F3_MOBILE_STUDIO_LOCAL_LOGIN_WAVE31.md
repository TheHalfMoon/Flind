# F3 Wave 31 — remove compiled development login defaults

## Prior behavior

The unpublished Mobile Studio app included fixed example local development
login credentials directly in its source configuration. The development
landing page offered a one-tap local sign-in using those baked-in values.
Although the button was guarded by React Native development mode, bundling
a default passphrase is unnecessary and masks the requirement to provision
an operator-controlled local stack.

## Implementation

- Remove the two compiled fixed development credential constants.
- Keep local sign-in visible only in development mode, but require the user
  to explicitly type their own local email and passphrase.
- Use secure text entry for the passphrase and clear it from component
  state after each local login attempt, successful or failed.
- Update the visible landing wordmark and local sign-in label to Flind.
- Preserve the existing local stack authentication endpoint and login state
  machine, without creating new test users, credentials or services.

## Evidence and limitations

- Source regression tests guard absence of bundled constants, credential
  entry, development-only UI and clearing in finally.
- TypeScript/TSX source parser zero errors; Flind Python 273/273 PASS;
  git diff --check PASS on macbook 2026-10-24.
- Mobile Studio dependencies are not installed on this Mac checkout, so no
  real React Native rendering, keyboard, password-manager, or login E2E
  qualification is claimed.
- Legacy seed data remains in backend/dev fixtures; removing the compiled
  mobile defaults does not migrate that data or qualify installed builds.

Repository private, Actions disabled, no publication/deployment, preserve
required attribution. Release remains NO-GO.
