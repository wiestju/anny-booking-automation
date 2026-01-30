# Anny Booking Automation

Automate study space reservations on [anny.eu](https://anny.eu) platforms used by university libraries. Logs in via SAML SSO, finds available slots, and books them automatically.

## Features

- **Pluggable SSO** - KIT provider included, easily extendable for other universities
- **Smart scheduling** - Waits until midnight when slots open, or runs immediately for testing
- **Configurable time slots** - Set your preferred booking times in order of priority
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

### 2. Configure credentials

Create a `.env` file:

```env
USERNAME=your_university_username
PASSWORD=your_university_password
```

### 3. Configure booking settings

Edit `config/constants.py`:

```python
SSO_PROVIDER = "kit"  # Your university's SSO provider
RESOURCE_ID = None    # Auto-detect, or set a specific resource ID

BOOKING_TIMES = [
    {'start': '14:00:00', 'end': '19:00:00'},  # First priority
    {'start': '09:00:00', 'end': '13:00:00'},  # Second priority
    {'start': '20:00:00', 'end': '23:45:00'},  # Third priority
]
```

### 4. Run locally

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

| Secret | Value |
|--------|-------|
| `USERNAME` | Your university username |
| `PASSWORD` | Your university password |

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
├── config/
│   └── constants.py        # URLs, timezone, booking times
├── auth/
│   ├── session.py          # Login session handling
│   └── providers/          # SSO provider implementations
│       ├── base.py         # Abstract base class
│       └── kit.py          # KIT provider
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
    "youruni": YourUniProvider,
}
```

## License

MIT
