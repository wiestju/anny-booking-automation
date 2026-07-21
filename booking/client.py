import time as _time

import requests
from requests.exceptions import JSONDecodeError

from config.constants import (
    ANNY_BASE_URL,
    BOOKING_API_BASE,
    CHECKOUT_FORM_API,
    DEBUG,
    RESOURCE_URL,
    SERVICE_ID,
)
from utils.helpers import ts


class CheckoutException(Exception):
    pass


class BookingClient:
    def __init__(self, cookies, customer_account_id=None, resource_urls=None):
        self.session = requests.Session()
        self.session.cookies = cookies
        self.token = cookies.get('anny_shop_jwt')
        # resource_urls is a list of (url, service_id) tuples covering all floors
        self.resource_urls = resource_urls or [(RESOURCE_URL, SERVICE_ID)]
        self.resource_url = self.resource_urls[0][0]
        self.service_id = self.resource_urls[0][1]
        self.customer_account_id = customer_account_id
        self._cached_customer = None  # set by prefetch_customer_info()
        self.floor_names = {}         # set by discover_all_floors()
        self.floor_by_parent_id = {}  # set by discover_all_floors()

        self.session.headers.update({
            'authorization': f'Bearer {self.token}',
            'accept': 'application/vnd.api+json',
            'content-type': 'application/vnd.api+json',
            'origin': ANNY_BASE_URL,
            'referer': ANNY_BASE_URL + '/',
            'user-agent': 'Mozilla/5.0'
        })

    def discover_all_floors(self):
        """Discover all bookable floor resource URLs and update self.resource_urls."""
        if not self.customer_account_id:
            return False
        try:
            response = self.session.get(
                f"{BOOKING_API_BASE}/customer-accounts/{self.customer_account_id}/all-resources",
                params={'page[number]': 1, 'page[size]': 50, 'sort': 'name', 'include': 'services'},
                timeout=15
            )
        except Exception as e:
            print(f"{ts()} ⚠️ Floor discovery request failed: {e}")
            return False

        if not response.ok:
            print(f"{ts()} ⚠️ Floor discovery failed: HTTP {response.status_code}")
            return False

        try:
            body = response.json()
        except (ValueError, JSONDecodeError):
            return False

        found = []
        for r in body.get('data', []):
            if not r.get('attributes', {}).get('has_children'):
                continue
            svc_refs = r.get('relationships', {}).get('services', {}).get('data', [])
            if not svc_refs:
                continue
            slug = r.get('attributes', {}).get('slug') or r['id']
            name = r.get('attributes', {}).get('name', slug)
            url  = f"{BOOKING_API_BASE}/resources/{slug}/children"
            svc  = svc_refs[0]['id']
            found.append((url, svc, name, str(r['id'])))

        if not found:
            print(f"{ts()} ⚠️ No bookable floors found — using default")
            return False

        self.resource_urls = [(url, svc) for url, svc, _, _ in found]
        self.resource_url = self.resource_urls[0][0]
        self.service_id   = self.resource_urls[0][1]
        # url → human-readable floor name, for FLOORS matching and logging
        self.floor_names = {url: name for url, _, name, _ in found}
        # parent resource id → url, so favorited floors can be matched
        self.floor_by_parent_id = {pid: url for url, _, _, pid in found}
        print(f"{ts()} 🏢 {len(found)} floor(s) discovered:", flush=True)
        for _, _, name, _ in found:
            print(f"   → {name}", flush=True)
        return True

    def get_favorites(self):
        """Return the user's starred favorites (liked=True) as model-id strings,
        ordered by anny's order_index. IDs may be seat (child) or floor (parent)
        resource ids — the caller resolves which is which.
        """
        try:
            r = self.session.get(f"{BOOKING_API_BASE}/favorites",
                                  params={'page[number]': 1, 'page[size]': 250}, timeout=15)
        except Exception as e:
            print(f"{ts()} ⚠️ Favorites request failed: {e}")
            return []
        if not r.ok:
            return []
        try:
            data = r.json().get('data', [])
        except (ValueError, JSONDecodeError):
            return []
        liked = []
        for item in data:
            a = item.get('attributes', {})
            if a.get('model_type') == 'resources' and a.get('liked'):
                liked.append((a.get('order_index', 0), str(a.get('model_id'))))
        liked.sort(key=lambda x: x[0])
        return [mid for _, mid in liked]

    def warm_connection(self):
        """Pre-establish TCP+TLS connection to b.anny.eu so no handshake overhead at midnight."""
        try:
            url, _ = self.resource_urls[0]
            self.session.get(url, params={'page[number]': 1, 'page[size]': 1, 'filter[exclude_hidden]': 0}, timeout=10)
        except Exception:
            pass

    def prefetch_customer_info(self):
        """Cache given_name/family_name/email to skip the checkout-form GET during booking."""
        if not self.customer_account_id:
            return False
        try:
            r = self.session.get(
                f"{BOOKING_API_BASE}/customer-accounts/{self.customer_account_id}",
                timeout=10
            )
            if r.ok:
                attrs = r.json().get('data', {}).get('attributes', {})
                given  = attrs.get('given_name')  or attrs.get('first_name')
                family = attrs.get('family_name') or attrs.get('last_name')
                email  = attrs.get('email')
                if given and family and email:
                    self._cached_customer = {'given_name': given, 'family_name': family, 'email': email}
                    if DEBUG:
                        print(f"{ts()} [prefetch] customer: {given} {family} <{email}>")
                    return True
        except Exception:
            pass
        return False

    def discover_resource_config(self):
        """Fallback: auto-discover resource URL when none is configured."""
        if not self.customer_account_id:
            print(f"{ts()} ❌ No customer account ID — set RESOURCE_URL and SERVICE_ID manually")
            return False
        return self.discover_all_floors()

    def find_available_resources(self, start, end):
        """Query all floors for available resources and return combined list of IDs."""
        params = {
            'page[number]': 1,
            'page[size]': 250,
            'filter[available_from]': start,
            'filter[available_to]': end,
            'filter[availability_exact_match]': 1,
            'filter[exclude_hidden]': 0,
            'filter[exclude_child_resources]': 0,
            'filter[include_unavailable]': 0,
            'filter[pre_order_ids]': '',
            'sort': 'name'
        }
        all_ids = []
        any_ok  = False
        for url, svc in self.resource_urls:
            params['filter[availability_service_id]'] = int(svc)
            if DEBUG:
                print(f"{ts()} [debug] GET availability: {url} from={start} to={end}")
            t0 = _time.monotonic()
            try:
                response = self.session.get(url, params=params)
            except Exception as e:
                print(f"{ts()} ❌ Request failed for {url}: {e}")
                continue
            elapsed = (_time.monotonic() - t0) * 1000
            if not response.ok:
                print(f"{ts()} ❌ HTTP {response.status_code} ({elapsed:.0f}ms) for {url}")
                continue
            try:
                resources = response.json().get('data', [])
            except (ValueError, JSONDecodeError):
                continue
            # (resource_id, service_id) — jede Resource muss mit dem Service
            # ihres eigenen Floors gebucht werden
            ids = [(r['id'], svc) for r in resources]
            all_ids.extend(ids)
            any_ok = True
            floor = url.split('/')[-2]
            print(f"{ts()} [availability] {elapsed:.0f}ms → {len(ids)} resources ({floor}) for {start[:16]}–{end[11:16]}")
        return all_ids if any_ok else None

    def discover_available_slots(self):
        """Print services and time windows for each floor."""
        for url, _svc in self.resource_urls:
            floor = url.split('/')[-2]
            print(f"\n{ts()} 🔎 Discovering slots for {floor}...")
            response = self.session.get(url, params={
                'page[number]': 1, 'page[size]': 10,
                'filter[exclude_hidden]': 0,
                'filter[exclude_child_resources]': 0,
                'sort': 'name', 'include': 'services',
            })
            if not response.ok:
                print(f"{ts()} ❌ HTTP {response.status_code}")
                continue
            try:
                body = response.json()
            except (ValueError, JSONDecodeError):
                continue
            resources = body.get('data', [])
            included  = {i['id']: i for i in body.get('included', [])}
            print(f"{ts()} {len(resources)} child resources")
            seen = set()
            for r in resources[:3]:
                for svc_ref in r.get('relationships', {}).get('services', {}).get('data', []):
                    sid = svc_ref['id']
                    if sid in seen:
                        continue
                    seen.add(sid)
                    attrs = included.get(sid, {}).get('attributes', {})
                    print(f"  Service {sid}: {attrs.get('name','?')} duration={attrs.get('duration','?')}min")
                    hours = attrs.get('opening_hours', {})
                    for day, slots in hours.items():
                        print(f"    {day}: {slots}")
        print()

    def get_all_resource_ids(self):
        """Fetch (resource_id, service_id) pairs from every floor (no availability filter)."""
        all_ids = []
        any_ok  = False
        for url, svc in self.resource_urls:
            t0 = _time.monotonic()
            try:
                response = self.session.get(url, params={
                    'page[number]': 1, 'page[size]': 250,
                    'filter[exclude_hidden]': 0,
                    'filter[exclude_child_resources]': 0,
                    'sort': 'name'
                })
            except Exception as e:
                print(f"{ts()} ❌ Pre-fetch request failed: {e}")
                continue
            elapsed = (_time.monotonic() - t0) * 1000
            if not response.ok:
                print(f"{ts()} ❌ Pre-fetch failed ({url.split('/')[-2]}): HTTP {response.status_code} ({elapsed:.0f}ms)")
                continue
            try:
                resources = response.json().get('data', [])
            except (ValueError, JSONDecodeError):
                continue
            ids = [(r['id'], svc) for r in resources]
            all_ids.extend(ids)
            any_ok = True
            floor = url.split('/')[-2]
            print(f"{ts()} Pre-fetch ({floor}): {elapsed:.0f}ms → {len(ids)} IDs")
        if any_ok:
            print(f"{ts()} Pre-fetch total: {len(all_ids)} resource IDs across {len(self.resource_urls)} floor(s)")
        return all_ids if any_ok else None

    def get_floor_resource_ids(self, url, svc):
        """Fetch (resource_id, service_id, name) triples for ONE floor only.

        `name` is the human-readable seat/room label (e.g. "1.007") — used for
        per-resource favorites.
        """
        try:
            response = self.session.get(url, params={
                'page[number]': 1, 'page[size]': 250,
                'filter[exclude_hidden]': 0,
                'filter[exclude_child_resources]': 0,
                'sort': 'name'
            }, timeout=15)
        except Exception as e:
            print(f"{ts()} ❌ Resource fetch failed ({url.split('/')[-2]}): {e}")
            return None
        if not response.ok:
            print(f"{ts()} ❌ Resource fetch ({url.split('/')[-2]}): HTTP {response.status_code}")
            return None
        try:
            resources = response.json().get('data', [])
        except (ValueError, JSONDecodeError):
            return None
        return [(r['id'], svc, r.get('attributes', {}).get('name', '')) for r in resources]

    def get_service_attributes(self):
        """Fetch full attributes of the configured service (advance_booking_period, advance_start_time, ...)."""
        url, svc = self.resource_urls[0]
        try:
            r = self.session.get(url, params={
                'page[number]': 1, 'page[size]': 3,
                'filter[exclude_hidden]': 0,
                'filter[exclude_child_resources]': 0,
                'sort': 'name', 'include': 'services',
            }, timeout=15)
        except Exception:
            return None
        if not r.ok:
            return None
        try:
            included = r.json().get('included', [])
        except (ValueError, JSONDecodeError):
            return None
        for inc in included:
            if inc.get('type') == 'services' and str(inc.get('id')) == str(svc):
                return inc.get('attributes', {})
        for inc in included:
            if inc.get('type') == 'services':
                return inc.get('attributes', {})
        return None

    def reserve(self, resource_id, start, end):
        """Book a single resource.

        resource_id accepts a bare id (uses self.service_id) or an (id, service_id)
        tuple. Multi-resource across different floors/services is NOT supported by
        the backend (it hangs and errors), so this method books exactly one resource.
        """
        if isinstance(resource_id, (list, tuple)) and len(resource_id) == 2 and not isinstance(resource_id[0], (list, tuple)):
            rid, svc = resource_id[0], str(resource_id[1])
        else:
            rid, svc = resource_id, self.service_id
        rid_label = rid
        ids = [rid]
        if DEBUG:
            print(f"{ts()} [debug] POST /order/bookings resource={rid_label} svc={svc} start={start}")
        t0 = _time.monotonic()
        booking = self.session.post(
            f"{BOOKING_API_BASE}/order/bookings",
            params={'stateless': '1'},
            json={
                "resource_id": ids,
                "service_id": {svc: 1},
                "start_date": start,
                "end_date": end,
                "description": "",
                "customer_note": "",
                "add_ons_by_service": {svc: [[]]},
                "sub_bookings_by_service": {},
                "strategy": "multi-resource"
            }
        )
        booking_elapsed = (_time.monotonic() - t0) * 1000

        if not booking.ok:
            if booking.status_code == 429:
                print(f"{ts()} ⚠️ HTTP 429 ({booking_elapsed:.0f}ms) resource={rid_label} — rate limited")
                return 'ratelimit'
            try:
                body   = booking.json()
                errors = body.get("errors", [])
                detail = errors[0].get('detail', '') if errors else ''
                title  = errors[0].get('title', '')  if errors else ''
                is_ausgebucht = 'ausgebucht' in detail.lower() or 'ausgebucht' in title.lower()
                print(f"{ts()} ❌ HTTP {booking.status_code} ({booking_elapsed:.0f}ms) resource={rid_label} — {title}: {detail}")
                if DEBUG and not is_ausgebucht:
                    print(f"    [debug] full error: {body}")
            except Exception:
                is_ausgebucht = False
                if DEBUG:
                    print(f"    [debug] raw: {booking.text[:500]}")
            return 'ausgebucht' if is_ausgebucht else False
        if DEBUG:
            print(f"{ts()} [debug] /order/bookings OK: {booking_elapsed:.0f}ms")

        try:
            data = booking.json().get("data", {})
        except (ValueError, JSONDecodeError):
            print(f"{ts()} ❌ Invalid JSON from booking: {booking.text[:200]}")
            return False

        oid = data.get("id")
        oat = data.get("attributes", {}).get("access_token")

        if not oid or not oat:
            print(f"{ts()} ❌ Missing booking ID or access token in response")
            return False

        # Use cached customer info if available — skips one HTTP round-trip
        if self._cached_customer:
            customer = self._cached_customer
            if DEBUG:
                print(f"{ts()} [debug] using cached customer info")
        else:
            t1 = _time.monotonic()
            checkout = self.session.get(f"{CHECKOUT_FORM_API}?oid={oid}&oat={oat}&stateless=1")
            if DEBUG:
                print(f"{ts()} [debug] GET checkout-form: {(_time.monotonic()-t1)*1000:.0f}ms → HTTP {checkout.status_code}")
            if not checkout.ok:
                print(f"{ts()} ❌ Checkout form failed: HTTP {checkout.status_code}")
                return False
            try:
                customer = checkout.json().get("default", {}).get("customer", {})
            except (ValueError, JSONDecodeError):
                print(f"{ts()} ❌ Invalid JSON from checkout form: {checkout.text[:200]}")
                return False

        t2 = _time.monotonic()
        final = self.session.post(
            f"{BOOKING_API_BASE}/order",
            params={"stateless": "1", "oid": oid, "oat": oat},
            json={
                "customer": {
                    "given_name": customer.get("given_name"),
                    "family_name": customer.get("family_name"),
                    "email": customer.get("email")
                },
                "accept_terms": True,
                "payment_method": "",
                "success_url": f"{ANNY_BASE_URL}/checkout/success?oids={oid}&oats={oat}",
                "cancel_url": f"{ANNY_BASE_URL}/checkout?step=checkout&childResource={ids[0]}",
                "meta": {"timezone": "Europe/Berlin"}
            }
        )
        final_elapsed = (_time.monotonic() - t2) * 1000

        if not final.ok:
            print(f"{ts()} ❌ Checkout failed: HTTP {final.status_code} ({final_elapsed:.0f}ms) resource={rid_label}")
            try:
                errors = final.json().get("errors", [])
                if errors:
                    print(f"    {errors[0].get('title', '?')}: {errors[0].get('detail', '?')}")
            except Exception:
                pass
            clear = self.session.get(
                f"{BOOKING_API_BASE}/order/bookings/delete-all",
                params={"stateless": "1", "oid": oid, "oat": oat}
            )
            if clear.ok:
                print(f"{ts()} Cart cleared — booking quota restored.")
            else:
                print(f"{ts()} ⚠️ Cart could not be cleared — quota may be locked for ~15 min.")
            raise CheckoutException

        total_elapsed = (_time.monotonic() - t0) * 1000
        print(f"{ts()} ✅ Reservation successful! resource={rid_label} start={start} ({total_elapsed:.0f}ms total)")
        return True
