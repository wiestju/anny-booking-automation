import requests
from config.constants import RESOURCE_URL, BOOKING_API_BASE, CHECKOUT_FORM_API, ANNY_BASE_URL, SERVICE_ID
from utils.helpers import extract_html_value

class BookingClient:
    def __init__(self, cookies):
        self.session = requests.Session()
        self.session.cookies = cookies
        self.token = cookies.get('anny_shop_jwt')

        self.session.headers.update({
            'authorization': f'Bearer {self.token}',
            'content-type': 'application/vnd.api+json',
            'origin': ANNY_BASE_URL,
            'referer': ANNY_BASE_URL + '/',
            'user-agent': 'Mozilla/5.0'
        })

    def find_available_resource(self, start, end):
        response = self.session.get(RESOURCE_URL, params={
            'page[number]': 1,
            'page[size]': 250,
            'filter[available_from]': start,
            'filter[available_to]': end,
            'filter[availability_exact_match]': 1,
            'filter[availability_service_id]': SERVICE_ID,
            'filter[include_unavailable]': 0,
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
