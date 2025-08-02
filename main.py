import os
from dotenv import load_dotenv
from auth.session import AnnySession
from booking.client import BookingClient
from utils.helpers import get_future_datetime

def main():
    load_dotenv('.env', override=True)
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    if not username or not password:
        print("❌ Missing USERNAME or PASSWORD in .env")
        return

    session = AnnySession(username, password)
    cookies = session.login()

    if not cookies:
        return

    booking = BookingClient(cookies)
    start = get_future_datetime(hour="13:00:00")
    end = get_future_datetime(hour="18:00:00")

    resource_id = booking.find_available_resource(start, end)

    if resource_id:
        booking.reserve(resource_id, start, end)
    else:
        print("⚠️ No available slots found.")

if __name__ == "__main__":
    main()
