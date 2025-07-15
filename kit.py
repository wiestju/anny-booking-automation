import requests
import urllib.parse
import re
import html
import time
import datetime
import pytz
import os

from dotenv import load_dotenv

def get_day():
    dt = datetime.datetime.now(pytz.timezone('Europe/Berlin')) + datetime.timedelta(days=3)
    date = dt.strftime('%Y-%m-%d')
    return date

def login(username, password):

    ses = requests.Session()
    ses.headers = {
        'accept': 'text/html, application/xhtml+xml',
        'accept-encoding': 'plain',
        'referer':  'https://auth.anny.eu/',
        'origin': 'https://auth.anny.eu',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
        'x-requested-with': 'XMLHttpRequest',
        'x-inertia': 'true',
        'x-inertia-version': '66b32acea13402d3aef4488ccd239c93',
    }

    r = ses.get(
        'https://auth.anny.eu/login/sso'
    )

    ses.headers['X-XSRF-TOKEN'] = urllib.parse.unquote(r.cookies['XSRF-TOKEN'])

    r2 = ses.post(
        'https://auth.anny.eu/login/sso',
        json={
            'domain': 'kit.edu'
        }, headers={
            'referer': 'https://auth.anny.eu/login/sso',
        }
    )

    redirect_url = r2.headers['x-inertia-location']

    r3 = ses.get(
        redirect_url,
        allow_redirects=True
    )

    ses.headers.pop('x-requested-with')
    ses.headers.pop('x-inertia')
    ses.headers.pop('x-inertia-version')

    pattern = r'name="csrf_token" value="([^"]+)"'
    csrf_token = re.search(pattern, r3.text).group(1)

    r4 = ses.post(
        'https://idp.scc.kit.edu/idp/profile/SAML2/Redirect/SSO?execution=e1s1',
        data={
            'csrf_token': csrf_token,
            'j_username': username,
            'j_password': password,
            '_eventId_proceed': '',
            'fudis_web_authn_assertion_input': '',
        }
    )

    response = html.unescape(r4.text)

    if '/consume' in response:
        print("KIT-Login successful!")
    else:
        print("Failed to login, probably wrong credentials!")
        return False

    pattern = r'form action="([^"]+)"'
    consume_url = re.search(pattern, response).group(1)
    pattern = r'name="RelayState" value="([^"]+)"'
    relayState = re.search(pattern, response).group(1)
    pattern = r'name="SAMLResponse" value="([^"]+)"'
    samlResponse = re.search(pattern, response).group(1)

    r5 = ses.post(
        consume_url,
        data={
            'RelayState': relayState,
            'SAMLResponse': samlResponse
        }
    )

    r6 = ses.get(
        'https://anny.eu/en-us/login?target=/en-us/home?withoutIntent=true',
        allow_redirects=True
    )


    return ses.cookies

def test_reservation():
    load_dotenv('credentials.env', override=True)

    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')

    cookies = login(username, password)


    TOKEN = cookies['anny_shop_jwt']

    ses = requests.Session()
    ses.cookies = cookies
    ses.headers = {
            'accept': 'application/vnd.api+json',
            'accept-encoding': 'plain',
            'authorization': 'Bearer ' + TOKEN,
            'content-type': 'application/vnd.api+json',
            'origin': 'https://anny.eu',
            'referer': 'https://anny.eu/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'
        }

    r = ses.post(
        'https://b.anny.eu/api/v1/order/bookings?include=customer,voucher,bookings.booking_add_ons.add_on.cover_image,bookings.sub_bookings.resource,bookings.sub_bookings.service,bookings.series_bookings,bookings.customer,bookings.service.custom_forms.custom_fields,bookings.cancellation_policy,bookings.resource.cover_image,bookings.resource.parent,bookings.resource.category,bookings.reminders,bookings.booking_series,sub_orders.bookings,sub_orders.organization.legal_documents&stateless=1',
        json={
            "resource_id": [
                "3305"
            ], "service_id": {
                "449": 1
            }, "start_date": get_day() + "T13:00:00+02:00",
            "end_date": get_day() + "T18:00:00+02:00",
            "description":"", "customer_note": "",
            "add_ons_by_service": {
                "449": [
                    []
                ]
            }, "sub_bookings_by_service": {},
            "strategy": "multi-resource"
        }, cookies=cookies
    )

    print(r.status_code, r.text)

    oid = r.json()['data']['id']
    oat = r.json()['data']['attributes']['access_token']

    r2 = ses.get(
        'https://b.anny.eu/api/ui/checkout-form?oid=' + oid + '&oat=' + oat + '&stateless=1'
    )

    customer = r2.json()['default']['customer']

    r3 = ses.post(
        'https://b.anny.eu/api/v1/order?include=customer,voucher,bookings.booking_add_ons.add_on,bookings.sub_bookings.resource,bookings.sub_bookings.service,bookings.service.custom_forms.custom_fields,bookings.cancellation_policy,bookings.resource.cover_image,bookings.resource.parent,bookings.reminders,bookings.customer,bookings.attendees,sub_orders.bookings,sub_orders.organization.legal_documents,last_payment.method&oid=' + oid + '&oat=' + oat + '&stateless=1',
        json={
            "customer": {
                "given_name": customer['given_name'],
                "family_name": customer['family_name'],
                "email": customer['email']
            }, "accept_terms": True,
            "payment_method": "",
            "success_url": "https://anny.eu/checkout/success?oids=" + oid + "&oats=" + oat,
            "cancel_url": "https://anny.eu/checkout?step=checkout&childResource=3302",
            "meta": {
                "timezone":"Europe/Berlin"
            }
        }
    )

    print(r3.status_code, r3.text)
    if r3.ok:
        print("Reservation successful!")

test_reservation()
