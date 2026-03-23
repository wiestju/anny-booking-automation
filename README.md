# Anny Booking Automation

Automatically reserve study spaces and library seats on [anny.eu](https://anny.eu) — the booking platform used by university libraries across Germany, including the **Karlsruhe Institute of Technology (KIT)** and the **Technical University of Munich (TUM)**.

The script logs in via SAML Single Sign-On (SSO), waits until midnight when new slots open, and instantly books your preferred time slot — fully automated.

## Features

- **Auto-discovery** — Automatically detects your library's resource and service IDs after login; no manual API research needed
- **Pluggable SSO** — Built-in providers for KIT (Karlsruhe Institute of Technology) and TUM (Technical University of Munich); easily extendable for other universities
- **Smart scheduling** — Waits until midnight when new booking slots open, or runs immediately for testing
- **Configurable time slots** — Set your preferred booking times in order of priority
- **Resource priority** — Define preferred desk or room IDs; falls back to any available resource
- **Environment-based config** — All settings via `.env` file or GitHub Secrets; no code changes required
- **Flexible execution** — Runs via GitHub Actions + cron-job.org (no server needed), or as a self-hosted Linux cron job

## Supported Universities

| University | SSO Provider | Status |
| --- | --- | --- |
| Karlsruhe Institute of Technology (KIT) | `kit` | ✅ Supported |
| Technical University of Munich (TUM) | `tum` | ✅ Supported |
| Other Anny-based libraries | Custom provider | See [Adding a New SSO Provider](#adding-a-new-sso-provider) |

## Quick Start

Choose your setup path and jump to the relevant section:

- **[Option A: GitHub Actions + cron-job.org](#option-a-github-actions--cron-joborg)** — No server needed. Fork the repo, add secrets, done.
- **[Option B: Self-hosted Linux Cron](#option-b-self-hosted-linux-cron)** — Clone, configure a `.env` file, and run on your own server.

## Automated Scheduling

Two options are supported: **GitHub Actions** (no server needed) or a **self-hosted Linux cron job** (for users who run their own server).

---

### Option A: GitHub Actions + cron-job.org

#### Why cron-job.org instead of GitHub's built-in schedule?

GitHub Actions `on: schedule` has two issues:

- **Queue delays** — Workflows can be delayed by minutes, missing the booking window
- **UTC only** — No timezone support, requiring manual DST adjustments

[cron-job.org](https://cron-job.org) provides precise, timezone-aware scheduling with no delays.

#### Setup

##### 1. Fork the repository

Click the **Fork** button on the [GitHub repository page](https://github.com/wiestju/anny-booking-automation) to create your own copy. The GitHub Actions workflow is already included.

> **⚠️ Security:** Forks of public repositories are public by default. Since your credentials are stored as GitHub Secrets (not in code), they are safe — but it is still recommended to set your fork to **private**: go to your fork's **Settings > Danger Zone > Change visibility**. Also remember: Never commit or push a `.env` file to any GitHub repository.

##### 2. Add GitHub Secrets

In your forked repository: **Settings > Secrets and variables > Actions**

Add the following repository secrets:

| Secret | Value |
| ------ | ----- |
| `USERNAME` | Your university username |
| `PASSWORD` | Your university password |
| `TIMEZONE` | Your timezone (e.g. `Europe/Berlin`) |
| `BOOKING_TIMES` | Comma-separated time slots (e.g. `14:00:00-19:00:00, 09:00:00-13:00:00`) |
| `SSO_PROVIDER` | `kit` or `tum` |
| `RESOURCE_IDS` | Preferred resource IDs (optional) |
| `USE_ANY_RESOURCE_ID` | `True` or `False` |

##### 3. Create a GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate a token with `repo` scope (or fine-grained with Actions read/write)
3. Copy the token

##### 4. Configure cron-job.org

Create a new cron job with these settings:

| Setting | Value |
|---------|-------|
| URL | `https://api.github.com/repos/YOUR_USERNAME/anny-booking-automation/actions/workflows/schedule.yml/dispatches` |
| Schedule | `58 23 * * *` (23:58 daily) |
| Timezone | `Europe/Berlin` (or your timezone) |
| Request method | `POST` |

**Headers:**
```
Authorization: Bearer YOUR_GITHUB_TOKEN
Content-Type: application/json
Accept: application/vnd.github.v3+json
```

**Request body:**
```json
{"ref": "main"}
```

#### How it works

1. cron-job.org triggers the workflow at **23:58**
2. The script logs in and establishes a session
3. It waits until **00:00** when new slots become available
4. Instantly books the first available slot from your priority list

---

### Option B: Self-hosted Linux Cron

If you have a Linux server (Raspberry Pi, VPS, etc.) you can run the script directly without GitHub Actions.

#### Setup

1. **Clone and install** the project on your server:

```bash
git clone https://github.com/wiestju/anny-booking-automation.git
cd anny-booking-automation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

1. **Create your `.env`** file by copying the example template and filling in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `USERNAME` | **Yes** | — | `student123` | Your university login username |
| `PASSWORD` | **Yes** | — | `secret` | Your university login password |
| `SSO_PROVIDER` | **Yes** | — | `kit` | SSO provider (`kit` or `tum`) |
| `RESOURCE_URL_PATH` | No | Auto-discovered | `/resources/1-lehrbuchsammlung-eg-und-1-og/children` | API path for your library's rooms. Detected automatically if not set. |
| `SERVICE_ID` | No | Auto-discovered | `449` | Booking service ID for your library. Detected automatically if not set. |
| `TIMEZONE` | No | `Europe/Berlin` | `Europe/Berlin` | Timezone for the midnight wait |
| `BOOKING_TIMES` | No | `14:00:00-19:00:00, 09:00:00-13:00:00, 20:00:00-23:45:00` | `14:00:00-19:00:00, 09:00:00-13:00:00` | Desired time slots in priority order (`hh:mm:ss-hh:mm:ss`, comma-separated) |
| `RESOURCE_IDS` | No | — | `5957, 5958` | Preferred desk or room IDs tried first (comma-separated) |
| `USE_ANY_RESOURCE_ID` | No | `False` | `True` | If `True`, falls back to any available resource after trying `RESOURCE_IDS` |

> **Note:** `RESOURCE_URL_PATH` and `SERVICE_ID` are automatically discovered from the Anny API after login. You only need to set them manually if auto-discovery picks the wrong resource (e.g. if your account has access to multiple libraries).
>
> **Note:** At least one of `RESOURCE_IDS` or `USE_ANY_RESOURCE_ID=True` must be set, otherwise no resource will be booked.

See `.env.example` for a ready-to-copy template including examples for KIT and TUM.

1. **Make the run script executable:**

```bash
chmod +x scripts/run.sh
```

4. **Add a cron entry** that fires at **23:58** every night:

```bash
crontab -e
```

Add this line (replace `/path/to` with the actual path):

```
58 23 * * * /path/to/anny-booking-automation/scripts/run.sh >> /path/to/anny-booking-automation/logs/cron.log 2>&1
```

> **Tip:** Create the logs directory first: `mkdir -p /path/to/anny-booking-automation/logs`

The script activates the virtual environment and runs `main.py` automatically. Logs are written to `logs/cron.log`.

#### How it works

1. The system cron fires `scripts/run.sh` at **23:58** in your server's local time
2. The script logs in and establishes a session
3. It waits until **00:00** when new slots become available
4. Instantly books the first available slot from your priority list

> **Timezone note:** The script uses the `TIMEZONE` env var to determine when midnight occurs. Make sure your server's local time matches your target timezone, or set `TIMEZONE` explicitly in your `.env`.

## Project Structure

```
anny-booking-automation/
├── main.py                 # Entry point
├── .env.example            # Example environment configuration
├── scripts/
│   └── run.sh              # Wrapper script for self-hosted Linux cron
├── config/
│   └── constants.py        # Loads settings from environment / .env
├── auth/
│   ├── session.py          # Login session handling and customer account discovery
│   └── providers/          # SSO provider implementations
│       ├── base.py         # Abstract base class
│       ├── kit.py          # Karlsruhe Institute of Technology (KIT)
│       └── tum.py          # Technical University of Munich (TUM)
├── booking/
│   └── client.py           # Booking API client and resource auto-discovery
└── utils/
    └── helpers.py          # Utility functions
```

## Adding a New SSO Provider

To add support for another university that uses Anny for library bookings, create `auth/providers/youruni.py`:

```python
from auth.providers.base import SSOProvider

class YourUniProvider(SSOProvider):
    name = "Your University Name"
    domain = "youruni.edu"
    available_days_ahead = 3  # How many days ahead bookings open

    def authenticate(self) -> str:
        # Implement the university's SAML authentication flow
        # Use self.session, self.redirect_response, self.username, self.password
        # Return the HTML page containing the SAMLResponse form field
        pass
```

Register it in `auth/providers/__init__.py`:

```python
from auth.providers.youruni import YourUniProvider

PROVIDERS = {
    "kit": KITProvider,
    "tum": TUMProvider,
    "youruni": YourUniProvider,
}
```

Then set `SSO_PROVIDER="youruni"` in your `.env` file.

## License

MIT
