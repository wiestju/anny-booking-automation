AUTH_BASE_URL = "https://auth.anny.eu"
ANNY_BASE_URL = "https://anny.eu"
BOOKING_API_BASE = "https://b.anny.eu/api/v1"
CHECKOUT_FORM_API = "https://b.anny.eu/api/ui/checkout-form"
TIMEZONE = "Europe/Berlin"

## Provider
# Example KIT
SSO_PROVIDER = "kit"  # Available: kit, tum (add more in auth/providers/)
RESOURCE_URL = f"{BOOKING_API_BASE}/resources/1-lehrbuchsammlung-eg-und-1-og/children"
SERVICE_ID = "449"
RESOURCE_ID = None # "5957"  # Will be set dynamically if None, else use the given ID
# Example TUM
# SSO_PROVIDER = "tum"  # Available: kit, tum (add more in auth/providers/)
# RESOURCE_URL = f"{BOOKING_API_BASE}/resources/study-desks-branch-library-main-campus/children" # TUM - Branch Library Main Campus
# SERVICE_ID = "601" # Branch Library Main Campus
# RESOURCE_ID = None # "16099" # Will be set dynamically if None, else use the given ID - "16099" -> Desk No. 125

DEFAULT_HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
    'accept-encoding': 'plain'
}

# Booking time slots (in order of priority)
BOOKING_TIMES = [
    {
        'start': '14:00:00',
        'end': '19:00:00'
    },
    {
        'start': '09:00:00',
        'end': '13:00:00'
    },
    {
        'start': '20:00:00',
        'end': '23:45:00'
    },
]