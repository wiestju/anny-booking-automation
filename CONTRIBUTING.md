# Contributing

Thanks for your interest in improving this project! Contributions of all sizes
are welcome — bug reports, docs, and especially **new university providers**.

## Development setup

```bash
git clone <your-fork>
cd anny-booking-automation
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"      # runtime + dev deps (pytest, ruff)
cp .env.example .env         # fill in your SSO credentials for manual testing
```

## Before opening a PR

```bash
ruff check .     # lint (and `ruff check --fix .` to auto-fix)
pytest           # run the test suite
```

Both run automatically in CI on every pull request. Please keep them green and
add tests for new logic (the pure helpers in `booking/selection.py` and
`utils/helpers.py` are the easiest to cover).

## Adding a new university (SSO provider)

Most contributions are new institutions. The auth layer is pluggable:

1. Create `auth/providers/<your_uni>.py` subclassing `SSOProvider`
   (see `auth/providers/kit.py` and `tum.py` for reference).
2. Implement `authenticate()` to return the SAML response HTML for your IdP.
3. Register it in `auth/providers/__init__.py`.
4. Set `SSO_PROVIDER=<your_uni>` in your `.env` and test a real login.

Please **do not** commit real credentials, cookies, or SAML payloads in tests or
fixtures — scrub them first.

## Style

- Ruff enforces formatting/imports (config in `pyproject.toml`).
- Keep the booking flow **calm**: no request storms, no pre-firing. See
  [DISCLAIMER.md](DISCLAIMER.md) — PRs that add aggressive spamming won't be merged.

## Reporting bugs

Open an issue with the steps to reproduce, your Python version, and the relevant
log lines (with any personal data redacted).
