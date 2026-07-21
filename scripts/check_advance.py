"""
Print the current booking config (advance_booking_period / advance_start_time)
of every floor — handy to see when a floor's slots open and whether the library
shifted the times. Read-only, books nothing.

Usage:  venv/bin/python3 scripts/check_advance.py
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
os.chdir(_REPO_ROOT)

from auth.session import AnnySession
from booking.client import BookingClient
from config.constants import PASSWORD, SSO_PROVIDER, USERNAME
from utils.helpers import ts


def main():
    print(f"{ts()} Checking advance-times...")
    session = AnnySession(USERNAME, PASSWORD, provider_name=SSO_PROVIDER)
    cookies = session.login()
    if not cookies:
        print(f"{ts()} ❌ Login failed")
        return
    client = BookingClient(cookies, customer_account_id=session.customer_account_id)
    client.discover_all_floors()

    print(f"\n{ts()} Opening config per floor:")
    for url, svc in client.resource_urls:
        floor = client.floor_names.get(url, url.split('/')[-2])
        c = BookingClient(cookies, customer_account_id=session.customer_account_id,
                          resource_urls=[(url, svc)])
        attrs = c.get_service_attributes() or {}
        print(f"\n— {floor} (service {svc}):")
        print(f"    advance_booking_period: {attrs.get('advance_booking_period', '?')} days")
        print(f"    advance_start_time:     {attrs.get('advance_start_time', '?')}")
        print(f"    lead_time:              {attrs.get('lead_time', '?')}")
        print(f"    updated_at:             {attrs.get('updated_at', '?')}")

    print(f"\n{ts()} Done.")


if __name__ == "__main__":
    main()
