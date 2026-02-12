import requests
from requests.exceptions import JSONDecodeError
from config.constants import RESOURCE_URL, BOOKING_API_BASE, CHECKOUT_FORM_API, ANNY_BASE_URL, SERVICE_ID

class BookingClient:
    def __init__(self, cookies):
        self.session = requests.Session()
        self.session.cookies = cookies
        self.token = cookies.get('anny_shop_jwt')

        self.session.headers.update({
            'authorization': f'Bearer {self.token}',
            'accept': 'application/vnd.api+json',
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
            'filter[exclude_hidden]': 0,
            'filter[exclude_child_resources]': 0,
            'filter[availability_service_id]': int(SERVICE_ID),
            'filter[include_unavailable]': 0,
            'filter[pre_order_ids]': '',
            'sort': 'name'
        })
        if not response.ok:
            print(f"❌ Failed to fetch resources: HTTP {response.status_code}")
            return None
        try:
            resources = response.json().get('data', [])
        except (ValueError, JSONDecodeError):
            print(f"❌ Invalid JSON response when fetching resources: {response.text[:200]}")
            return None
        return resources[-1]['id'] if resources else None

    def reserve(self, resource_id, start, end):
        booking = self.session.post(
            f"{BOOKING_API_BASE}/order/bookings",
            params={
                'stateless': '1',
                'include': 'customer,voucher,bookings.booking_add_ons.add_on.cover_image,bookings.sub_bookings.resource,bookings.sub_bookings.service,bookings.customer,bookings.service.custom_forms.custom_fields,bookings.service.add_ons.cover_image,bookings.service.add_ons.group,bookings.cancellation_policy,bookings.resource.cover_image,bookings.resource.parent,bookings.resource.location,bookings.resource.category,bookings.reminders,bookings.booking_series,bookings.sequenced_bookings.resource,bookings.sequenced_bookings.service,bookings.sequenced_bookings.service.add_ons.cover_image,bookings.sequenced_bookings.service.add_ons.group,bookings.booking_participants,sub_orders.bookings,sub_orders.organization.legal_documents'
            },
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
            print(f"❌ Booking failed: HTTP {booking.status_code}")
            try:
                errors = booking.json().get("errors", {})
                print(f"  {errors[0]['title']}: {errors[0]['detail']}")
                print(f"  resource_id: {resource_id}; start: {start}; end: {end}")
            except (ValueError, JSONDecodeError, KeyError):
                pass
            return False

        try:
            data = booking.json().get("data", {})
        except (ValueError, JSONDecodeError):
            print("❌ Invalid JSON response from booking request.")
            print(f"  resource_id: {resource_id}; start: {start}; end: {end}")
            print(f"  response: {booking.text[:200]}")
            return False

        oid = data.get("id")
        oat = data.get("attributes", {}).get("access_token")

        if not oid or not oat:
            print("❌ Missing booking ID or access token in response")
            return False

        checkout = self.session.get(f"{CHECKOUT_FORM_API}?oid={oid}&oat={oat}&stateless=1")
        if not checkout.ok:
            print(f"❌ Checkout form failed: HTTP {checkout.status_code}")
            return False

        try:
            customer = checkout.json().get("default", {}).get("customer", {})
        except (ValueError, JSONDecodeError):
            print(f"❌ Invalid JSON response from checkout form: {checkout.text[:200]}")
            return False

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

        if not final.ok:
            print(f"❌ Reservation failed: HTTP {final.status_code}")
            try:
                errors = final.json().get("errors", {})
                print(f"  {errors[0]['title']}: {errors[0]['detail']}")
                print(f"  resource_id: {resource_id}; start: {start}; end: {end}")
            except (ValueError, JSONDecodeError, KeyError):
                pass
            return False

        print("✅ Reservation successful!")
        return True