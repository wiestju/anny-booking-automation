import datetime
import time

from auth.session import AnnySession
from booking.client import BookingClient, CheckoutException
from utils.helpers import get_future_datetime
import pytz
from config.constants import USERNAME, PASSWORD, RESOURCE_ID, USE_ANY_RESOURCE_ID, TIMEZONE, SSO_PROVIDER, BOOKING_TIMES

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

            if not USE_ANY_RESOURCE_ID:
                if not RESOURCE_ID or RESOURCE_ID not in r_ids_available:
                    print(f"⚠️ No available slots found for specified resource_id {RESOURCE_ID} for {time_['start']}-{time_['end']}")
                    break
                # specified resource id is available -> only use specified resource id
                r_ids_available = [RESOURCE_ID]
            elif RESOURCE_ID and RESOURCE_ID in r_ids_available:
                # specified resource id is available -> ensure specified resource id is tried first
                r_ids_available.insert(0, r_ids_available.pop(r_ids_available.index(RESOURCE_ID)))

            # Try all resource ids available until booking is successful
            for i, resource_id in enumerate(r_ids_available):
                try:
                    success = booking.reserve(resource_id, start, end)
                except CheckoutException:
                    # Reservation failed on checkout -> Booking limit exceeded for that timeslot -> try next booking time
                    print(f"⚠️ You have probably exceeded your booking limit for {time_['start']}-{time_['end']}")
                    break

                if success:
                    break

                print(f"  Attempt {i + 1}/{len(r_ids_available)}")
            else:
                print(f"⚠️ No available slots found for {time_['start']}-{time_['end']}")
        except Exception as e:
            print(f"❌ Error booking slot {time_['start']}-{time_['end']}: {e}")
            break

if __name__ == "__main__":
    main()
