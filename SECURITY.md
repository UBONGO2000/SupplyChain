# Security Policy

## Supported versions

The `main` branch is the only supported version.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Send a description and, if possible, a minimal reproduction to the maintainer:

- GitHub: [@UBONGO2000](https://github.com/UBONGO2000)

You should receive an answer within 72 hours. Please allow time for a fix before
any public disclosure.

## Security model

- Authentication is stateless: a signed JWT (HS256) is sent as a bearer token.
- Authorization is role-based (`admin`, `manager`, `staff`, `viewer`). Public
  registration always creates a read-only `viewer` account; roles are granted by
  an administrator only.
- A deactivated account is rejected on every request, even with a valid token.
- Secrets (`DATABASE_URL`, `SECRET_KEY`, bootstrap credentials) come from the
  environment. The application refuses to start with a missing or short
  `SECRET_KEY`; there is no fallback value in the repository.
- No default account and no default password is created by the application.

## Known limitations

These are accepted trade-offs, not oversights:

- **No login rate limiting.** A brute-force protection (per-IP and per-account)
  is planned; until then, use a strong unique password.
- **No immediate token revocation.** A signed token stays valid until it
  expires (30 minutes by default). Deactivating the account blocks it on the
  next request, but a leaked token cannot be invalidated before expiry.
- **No refresh-token rotation.** `create_refresh_token()` exists but is not
  exposed.

## Operational hygiene

- Dependencies are watched by Dependabot (see `.github/dependabot.yml`).
- `.env` is git-ignored and has never been committed.
- The four historical demo accounts shipped with published passwords. If an
  older database still holds them, run
  `python scripts/disable_default_accounts.py --apply`.
