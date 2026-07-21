from os import getenv

from dotenv import load_dotenv

AUTH_BASE_URL = "https://auth.anny.eu"
ANNY_BASE_URL = "https://anny.eu"
BOOKING_API_BASE = "https://b.anny.eu/api/v1"
CHECKOUT_FORM_API = "https://b.anny.eu/api/ui/checkout-form"

DEFAULT_HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
    'accept-encoding': 'plain'
}

# Get variables from dotenv file
load_dotenv('.env', override=True)

USERNAME = getenv("USERNAME")
PASSWORD = getenv("PASSWORD")

TIMEZONE = getenv("TIMEZONE") or "Europe/Berlin"

# Provider — available: kit, tum (add more in auth/providers/)
SSO_PROVIDER = getenv("SSO_PROVIDER") or "kit"

# Resource config is optional: if unset, the tool auto-discovers all bookable
# floors/buildings for your account. Set these only to pin a single resource.
RESOURCE_URL_PATH = getenv("RESOURCE_URL_PATH")
SERVICE_ID = getenv("SERVICE_ID")
RESOURCE_URL = f"{BOOKING_API_BASE}{RESOURCE_URL_PATH}" if RESOURCE_URL_PATH else None

# Verbose request/error logging
DEBUG = getenv("DEBUG") == "True"

# ── Booking strategy ─────────────────────────────────────────────────────────
# "opening"   → wait for each floor's real advance_start_time and book calmly the
#               moment it opens (recommended; slots open ahead of time and are
#               uncontested for minutes). Self-adjusting: reads the times live.
# "immediate" → just book what is available right now (classic flow / testing).
BOOKING_MODE = (getenv("BOOKING_MODE") or "opening").strip().lower()

# Which day to book: today + this many days.
BOOK_DAYS_AHEAD = int(getenv("BOOK_DAYS_AHEAD") or "4")

# Floor selection & priority. Empty = auto-discover and use ALL floors. Otherwise
# a comma-separated priority list of name/slug substrings (case-insensitive).
FLOORS = [f.strip().lower() for f in (getenv("FLOORS") or "").split(",") if f.strip()]

# Favorite seats tried first within a floor (comma-separated, priority order;
# case-insensitive substring match against the seat name). A preference, not a filter.
PREFERRED_RESOURCES = [r.strip().lower() for r in (getenv("PREFERRED_RESOURCES") or "").split(",") if r.strip()]

# Also auto-prioritize the seats/floors you starred in anny itself.
# Empty/unset → default ON (unset CI variables become empty strings).
USE_ANNY_FAVORITES = (getenv("USE_ANNY_FAVORITES") or "True").strip().lower() not in ("false", "0", "no")

# "opening" mode only: wake up / log in only when the next opening is within this
# many minutes; otherwise exit silently so a cron heartbeat re-checks later.
SNIPE_ACTIVATE_MIN = int(getenv("SNIPE_ACTIVATE_MIN") or "20")

# "opening" mode only: after a floor opens, keep trying its seats for at most this
# long (absorbs clock jitter / a few seconds of "not yet open").
SNIPE_WINDOW_S = int(getenv("SNIPE_WINDOW_S") or "20")

# Print the services/opening-hours anny offers for the resource, then continue
DISCOVER_SLOTS = getenv("DISCOVER_SLOTS") == "True"

# Booking time slots (comma-separated HH:MM:SS-HH:MM:SS, in order of priority)
BOOKING_TIMES_CSV = getenv("BOOKING_TIMES") or "14:00:00-19:00:00, 09:00:00-13:00:00, 20:00:00-23:45:00"
BOOKING_TIMES = [
    {"start": b.split("-")[0].strip(), "end": b.split("-")[1].strip()}
    for b in BOOKING_TIMES_CSV.split(",") if "-" in b
]
