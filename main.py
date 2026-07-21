"""
anny booking automation — single entry point, two calm strategies (no spamming,
no pre-firing).

BOOKING_MODE = "opening"  (recommended)
    Wait for each floor's real advance_start_time (read live, so it self-adjusts
    if the library shifts the times) and book the instant it opens. Slots unlock
    in the evening ~BOOK_DAYS_AHEAD days ahead, staggered per floor, and stay
    uncontested for minutes — one calm, well-timed pass is enough.
    Meant to run from a cron heartbeat: exits silently unless an opening is near.

BOOKING_MODE = "immediate"  (classic / other universities)
    Just book whatever is available right now for the target day. No waiting,
    no floor-opening logic — the normal reservation flow.

Both modes book each resource at most a couple of times and stop on the first
success; there is no burst/retry-storm and nothing fires before the real opening.
"""
import copy
import datetime
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytz

from auth.session import AnnySession
from booking.client import BookingClient, CheckoutException
from booking.selection import order_resources, select_floors
from config.constants import (
    BOOK_DAYS_AHEAD,
    BOOKING_MODE,
    BOOKING_TIMES,
    DISCOVER_SLOTS,
    FLOORS,
    PASSWORD,
    PREFERRED_RESOURCES,
    SNIPE_ACTIVATE_MIN,
    SNIPE_WINDOW_S,
    SSO_PROVIDER,
    TIMEZONE,
    USE_ANNY_FAVORITES,
    USERNAME,
)
from utils.helpers import get_future_datetime, ts

_print_lock = threading.Lock()

# Populated once in main() from the user's anny favorites (when USE_ANNY_FAVORITES).
_favorite_seat_ids = []    # resource ids of starred seats → tried first within a floor
_favorite_floor_urls = []  # floor urls starred in anny → floor priority when FLOORS is empty


def safe_print(msg):
    with _print_lock:
        print(msg, flush=True)


def load_favorites(ref):
    """Fetch the user's anny favorites and split them into starred seats vs. floors.
    Logs what was found so users who forgot they set favorites are reminded."""
    global _favorite_seat_ids, _favorite_floor_urls
    if not USE_ANNY_FAVORITES:
        return
    fav_ids = ref.get_favorites()
    if not fav_ids:
        return
    seats, floors = [], []
    for mid in fav_ids:
        if mid in ref.floor_by_parent_id:
            floors.append(ref.floor_by_parent_id[mid])
        else:
            seats.append(mid)
    _favorite_seat_ids = seats
    _favorite_floor_urls = floors

    # Resolve favorite seat ids → readable names (e.g. A1.007); stop once all found.
    seat_names = {}
    if seats:
        remaining = set(seats)
        for url, svc in ref.resource_urls:
            for rid, _svc, name in (ref.get_floor_resource_ids(url, svc) or []):
                if str(rid) in remaining:
                    seat_names[str(rid)] = name
                    remaining.discard(str(rid))
            if not remaining:
                break

    floor_names = [ref.floor_names.get(u, u) for u in floors]
    parts = []
    if seats:
        labels = [seat_names.get(s, f"ID {s}") for s in seats]
        parts.append(f"seat(s): {', '.join(labels)}")
    if floor_names:
        parts.append(f"floor(s): {', '.join(floor_names)}")
    safe_print(f"{ts()} 🌟 Prioritizing your anny favorites — {'; '.join(parts)}")
    safe_print(f"{ts()}    (starred in anny; disable with USE_ANNY_FAVORITES=False)")


def _today_at(time_str, tz):
    """'HH:MM:SS' → today's aware datetime in the configured timezone."""
    h, m, s = (int(x) for x in time_str.split(':'))
    now = datetime.datetime.now(tz)
    return tz.localize(datetime.datetime(now.year, now.month, now.day, h, m, s))


def book_window(cookies, cust_id, resource_urls, resources, window, tz, deadline=None):
    """
    Book ONE seat for a single time window, trying resources strictly one at a
    time (no parallel seat attempts): favorites first, then the rest, stopping on
    the first success. The three time windows are what run in parallel — each
    window calls this on its own thread.

    resources : list of (resource_id, service_id[, name]) — each booked with its
                own service. Favorites (PREFERRED_RESOURCES, then anny favorites)
                are ordered first.
    deadline  : if set, keep retrying a resource that is 'not yet open' / briefly
                rate-limited until this time (absorbs a few seconds of clock jitter
                at opening). If None, each resource is tried exactly once.
    Returns 'booked' | 'limit' | None.
    """
    start = get_future_datetime(days_ahead=BOOK_DAYS_AHEAD, time_string=window['start'])
    end   = get_future_datetime(days_ahead=BOOK_DAYS_AHEAD, time_string=window['end'])
    label = f"[{window['start']}]"

    res = order_resources(resources, PREFERRED_RESOURCES, _favorite_seat_ids)
    client = BookingClient(copy.copy(cookies), customer_account_id=cust_id,
                           resource_urls=resource_urls)

    status = booked_rid = booked_name = None
    for rid, svc, name in res:
        while True:
            try:
                r = client.reserve((rid, svc), start, end)
            except CheckoutException:
                status = 'limit'
                break
            except Exception as e:
                safe_print(f"{ts()} {label} ❌ {rid}: {e}")
                break  # move on to the next seat
            if r is True:
                status, booked_rid, booked_name = 'booked', rid, name
                break
            if r == 'ausgebucht':
                break  # this seat is gone → next seat
            if deadline and datetime.datetime.now(tz) < deadline:
                time.sleep(0.4)  # 'not yet open' / brief 429 — retry same seat
                continue
            break
        if status in ('booked', 'limit'):
            break

    if status == 'booked':
        seat = f" ({booked_name})" if booked_name else ""
        star = " ⭐ your anny favorite" if str(booked_rid) in _favorite_seat_ids else ""
        safe_print(f"{ts()} {label} ✅ BOOKED resource={booked_rid}{seat}{star}")
    elif status == 'limit':
        safe_print(f"{ts()} {label} ⚠️ Booking limit — this window is already taken")
    return status


def floors_of(ref):
    """ref.resource_urls → [(url, svc, name)] with FLOORS filter/priority and, when
    FLOORS is empty, anny favorite floors moved to the front."""
    floors = [(url, svc, ref.floor_names.get(url, url.split('/')[-2]))
              for url, svc in ref.resource_urls]
    return select_floors(floors, FLOORS, _favorite_floor_urls)


def run_opening_mode(cookies, session, ref, tz):
    """Wait for each floor's advance_start_time and book calmly the moment it opens.

    Every configured time window is booked on exactly ONE floor. With FLOORS set,
    floors are tried in that priority order; otherwise in opening-time order.
    """
    now = datetime.datetime.now(tz)

    floors = floors_of(ref)
    if not floors:
        safe_print(f"{ts()} ⚠️ No floors match FLOORS={FLOORS} — aborting")
        return

    # Read each selected floor's current opening time fresh (self-adjusting).
    entries = []  # (fire_dt, url, svc, name)
    for url, svc, name in floors:
        attrs = BookingClient(cookies, customer_account_id=session.customer_account_id,
                              resource_urls=[(url, svc)]).get_service_attributes() or {}
        tstr = attrs.get('advance_start_time')
        if tstr:
            entries.append((_today_at(tstr, tz), url, svc, name))

    if not entries:
        safe_print(f"{ts()} ⚠️ No advance_start_time found — aborting")
        return

    # FLOORS set → keep priority order. Otherwise → favorite floors first (in
    # favorite order), then the rest by opening time.
    if not FLOORS:
        fav = [e for e in entries if e[1] in _favorite_floor_urls]
        rest = [e for e in entries if e[1] not in _favorite_floor_urls]
        fav.sort(key=lambda e: _favorite_floor_urls.index(e[1]))
        rest.sort(key=lambda x: x[0])
        entries = fav + rest

    upcoming = [e for e in entries if e[0] >= now - datetime.timedelta(minutes=2)]
    if not upcoming:
        earliest = min(e[0] for e in entries)
        safe_print(f"{ts()} All of today's openings have passed "
                   f"(earliest was {earliest.strftime('%H:%M')}) — exiting.")
        return

    nearest = min(e[0] for e in upcoming)
    mins = (nearest - now).total_seconds() / 60
    if mins > SNIPE_ACTIVATE_MIN:
        safe_print(f"{ts()} Next opening at {nearest.strftime('%H:%M:%S')} "
                   f"({mins:.0f} min away) — exiting, cron will re-check.")
        return

    safe_print(f"{ts()} ── opening mode — target +{BOOK_DAYS_AHEAD}d, {len(upcoming)} floor(s) ──")
    for fire, _, _, name in upcoming:
        safe_print(f"{ts()}   {fire.strftime('%H:%M:%S')}  {name}")

    secured = set()
    for fire, url, svc, name in upcoming:
        wait = (fire - datetime.datetime.now(tz)).total_seconds()
        if wait > 0:
            safe_print(f"{ts()} ⏳ waiting {wait:.1f}s for {name} to open ({fire.strftime('%H:%M:%S')})...")
            time.sleep(wait)

        resources = ref.get_floor_resource_ids(url, svc)
        if not resources:
            safe_print(f"{ts()} [{name}] ⚠️ no resources — skipping")
            continue

        deadline = fire + datetime.timedelta(seconds=SNIPE_WINDOW_S)
        pending = [w for w in BOOKING_TIMES if w['start'] not in secured]
        # Run the (still-unsecured) time windows in parallel — one thread per
        # window; each books a single seat sequentially (favorites first).
        with ThreadPoolExecutor(max_workers=len(pending)) as ex:
            futs = {
                ex.submit(book_window, cookies, session.customer_account_id,
                          [(url, svc)], resources, w, tz, deadline): w
                for w in pending
            }
            for fut in as_completed(futs):
                w = futs[fut]
                if fut.result() in ('booked', 'limit'):
                    secured.add(w['start'])

        if all(w['start'] in secured for w in BOOKING_TIMES):
            safe_print(f"{ts()} All windows secured — done.")
            break

    safe_print(f"{ts()} Done. Secured: {sorted(secured) or 'nothing'}")


def run_immediate_mode(cookies, session, ref, tz):
    """Book whatever is available right now for the target day (classic flow).
    The time windows run in parallel; each books a single seat sequentially."""
    safe_print(f"{ts()} ── immediate mode — target +{BOOK_DAYS_AHEAD}d ──")
    sel = [(url, svc) for url, svc, _ in floors_of(ref)]
    if not sel:
        safe_print(f"{ts()} ⚠️ No floors match FLOORS={FLOORS} — aborting")
        return

    def handle(window):
        start = get_future_datetime(days_ahead=BOOK_DAYS_AHEAD, time_string=window['start'])
        end   = get_future_datetime(days_ahead=BOOK_DAYS_AHEAD, time_string=window['end'])
        client = BookingClient(copy.copy(cookies), customer_account_id=session.customer_account_id,
                               resource_urls=sel)
        resources = client.find_available_resources(start, end)
        if not resources:
            safe_print(f"{ts()} [{window['start']}] 0 available — skipping")
            return None
        return book_window(cookies, session.customer_account_id, sel, resources, window, tz)

    secured = set()
    with ThreadPoolExecutor(max_workers=len(BOOKING_TIMES)) as ex:
        futs = {ex.submit(handle, w): w for w in BOOKING_TIMES}
        for fut in as_completed(futs):
            w = futs[fut]
            if fut.result() in ('booked', 'limit'):
                secured.add(w['start'])
    safe_print(f"{ts()} Done. Secured: {sorted(secured) or 'nothing'}")


def main():
    tz = pytz.timezone(TIMEZONE)
    print(f"{ts()} Script started (mode={BOOKING_MODE})", flush=True)

    if not USERNAME or not PASSWORD:
        print(f"{ts()} ❌ Missing USERNAME or PASSWORD in .env")
        return False
    if not BOOKING_TIMES:
        print(f"{ts()} ❌ Missing timeslots in BOOKING_TIMES")
        return False

    session = AnnySession(USERNAME, PASSWORD, provider_name=SSO_PROVIDER)
    cookies = session.login()
    if not cookies:
        return False
    print(f"{ts()} ✅ Login successful via {session.provider.name}", flush=True)

    ref = BookingClient(cookies, customer_account_id=session.customer_account_id)
    # Discovery can transiently fail (API hiccup); retry, then abort cleanly rather
    # than proceeding with an empty resource list and crashing downstream.
    for attempt in range(3):
        if ref.discover_all_floors():
            break
        if attempt < 2:
            print(f"{ts()} ⚠️ Floor discovery failed — retrying...", flush=True)
            time.sleep(2)
    else:
        print(f"{ts()} ❌ Could not discover any floors — aborting.", flush=True)
        return False
    load_favorites(ref)

    if DISCOVER_SLOTS:
        ref.discover_available_slots()

    if BOOKING_MODE == "immediate":
        run_immediate_mode(cookies, session, ref, tz)
    else:
        run_opening_mode(cookies, session, ref, tz)


if __name__ == "__main__":
    main()
