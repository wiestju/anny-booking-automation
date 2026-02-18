import re
import html
import datetime
import pytz
from config.constants import TIMEZONE

def get_future_datetime(days_ahead=3, time_string="13:00:00"):
    tz = pytz.timezone(TIMEZONE)
    h, m, s = [int(h) for h in time_string.split(":")]
    dt = datetime.datetime.now(tz=tz) + datetime.timedelta(days=days_ahead)
    dt_correct_time = tz.localize(datetime.datetime(dt.year, dt.month, dt.day, h, m, s))
    return dt_correct_time.strftime(f"%Y-%m-%dT%H:%M:%S%:z")

def extract_html_value(text, pattern):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Pattern not found: {pattern}")
    return html.unescape(match.group(1))
