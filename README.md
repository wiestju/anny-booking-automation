# 📚 Anny Booking Automation

[![Stars](https://img.shields.io/github/stars/wiestju/anny-booking-automation?style=flat-square)](https://github.com/wiestju/anny-booking-automation/stargazers)
[![Forks](https://img.shields.io/github/forks/wiestju/anny-booking-automation?style=flat-square)](https://github.com/wiestju/anny-booking-automation/network/members)
[![CI](https://github.com/wiestju/anny-booking-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/wiestju/anny-booking-automation/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/wiestju/anny-booking-automation?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://www.python.org/)

> ⭐ If this saves you the scramble for a study space — give it a star!

---

**Automatically reserve study spaces and library seats on [anny.eu](https://anny.eu)** — the
booking platform many university libraries use, including the **Karlsruhe Institute of
Technology (KIT)** and the **Technical University of Munich (TUM)**.

The tool logs in via your university's SAML Single Sign-On, then books a seat for you —
either the exact moment new slots are released, or whatever is free right now. It runs
unattended via GitHub Actions (no server needed), grabs your favorite seat first, and
books only what you could book by hand.

> 🇩🇪 **Für Studierende:** Dieses Tool reserviert automatisch Lernplätze in der
> Universitätsbibliothek auf anny.eu — pünktlich zur Freischaltung, mit deinem
> Lieblingsplatz zuerst. Unterstützt KIT, TUM und weitere anny-basierte Bibliotheken.

⚠️ **Please use it responsibly** — see the [DISCLAIMER](DISCLAIMER.md). It logs in as you and
reserves a single seat per time slot, exactly as you would by hand.

## 📋 Table of Contents

- [Features](#-features)
- [Supported Universities](#-supported-universities)
- [Quick Start](#-quick-start)
- [AI-Assisted Setup](#-ai-assisted-setup)
- [Configuration](#-configuration)
- [How booking works](#-how-booking-works)
- [Automated Scheduling](#-automated-scheduling)
- [Adding a New University](#-adding-a-new-university)
- [Development](#-development)
- [Help & Support](#-help--support)
- [License](#-license)

## ✨ Features

- **Auto-discovery** — finds every bookable floor/building for your account after login; no manual API research.
- **Two booking strategies** — book the instant slots open, or book whatever is free right now.
- **Books your favorite seat first** — auto-prioritizes the seats and floors you starred in anny, plus your own preferences.
- **Pluggable SSO** — KIT and TUM built in; easily extended to any anny university.
- **Calm & fair** — one seat per time slot, tried gently one at a time; no request storms.
- **Zero-config option** — sensible defaults; everything overridable via `.env` or GitHub Secrets/Variables, no code changes.
- **Runs anywhere** — GitHub Actions + cron-job.org (no server), or any Linux cron.

## 🏫 Supported Universities

| University | SSO Provider | Status |
| --- | --- | --- |
| Karlsruhe Institute of Technology (KIT) | `kit` | ✅ Supported |
| Technical University of Munich (TUM) | `tum` | ✅ Supported |
| Other anny-based libraries | Custom provider | [Add yours →](#-adding-a-new-university) |

## ⚡ Quick Start

### 🚀 Automated (recommended) — runs itself in the cloud, no server

This is how you actually use it day-to-day. **A local clone runs once and exits; it does not
schedule anything** — for daily automation, deploy it to GitHub Actions:

1. **Fork** this repository (top-right **Fork** button). Your credentials live in GitHub
   *Secrets*, never in the code — so a public fork is perfectly safe. Prefer a private copy?
   Create a new **private** repo and push this project into it.
2. Add your login as **GitHub Secrets** (Settings → Secrets and variables → Actions → Secrets):
   `USERNAME` and `PASSWORD`.
3. *(Optional)* Add config like `SSO_PROVIDER`, `FLOORS`, `PREFERRED_RESOURCES` as repository
   **Variables** on the same page.
4. Schedule the daily run via **cron-job.org** — see [Automated Scheduling](#-automated-scheduling).

That's it — it now books for you every day. New to GitHub/secrets/schedulers? Let an AI walk
you through it → [AI-Assisted Setup](#-ai-assisted-setup).

### 🧪 Run locally (optional — for testing credentials or development)

```bash
git clone https://github.com/wiestju/anny-booking-automation.git
cd anny-booking-automation
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then edit .env (USERNAME, PASSWORD, SSO_PROVIDER)
python main.py
```

A local run just verifies everything works and books once. Everything has sensible defaults,
and your anny favorites are picked up automatically.

## 🤖 AI-Assisted Setup

Not a programmer? The whole setup — forking, GitHub Secrets, a scheduler — is easiest with an
AI assistant guiding you one step at a time. You never touch the code yourself.

The smoothest path is **[Claude Code](https://claude.com/claude-code)**: it can clone the
repo, edit your `.env`, and walk you through GitHub Secrets and cron-job.org interactively
on your own machine. Or paste this prompt into [Claude](https://claude.ai):

```text
I want to set up anny-booking-automation to automatically book library seats at my university.
The repo is: https://github.com/wiestju/anny-booking-automation

Please guide me through the full setup step by step, asking me one question at a time.
My university is: [KIT / TUM / other]. I have little technical experience.
```

It will walk you through forking the repo, adding your credentials as GitHub Secrets,
creating an access token, and scheduling the daily run — one step at a time.

## 🔧 Configuration

All settings are environment variables (in `.env` locally, or GitHub Actions
Secrets/Variables). Only `USERNAME`/`PASSWORD` are required.

| Variable | Default | Description |
| --- | --- | --- |
| `USERNAME`, `PASSWORD` | — | Your university SSO credentials (required). |
| `SSO_PROVIDER` | `kit` | Which SSO provider to use (`kit`, `tum`, …). |
| `BOOKING_MODE` | `opening` | `opening` = book at each floor's real opening time; `immediate` = book what's free now. |
| `BOOK_DAYS_AHEAD` | `4` | Book the day this many days ahead. |
| `BOOKING_TIMES` | 3 windows | Comma-separated `HH:MM:SS-HH:MM:SS` windows, in priority order. |
| `FLOORS` | *(all)* | Empty = all floors. Otherwise a comma-separated priority list of name/slug substrings, e.g. `lehrbuchsammlung`. |
| `PREFERRED_RESOURCES` | *(none)* | Favorite seats tried first, e.g. `A1.007`. Find names via `scripts/list_resources.py`. |
| `USE_ANNY_FAVORITES` | `True` | Also auto-prioritize the seats/floors you starred in anny. |
| `SNIPE_ACTIVATE_MIN` | `20` | Opening mode: only wake up when an opening is within N minutes. |
| `DEBUG` | `False` | Verbose request logging. |

Booking exactly one seat per time window is the default. The windows are attempted in
parallel; within each, seats are tried one at a time — favorites first — stopping on the
first success.

## 🎯 How booking works

### Opening mode (default)

Anny releases slots ahead of time — for each floor, at a configured *advance start time*, a
set number of days in advance. The tool reads these values live from anny (so it
self-adjusts if your library changes them), waits for each floor's real opening moment, and
calmly books.

> **KIT example:** the study floors open in the evening, staggered per floor
> (~19:14–19:26 Berlin time), for the day 4 ahead. The run is scheduled to start shortly
> before that and books right as each floor opens — when seats are plentiful. Your library's
> times will differ; the tool figures them out on its own. Check yours with
> `python scripts/check_advance.py`.

### Immediate mode

`BOOKING_MODE=immediate` skips the timing logic and books whatever is available right now
for the target day — handy for libraries without an advance-release mechanism, or for a
quick test.

## ⏰ Automated Scheduling

Run it daily from **GitHub Actions**, triggered precisely by
[cron-job.org](https://cron-job.org). (GitHub's built-in `schedule:` cron can be delayed
10–15 min and is UTC-only, which is why an external trigger is used. Prefer your own server?
Any Linux cron works too — point it at `scripts/snipe.sh`.)

**1. Add GitHub Secrets** (Settings → Secrets and variables → Actions → Secrets):

| Secret | Value |
| --- | --- |
| `USERNAME` | Your university username |
| `PASSWORD` | Your university password |

Optionally add any config from the table above as repository **Variables** (same page).

**2. Create a GitHub Personal Access Token** with Actions read/write on this repo.

**3. Configure cron-job.org:**

| Setting | Value |
| --- | --- |
| URL | `https://api.github.com/repos/YOUR_USER/anny-booking-automation/actions/workflows/schedule.yml/dispatches` |
| Method | `POST` |
| Schedule | shortly **before** your earliest floor opening, timezone `Europe/Berlin` |
| Body | `{"ref":"main"}` |
| Headers | `Authorization: Bearer YOUR_TOKEN`, `Accept: application/vnd.github+json` |

> **KIT example:** trigger at **19:05** (a few minutes before the ~19:14 opening). The job
> then waits for each floor and books. Run **one** source only (GitHub Actions *or* your own
> cron) to avoid two attempts colliding.

## 🎓 Adding a New University

The auth layer is pluggable. Create `auth/providers/youruni.py`:

```python
from auth.providers.base import SSOProvider

class YourUniProvider(SSOProvider):
    name = "youruni"
    domain = "youruni.edu"

    def authenticate(self) -> str:
        # Implement the SAML flow using self.session, self.redirect_response,
        # self.username, self.password. Return the HTML containing SAMLResponse.
        ...
```

Register it in `auth/providers/__init__.py`, then set `SSO_PROVIDER=youruni`. New
universities are the most welcome contribution — see [CONTRIBUTING.md](CONTRIBUTING.md).

## 🛠️ Development

```bash
pip install -e ".[dev]"   # runtime + dev deps (pytest, ruff)
ruff check .              # lint
pytest                    # run the test suite (no credentials needed)
```

CI runs ruff + pytest on every push/PR across Python 3.10–3.12. Tests cover the pure logic
(`booking/selection.py`, `utils/helpers.py`) and **need no credentials or network**.

```text
anny-booking-automation/
├── main.py                 # Entry point (both booking modes)
├── config/constants.py     # Settings (all env-overridable)
├── auth/
│   ├── session.py          # SAML SSO login
│   └── providers/          # Pluggable SSO providers (base, kit, tum, …)
├── booking/
│   ├── client.py           # anny API client
│   └── selection.py        # Pure floor/seat prioritization (unit-tested)
├── scripts/                # check_advance.py, list_resources.py, run helpers
└── tests/                  # pytest suite
```

## 🆘 Help & Support

Something not working, or want your university supported? **[Open an issue](https://github.com/wiestju/anny-booking-automation/issues/new/choose)** — bug reports and
new-university requests are welcome, and setup questions are fine too. Please redact any
credentials from logs you paste. Contributions are very welcome; see
[CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE) — please use responsibly, see [DISCLAIMER.md](DISCLAIMER.md).
