# Anny Booking Automation

Automate study space reservations on [anny.eu](https://anny.eu) platforms used by university libraries. Logs in via SAML SSO, finds available slots, and books them automatically.

## Features

- **Pluggable SSO** - KIT and TUM providers included, easily extendable for other universities
- **Smart scheduling** - Waits until midnight when slots open, or runs immediately for testing
- **Configurable time slots** - Set your preferred booking times in order of priority
- **Resource priority** - Define preferred desk/room IDs; falls back to any available resource
- **Environment-based config** - All settings (provider, times, resources) via `.env` / GitHub Secrets
- **Automated execution** - Runs via GitHub Actions + cron-job.org for precise timing

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

```env
# Mandatory
USERNAME=your_university_username
PASSWORD=your_university_password

# Timezone (default: Europe/Berlin)
TIMEZONE="Europe/Berlin"

# Booking time slots in order of priority (format: hh:mm:ss-hh:mm:ss, comma-separated)
BOOKING_TIMES="14:00:00-19:00:00, 09:00:00-13:00:00, 20:00:00-23:45:00"

# SSO provider - available: "kit", "tum" (add more in auth/providers/)
SSO_PROVIDER="kit"

# Resource configuration
RESOURCE_URL_PATH="/resources/1-lehrbuchsammlung-eg-und-1-og/children"
SERVICE_ID="449"

# Preferred resource IDs tried first (comma-separated). Leave empty to skip.
RESOURCE_IDS=""

# Set to "True" to iterate through all available resources after trying RESOURCE_IDS
USE_ANY_RESOURCE_ID="True"
```

See `.env.example` for a full reference including a TUM example.

### 3. Run locally

```bash
python main.py
```

## Automated Scheduling

For daily automated bookings, use GitHub Actions triggered by [cron-job.org](https://cron-job.org).

### Why cron-job.org instead of GitHub's schedule?

GitHub Actions `on: schedule` has two issues:
- **Queue delays** - Workflows can be delayed by minutes, missing the booking window
- **UTC only** - No timezone support, requiring manual DST adjustments

cron-job.org provides precise, timezone-aware scheduling with no delays.

### Setup

#### 1. Add GitHub Secrets

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

#### 2. Create a GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate a token with `repo` scope (or fine-grained with Actions read/write)
3. Copy the token

#### 3. Configure cron-job.org

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

### How it works

1. cron-job.org triggers the workflow at **23:58**
2. The script logs in and establishes a session
3. It waits until **00:00** when new slots become available
4. Instantly books the first available slot from your priority list

## Project Structure

```
anny-booking-automation/
├── main.py                 # Entry point
├── .env.example            # Example environment configuration
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
