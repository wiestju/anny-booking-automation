import pytest

from utils.helpers import extract_html_value, get_future_datetime


class TestExtractHtmlValue:
    def test_extracts_first_group(self):
        html = '<form action="https://sso.example/consume">'
        assert extract_html_value(html, r'form action="([^"]+)"') == "https://sso.example/consume"

    def test_unescapes_entities(self):
        html = 'value="a &amp; b"'
        assert extract_html_value(html, r'value="([^"]+)"') == "a & b"

    def test_raises_when_not_found(self):
        with pytest.raises(ValueError):
            extract_html_value("nothing here", r'value="([^"]+)"')


class TestGetFutureDatetime:
    def test_returns_iso_with_requested_time(self):
        out = get_future_datetime(days_ahead=3, time_string="09:00:00")
        # ISO 8601 with timezone offset, at the requested wall-clock time
        assert "T09:00:00" in out
        assert out.endswith("+02:00") or out.endswith("+01:00")  # CEST / CET

    def test_end_time_after_start_time(self):
        start = get_future_datetime(days_ahead=4, time_string="14:00:00")
        end = get_future_datetime(days_ahead=4, time_string="19:00:00")
        assert start < end
