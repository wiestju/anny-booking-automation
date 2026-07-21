"""
List every seat/room per floor with its name (e.g. A1.007) — so you can find the
exact name of your favorite seat for PREFERRED_RESOURCES.

Read-only, books nothing.

Usage:            venv/bin/python3 scripts/list_resources.py
Single floor:     venv/bin/python3 scripts/list_resources.py lehrbuchsammlung
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
    flt = sys.argv[1].lower() if len(sys.argv) > 1 else None
    session = AnnySession(USERNAME, PASSWORD, provider_name=SSO_PROVIDER)
    cookies = session.login()
    if not cookies:
        print(f"{ts()} ❌ Login failed")
        return
    client = BookingClient(cookies, customer_account_id=session.customer_account_id)
    client.discover_all_floors()

    for url, svc in client.resource_urls:
        floor = client.floor_names.get(url, url.split('/')[-2])
        if flt and flt not in floor.lower() and flt not in url.lower():
            continue
        resources = client.get_floor_resource_ids(url, svc) or []
        names = sorted(n for _, _, n in resources if n)
        print(f"\n{floor}  ({len(names)} seats):")
        line = "   "
        for n in names:
            line += f"{n:<12}"
            if len(line) > 90:
                print(line)
                line = "   "
        if line.strip():
            print(line)


if __name__ == "__main__":
    main()
