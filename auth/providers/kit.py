import html
from auth.providers.base import SSOProvider
from utils.helpers import extract_html_value


class KITProvider(SSOProvider):
    """SSO provider for Karlsruhe Institute of Technology (KIT)."""

    name = "KIT"
    domain = "kit.edu"
    available_days_ahead = 3

    def authenticate(self) -> str:
        self.session.headers.pop('x-requested-with', None)
        self.session.headers.pop('x-inertia', None)
        self.session.headers.pop('x-inertia-version', None)

        csrf_token = extract_html_value(
            self.redirect_response.text,
            r'name="csrf_token" value="([^"]+)"'
        )

        response = self.session.post(
            'https://idp.scc.kit.edu/idp/profile/SAML2/Redirect/SSO?execution=e1s1',
            data={
                'csrf_token': csrf_token,
                'j_username': self.username,
                'j_password': self.password,
                '_eventId_proceed': '',
                'fudis_web_authn_assertion_input': '',
            }
        )

        if "/consume" not in html.unescape(response.text):
            raise ValueError("KIT authentication failed - invalid credentials or SSO error")

        return response.text
