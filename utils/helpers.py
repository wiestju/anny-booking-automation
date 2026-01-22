import re
import html
import datetime
import pytz
from config.constants import TIMEZONE

def get_future_datetime(days_ahead=3, hour="13:00:00"):
    dt = datetime.datetime.now(pytz.timezone(TIMEZONE)) + datetime.timedelta(days=days_ahead)
    return dt.strftime(f"%Y-%m-%dT{hour}+02:00")

def extract_html_value(text, pattern):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Pattern not found: {pattern}")
    return html.unescape(match.group(1))
