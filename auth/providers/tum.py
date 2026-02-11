import html
from auth.providers.base import SSOProvider
from utils.helpers import extract_html_value


class TUMProvider(SSOProvider):
    """SSO provider for Technical University of Munich (TUM)."""

    name = "TUM"
    domain = "tum.de"
    available_days_ahead = 4

    def authenticate(self) -> str:
        self.session.headers.pop('x-requested-with', None)
        self.session.headers.pop('x-inertia', None)
        self.session.headers.pop('x-inertia-version', None)

        csrf_token = extract_html_value(
            self.redirect_response.text,
            r'name="csrf_token" value="([^"]+)"'
        )

        # First request to get correct CSRF token
        response = self.session.post(
            self.redirect_response.url,
            data={
                'csrf_token': csrf_token,
                'shib_idp_ls_exception.shib_idp_session_ss': '',
                'shib_idp_ls_success.shib_idp_session_ss': 'true',
                'shib_idp_ls_value.shib_idp_session_ss': '',
                'shib_idp_ls_exception.shib_idp_persistent_ss': '',
                'shib_idp_ls_success.shib_idp_persistent_ss': 'true',
                'shib_idp_ls_value.shib_idp_persistent_ss': '',
                'shib_idp_ls_supported': 'true',
                '_eventId_proceed': ''
            }
        )

        old_referer = self.session.headers.get('referer')
        self.session.headers.update({
            'referer': response.url
        })

        csrf_token = extract_html_value(
            response.text,
            r'name="csrf_token" value="([^"]+)"'
        )

        # Second request to get SAML response
        response = self.session.post(
            response.url,
            data={
                'csrf_token': csrf_token,
                'j_username': self.username,
                'j_password': self.password,
                'donotcache': '1',
                '_eventId_proceed': '',
            }
        )

        if "/consume" not in html.unescape(response.text):
            raise ValueError("TUM authentication failed - invalid credentials or SSO error")

        self.session.headers.update({
            'referer': old_referer
        })

        return response.text
