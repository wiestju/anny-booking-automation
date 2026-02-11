import datetime
import os
import time

from dotenv import load_dotenv
from auth.session import AnnySession
from booking.client import BookingClient
from utils.helpers import get_future_datetime
import pytz
from config.constants import RESOURCE_ID, TIMEZONE, SSO_PROVIDER, BOOKING_TIMES

def main():
    load_dotenv('.env', override=True)
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    tz = pytz.timezone(TIMEZONE)

    if not username or not password:
        print("❌ Missing USERNAME or PASSWORD in .env")
        return

    session = AnnySession(username, password, provider_name=SSO_PROVIDER)
    cookies = session.login()

    if not cookies:
        return

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
            start = get_future_datetime(time_string=time_['start'])
            end = get_future_datetime(time_string=time_['end'])

            if RESOURCE_ID:
                resource_id = RESOURCE_ID
            else:
                resource_id = booking.find_available_resource(start, end)

            if resource_id:
                booking.reserve(resource_id, start, end)
            else:
                print("⚠️ No available slots found.")
        except Exception as e:
            print(f"❌ Error booking slot {time_['start']}-{time_['end']}: {e}")

if __name__ == "__main__":
    main()
