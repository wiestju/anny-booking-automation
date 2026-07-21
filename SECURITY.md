# Security Policy

## Credential handling

This tool authenticates with your real university SSO account. To keep your
credentials safe:

- Store them **only** in a local `.env` file (git-ignored) or in your CI/host
  secret store. Never commit them.
- The repository's `.gitignore` excludes `.env`, `*.env`, `venv/`, and `logs/`.
  Double-check `git status` before committing.
- On a shared/hosted machine (e.g. a VPS), restrict the `.env` file permissions:
  `chmod 600 .env`.
- Rotate your password if you suspect it was exposed, and never paste real logs
  containing tokens/cookies into issues or PRs.

## Reporting a vulnerability

If you find a security issue **in this project**, please open a GitHub issue
marked `[security]`, or contact the maintainer privately via their GitHub
profile. Please do not include working credentials in the report.

## Third-party services

If you happen to discover a defect in **anny.eu** itself (not this project),
report it responsibly to anny via the contact/imprint on their website rather
than filing it here or exploiting it. This project intentionally stays within
normal, user-level usage of their API.
