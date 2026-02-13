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

# Variables to be overwritten by dotenv vars
TIMEZONE = getenv("TIMEZONE") or "Europe/Berlin"

## Provider - available: kit, tum (add more in auth/providers/)
SSO_PROVIDER = getenv("SSO_PROVIDER") or "kit"
RESOURCE_URL_PATH = getenv("RESOURCE_URL_PATH") or "/resources/1-lehrbuchsammlung-eg-und-1-og/children"
SERVICE_ID = getenv("SERVICE_ID") or "449"
RESOURCE_ID = getenv("RESOURCE_ID") or None
USE_ANY_RESOURCE_ID = getenv("USE_ANY_RESOURCE_ID") == "True"

RESOURCE_URL = f"{BOOKING_API_BASE}{RESOURCE_URL_PATH}"

# Booking time slots (in order of priority)
BOOKING_TIMES_CSV = getenv("BOOKING_TIMES") or "14:00:00-19:00:00,09:00:00-13:00:00,20:00:00-23:45:00"
# create object with the format [{"start": start, "end": end}] from csv
BOOKING_TIMES = [{"start": b.split("-")[0], "end": b.split("-")[1]} for b in BOOKING_TIMES_CSV.split(",")]