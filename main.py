import datetime
import os
import time

from dotenv import load_dotenv
from auth.session import AnnySession
from booking.client import BookingClient
from utils.helpers import get_future_datetime
import pytz
from config.constants import RESSOURCE_ID

def main():
    load_dotenv('.env', override=True)
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    start_time = datetime.datetime.now(pytz.timezone('Europe/Berlin'))

    if not username or not password:
        print("❌ Missing USERNAME or PASSWORD in .env")
        return

    session = AnnySession(username, password)
    cookies = session.login()

    if not cookies:
        return

    booking = BookingClient(cookies)

    while start_time.day == datetime.datetime.now(pytz.timezone('Europe/Berlin')).day:
        time.sleep(1)

    times = [
        {
            'start': '13:00:00',
            'end': '18:00:00'
        },
        {
            'start': '08:00:00',
            'end': '12:00:00'
        },
        {
            'start': '19:00:00',
            'end': '21:00:00'
        },
    ]

    for time_ in times:

        start = get_future_datetime(hour=time_['start'])
        end = get_future_datetime(hour=time_['end'])

        if RESSOURCE_ID:
            resource_id = RESSOURCE_ID
        else:
            resource_id = booking.find_available_resource(start, end)

        if resource_id:
            booking.reserve(resource_id, start, end)
        else:
            print("⚠️ No available slots found.")

if __name__ == "__main__":
    main()
