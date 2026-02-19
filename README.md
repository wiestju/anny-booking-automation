# Anny Booking Automation

Automate study space reservations on [anny.eu](https://anny.eu) platforms used by university libraries. Logs in via SAML SSO, finds available slots, and books them automatically.

## Features

- **Pluggable SSO** - KIT and TUM providers included, easily extendable for other universities
- **Smart scheduling** - Waits until midnight when slots open, or runs immediately for testing
- **Configurable time slots** - Set your preferred booking times in order of priority
- **Resource priority** - Define preferred desk/room IDs; falls back to any available resource
- **Environment-based config** - All settings (provider, times, resources) via `.env` / GitHub Secrets
- **Automated execution** - Runs via GitHub Actions + cron-job.org, or as a self-hosted Linux cron job

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/wiestju/anny-booking-automation.git
cd anny-booking-automation
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Example | Description |
|---|---|---|---|---|
| `USERNAME` | **Yes** | — | `student123` | Your university login username |
| `PASSWORD` | **Yes** | — | `secret` | Your university login password |
| `SSO_PROVIDER` | **Yes** | — | `kit` | SSO provider (`kit` or `tum`) |
| `RESOURCE_URL_PATH` | **Yes** | — | `/resources/1-lehrbuchsammlung-eg-und-1-og/children` | API path for your library's rooms |
| `SERVICE_ID` | **Yes** | — | `449` | Service ID for your library |
| `TIMEZONE` | No | `Europe/Berlin` | `Europe/Berlin` | Timezone for the midnight wait |
| `BOOKING_TIMES` | No | `14:00:00-19:00:00, 09:00:00-13:00:00, 20:00:00-23:45:00` | `14:00:00-19:00:00, 09:00:00-13:00:00` | Desired time slots in priority order (`hh:mm:ss-hh:mm:ss`, comma-separated) |
| `RESOURCE_IDS` | No | — | `5957, 5958` | Preferred resource IDs tried first (comma-separated). Omit to skip. |
| `USE_ANY_RESOURCE_ID` | No | `False` | `True` | If `True`, falls back to any available resource after trying `RESOURCE_IDS` |

See `.env.example` for a ready-to-copy template including a TUM example.

> **Note:** At least one of `RESOURCE_IDS` or `USE_ANY_RESOURCE_ID=True` must be set, otherwise no resource will be booked.

### 3. Run locally

```bash
python main.py
```

## Automated Scheduling

Two options are supported: **GitHub Actions** (no server needed) or a **self-hosted Linux cron job** (for users who run their own server).

---

### Option A: GitHub Actions + cron-job.org

#### Why cron-job.org instead of GitHub's schedule?

GitHub Actions `on: schedule` has two issues:
- **Queue delays** - Workflows can be delayed by minutes, missing the booking window
- **UTC only** - No timezone support, requiring manual DST adjustments

cron-job.org provides precise, timezone-aware scheduling with no delays.

#### Setup

##### 1. Add GitHub Secrets

In your repository: **Settings > Secrets and variables > Actions**

Add all variables from your `.env` file as repository secrets. At a minimum:

| Secret | Value |
|--------|-------|
| `USERNAME` | Your university username |
| `PASSWORD` | Your university password |
| `TIMEZONE` | Your timezone (e.g. `Europe/Berlin`) |
| `BOOKING_TIMES` | Comma-separated time slots (e.g. `14:00:00-19:00:00, 09:00:00-13:00:00`) |
| `SSO_PROVIDER` | `kit` or `tum` |
| `RESOURCE_URL_PATH` | Resource URL path for your library |
| `SERVICE_ID` | Service ID for your library |
| `RESOURCE_IDS` | Preferred resource IDs (optional) |
| `USE_ANY_RESOURCE_ID` | `True` or `False` |

##### 2. Create a GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate a token with `repo` scope (or fine-grained with Actions read/write)
3. Copy the token

##### 3. Configure cron-job.org

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

If you have a Linux server (or a Raspberry Pi, VPS, etc.) you can run the script directly without GitHub Actions.

#### Setup

1. **Clone and install** the project on your server (see [Quick Start](#quick-start)).

2. **Create your `.env`** file in the repo root with all required variables.

3. **Make the run script executable:**

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
│   ├── session.py          # Login session handling
│   └── providers/          # SSO provider implementations
│       ├── base.py         # Abstract base class
│       ├── kit.py          # KIT provider
│       └── tum.py          # TUM provider
├── booking/
│   └── client.py           # Booking API client
└── utils/
    └── helpers.py          # Utility functions
```

## Adding a New SSO Provider

Create `auth/providers/youruni.py`:

```python
from auth.providers.base import SSOProvider

class YourUniProvider(SSOProvider):
    name = "youruni"
    domain = "youruni.edu"

    def authenticate(self) -> str:
        # Implement SAML authentication flow
        # Use self.session, self.redirect_response, self.username, self.password
        # Return HTML containing SAMLResponse
        pass
```

Register in `auth/providers/__init__.py`:

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
