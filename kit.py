import os
import re
import html
import pytz
import requests
import datetime
import urllib.parse

from dotenv import load_dotenv


# === CONFIGURATION CONSTANTS === #
AUTH_BASE_URL = "https://auth.anny.eu"
ANNY_BASE_URL = "https://anny.eu"
BOOKING_API_BASE = "https://b.anny.eu/api/v1"
CHECKOUT_FORM_API = "https://b.anny.eu/api/ui/checkout-form"
RESOURCE_URL = f"{BOOKING_API_BASE}/resources/1-lehrbuchsammlung-eg-und-1-og/children"
SERVICE_ID = "449"

DEFAULT_HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
    'accept': 'application/vnd.api+json',
    'accept-encoding': 'plain'
}


def get_future_datetime(days_ahead=3, hour="13:00:00"):
    dt = datetime.datetime.now(pytz.timezone('Europe/Berlin')) + datetime.timedelta(days=days_ahead)
    return dt.strftime(f"%Y-%m-%dT{hour}+02:00")


def extract_html_value(text, pattern):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Pattern not found: {pattern}")
    return html.unescape(match.group(1))


class AnnySession:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.cookies = None

    def login(self):
        try:
            self._init_headers()
            self._sso_login()
            self._kit_auth()
            self._consume_saml()
            self.cookies = self.session.cookies
            print("✅ Login successful")
            return self.cookies
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return None

    def _init_headers(self):
        self.session.headers.update({
            **DEFAULT_HEADERS,
            'accept': 'text/html, application/xhtml+xml',
            'referer': AUTH_BASE_URL + '/',
            'origin': AUTH_BASE_URL
        })

    def _sso_login(self):
        r1 = self.session.get(f"{AUTH_BASE_URL}/login/sso")
        self.session.headers['X-XSRF-TOKEN'] = urllib.parse.unquote(r1.cookies['XSRF-TOKEN'])

        page_data = extract_html_value(r1.text, r'data-page="(.*?)"')
        version = re.search(r'"version"\s*:\s*"([a-f0-9]{32})"', page_data)
        x_inertia_version = version.group(1) if version else '66b32acea13402d3aef4488ccd239c93'

        self.session.headers.update({
            'x-requested-with': 'XMLHttpRequest',
            'x-inertia': 'true',
            'x-inertia-version': x_inertia_version
        })

        r2 = self.session.post(f"{AUTH_BASE_URL}/login/sso", json={"domain": "kit.edu"})
        redirect_url = r2.headers['x-inertia-location']
        self.redirect_response = self.session.get(redirect_url)

    def _kit_auth(self):
        self.session.headers.pop('x-requested-with', None)
        self.session.headers.pop('x-inertia', None)
        self.session.headers.pop('x-inertia-version', None)

        csrf_token = extract_html_value(self.redirect_response.text, r'name="csrf_token" value="([^"]+)"')

        r4 = self.session.post(
            'https://idp.scc.kit.edu/idp/profile/SAML2/Redirect/SSO?execution=e1s1',
            data={
                'csrf_token': csrf_token,
                'j_username': self.username,
                'j_password': self.password,
                '_eventId_proceed': '',
                'fudis_web_authn_assertion_input': '',
            }
        )

        if "/consume" not in html.unescape(r4.text):
            raise Exception("KIT authentication failed")

        self.saml_response_html = r4.text

    def _consume_saml(self):
        consume_url = extract_html_value(self.saml_response_html, r'form action="([^"]+)"')
        relay_state = extract_html_value(self.saml_response_html, r'name="RelayState" value="([^"]+)"')
        saml_response = extract_html_value(self.saml_response_html, r'name="SAMLResponse" value="([^"]+)"')

        self.session.post(consume_url, data={
            'RelayState': relay_state,
            'SAMLResponse': saml_response
        })

        self.session.get(f"{ANNY_BASE_URL}/en-us/login?target=/en-us/home?withoutIntent=true")


class BookingClient:
    def __init__(self, cookies):
        self.session = requests.Session()
        self.session.cookies = cookies
        self.token = cookies.get('anny_shop_jwt')
        self.session.headers.update({
            **DEFAULT_HEADERS,
            'authorization': f'Bearer {self.token}',
            'content-type': 'application/vnd.api+json',
            'origin': ANNY_BASE_URL,
            'referer': ANNY_BASE_URL + '/'
        })

    def find_available_resource(self, start, end):
        response = self.session.get(RESOURCE_URL, params={
            'page[number]': 1,
            'page[size]': 250,
            'filter[available_from]': start,
            'filter[available_to]': end,
            'filter[availability_exact_match]': 1,
            'filter[exclude_hidden]': 0,
            'filter[exclude_child_resources]': 0,
            'filter[availability_service_id]': SERVICE_ID,
            'filter[include_unavailable]': 0,
            'filter[pre_order_ids]': '',
            'sort': 'name'
        })

        resources = response.json().get('data', [])
        return resources[0]['id'] if resources else None

    def reserve(self, resource_id, start, end):
        booking = self.session.post(
            f"{BOOKING_API_BASE}/order/bookings?include=customer&stateless=1",
            json={
                "resource_id": [resource_id],
                "service_id": {SERVICE_ID: 1},
                "start_date": start,
                "end_date": end,
                "description": "",
                "customer_note": "",
                "add_ons_by_service": {SERVICE_ID: [[]]},
                "sub_bookings_by_service": {},
                "strategy": "multi-resource"
            }
        )

        if not booking.ok:
            print("❌ Slot already taken.")
            return False

        data = booking.json().get("data", {})
        oid = data.get("id")
        oat = data.get("attributes", {}).get("access_token")

        checkout = self.session.get(f"{CHECKOUT_FORM_API}?oid={oid}&oat={oat}&stateless=1")
        customer = checkout.json().get("default", {}).get("customer", {})

        final = self.session.post(
            f"{BOOKING_API_BASE}/order?oid={oid}&oat={oat}&stateless=1",
            json={
                "customer": {
                    "given_name": customer.get("given_name"),
                    "family_name": customer.get("family_name"),
                    "email": customer.get("email")
                },
                "accept_terms": True,
                "payment_method": "",
                "success_url": f"{ANNY_BASE_URL}/checkout/success?oids={oid}&oats={oat}",
                "cancel_url": f"{ANNY_BASE_URL}/checkout?step=checkout&childResource={resource_id}",
                "meta": {"timezone": "Europe/Berlin"}
            }
        )

        if final.ok:
            print("✅ Reservation successful!")
            return True

        print("❌ Reservation failed.")
        return False


def main():
    load_dotenv('credentials.env', override=True)
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    if not username or not password:
        print("❌ Missing credentials in .env")
        return

    session = AnnySession(username, password)
    cookies = session.login()

    if not cookies:
        return

    booking = BookingClient(cookies)
    start = get_future_datetime(hour="13:00:00")
    end = get_future_datetime(hour="18:00:00")

    resource_id = booking.find_available_resource(start, end)

    if not resource_id:
        print("⚠️ No available resources found.")
        return

    booking.reserve(resource_id, start, end)


if __name__ == "__main__":
    main()
