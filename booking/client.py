import requests
from requests.exceptions import JSONDecodeError
from config.constants import RESOURCE_URL, BOOKING_API_BASE, CHECKOUT_FORM_API, ANNY_BASE_URL, SERVICE_ID


class CheckoutException(Exception):
    pass


class BookingClient:
    def __init__(self, cookies, customer_account_id=None):
        self.session = requests.Session()
        self.session.cookies = cookies
        self.token = cookies.get('anny_shop_jwt')
        self.resource_url = RESOURCE_URL
        self.service_id = SERVICE_ID
        self.customer_account_id = customer_account_id

        self.session.headers.update({
            'authorization': f'Bearer {self.token}',
            'accept': 'application/vnd.api+json',
            'content-type': 'application/vnd.api+json',
            'origin': ANNY_BASE_URL,
            'referer': ANNY_BASE_URL + '/',
            'user-agent': 'Mozilla/5.0'
        })

    def discover_resource_config(self):
        """Attempt to discover RESOURCE_URL_PATH and SERVICE_ID from the Anny API."""
        if not self.customer_account_id:
            print("❌ Could not determine customer account ID from login. Please set RESOURCE_URL_PATH and SERVICE_ID in your .env")
            return False

        response = self.session.get(
            f"{BOOKING_API_BASE}/customer-accounts/{self.customer_account_id}/all-resources",
            params={
                'page[number]': 1,
                'page[size]': 50,
                'sort': 'name',
                'include': 'services',
            }
        )
        if not response.ok:
            print(f"❌ Failed to discover resources: HTTP {response.status_code}")
            return False

        try:
            body = response.json()
        except (ValueError, JSONDecodeError):
            print("❌ Invalid JSON response when discovering resources")
            return False

        resources = body.get('data', [])

        # Only keep parent resources (has_children=true) — these have individual desks
        # as children and match the /resources/{slug}/children URL pattern.
        bookable = []
        for r in resources:
            if not r.get('attributes', {}).get('has_children'):
                continue
            svc_refs = r.get('relationships', {}).get('services', {}).get('data', [])
            if not svc_refs:
                continue
            slug = r.get('attributes', {}).get('slug') or r['id']
            bookable.append((f"/resources/{slug}", svc_refs[0]['id']))

        if not bookable:
            print("❌ No bookable resources found. Please set RESOURCE_URL_PATH and SERVICE_ID in your .env")
            return False

        if len(bookable) > 1:
            print("ℹ️ Multiple bookable resources found. Using the first one automatically.")
            print("   To use a specific one, set these in your .env:")
            for resource_path, service_id in bookable:
                print(f"   RESOURCE_URL_PATH={resource_path}/children")
                print(f"   SERVICE_ID={service_id}")
                print()

        resource_path, service_id = bookable[0]
        self.resource_url = f"{BOOKING_API_BASE}{resource_path}/children"
        self.service_id = service_id

        print(f"✅ Auto-discovered: RESOURCE_URL_PATH={resource_path}/children, SERVICE_ID={service_id}")
        return True

    def find_available_resources(self, start, end):
        response = self.session.get(self.resource_url, params={
            'page[number]': 1,
            'page[size]': 250,
            'filter[available_from]': start,
            'filter[available_to]': end,
            'filter[availability_exact_match]': 1,
            'filter[exclude_hidden]': 0,
            'filter[exclude_child_resources]': 0,
            'filter[availability_service_id]': int(self.service_id),
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
        return [r['id'] for r in resources]

    def reserve(self, resource_id, start, end):
        booking = self.session.post(
            f"{BOOKING_API_BASE}/order/bookings",
            params={
                'stateless': '1',
                'include': 'customer,voucher,bookings.booking_add_ons.add_on.cover_image,bookings.sub_bookings.resource,bookings.sub_bookings.service,bookings.customer,bookings.service.custom_forms.custom_fields,bookings.service.add_ons.cover_image,bookings.service.add_ons.group,bookings.cancellation_policy,bookings.resource.cover_image,bookings.resource.parent,bookings.resource.location,bookings.resource.category,bookings.reminders,bookings.booking_series,bookings.sequenced_bookings.resource,bookings.sequenced_bookings.service,bookings.sequenced_bookings.service.add_ons.cover_image,bookings.sequenced_bookings.service.add_ons.group,bookings.booking_participants,sub_orders.bookings,sub_orders.organization.legal_documents'
            },
            json={
                "resource_id": [resource_id],
                "service_id": {self.service_id: 1},
                "start_date": start,
                "end_date": end,
                "description": "",
                "customer_note": "",
                "add_ons_by_service": {self.service_id: [[]]},
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
            except:
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
            f"{BOOKING_API_BASE}/order",
            params={
                "stateless": "1",
                "include": "customer,voucher,bookings.booking_add_ons.add_on.cover_image,bookings.sub_bookings.resource,bookings.sub_bookings.service,bookings.customer,bookings.service.custom_forms.custom_fields,bookings.service.add_ons.cover_image,bookings.service.add_ons.group,bookings.cancellation_policy,bookings.resource.cover_image,bookings.resource.parent,bookings.resource.location,bookings.resource.category,bookings.reminders,bookings.booking_series,bookings.sequenced_bookings.resource,bookings.sequenced_bookings.service,bookings.sequenced_bookings.service.add_ons.cover_image,bookings.sequenced_bookings.service.add_ons.group,bookings.booking_participants,sub_orders.bookings,sub_orders.organization.legal_documents",
                "oid": oid,
                "oat": oat
            },
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
            print(f"❌ Checkout failed: HTTP {final.status_code}")
            try:
                errors = final.json().get("errors", {})
                print(f"  {errors[0]['title']}: {errors[0]['detail']}")
                print(f"  resource_id: {resource_id}; start: {start}; end: {end}")
            except:
                pass

            # Clear checkout cart
            clear_checkout = self.session.get(
                f"{BOOKING_API_BASE}/order/bookings/delete-all",
                params={
                    "stateless": "1",
                    "include": "customer,voucher,bookings.booking_add_ons.add_on.cover_image,bookings.sub_bookings.resource,bookings.sub_bookings.service,bookings.customer,bookings.service.custom_forms.custom_fields,bookings.service.add_ons.cover_image,bookings.service.add_ons.group,bookings.cancellation_policy,bookings.resource.cover_image,bookings.resource.parent,bookings.resource.location,bookings.resource.category,bookings.reminders,bookings.booking_series,bookings.sequenced_bookings.resource,bookings.sequenced_bookings.service,bookings.sequenced_bookings.service.add_ons.cover_image,bookings.sequenced_bookings.service.add_ons.group,bookings.booking_participants,sub_orders.bookings,sub_orders.organization.legal_documents",
                    "oid": oid,
                    "oat": oat
                }
            )
            if clear_checkout.ok:
                print(f"  Checkout cart has been cleared. Booking quota should be restored.")
            else:
                print(f"  Checkout cart could not be cleared. You might need to wait 15 minutes for your booking quota to be restored automatically again.")

            raise CheckoutException

        print("✅ Reservation successful!")
        print(f"  resource_id: {resource_id}; start: {start}; end: {end}")
        return True
