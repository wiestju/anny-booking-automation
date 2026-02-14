import datetime
import time

from auth.session import AnnySession
from booking.client import BookingClient, CheckoutException
from utils.helpers import get_future_datetime
import pytz
from config.constants import USERNAME, PASSWORD, RESOURCE_IDS, USE_ANY_RESOURCE_ID, TIMEZONE, SSO_PROVIDER, BOOKING_TIMES

def main():
    tz = pytz.timezone(TIMEZONE)

    if not USERNAME or not PASSWORD:
        print("❌ Missing USERNAME or PASSWORD in .env")
        return False

    if not BOOKING_TIMES:
        print("❌ Missing timeslots in BOOKING_TIMES")
        return False

    session = AnnySession(USERNAME, PASSWORD, provider_name=SSO_PROVIDER)
    cookies = session.login()

    if not cookies:
        return False

    booking = BookingClient(cookies)

    # Only wait for midnight if within 10 minutes, otherwise execute immediately
    now = datetime.datetime.now(tz)
    midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until_midnight = (midnight - now).total_seconds()
    max_wait_seconds = 10 * 60  # 10 minutes

    if 0 < seconds_until_midnight <= max_wait_seconds:
        print(f"⏳ Waiting {seconds_until_midnight:.0f} seconds until midnight...")
        time.sleep(seconds_until_midnight)
    elif seconds_until_midnight > max_wait_seconds:
        print(f"⚡ More than 10 min until midnight, executing immediately...")

    for time_ in BOOKING_TIMES:
        try:
            days_ahead = session.provider.available_days_ahead
            start = get_future_datetime(days_ahead=days_ahead, time_string=time_['start'])
            end = get_future_datetime(days_ahead=days_ahead, time_string=time_['end'])

            r_ids_available = booking.find_available_resources(start, end)

            r_ids_book = []
            for r_id_av in RESOURCE_IDS:
                if r_id_av in r_ids_available:
                    r_ids_book.append(r_id_av)
                    r_ids_available.remove(r_id_av)

            if USE_ANY_RESOURCE_ID:
                r_ids_book += r_ids_available

            # Iterate through resource ids until booking is successful
            for i, r_id in enumerate(r_ids_book):
                try:
                    success = booking.reserve(r_id, start, end)
                except CheckoutException:
                    # Reservation failed on checkout -> Booking limit exceeded for that timeslot -> try next booking time
                    print(f"⚠️ You have probably exceeded your booking limit for {time_['start']}-{time_['end']}")
                    break

                if success:
                    break

                print(f"  Attempt {i + 1}/{len(r_ids_book)}")
            else:
                print(f"⚠️ No available slots found for {time_['start']}-{time_['end']}")
        except Exception as e:
            print(f"❌ Error booking slot {time_['start']}-{time_['end']}: {e}")
            break

if __name__ == "__main__":
    main()
