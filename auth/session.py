import requests
import urllib.parse
import re
from config.constants import AUTH_BASE_URL, ANNY_BASE_URL, DEFAULT_HEADERS
from utils.helpers import extract_html_value
from auth.providers import get_provider, SSOProvider


class AnnySession:
    def __init__(self, username: str, password: str, provider_name: str):
        self.session = requests.Session()
        self.username = username
        self.password = password

        # Initialize the SSO provider
        provider_class = get_provider(provider_name)
        self.provider: SSOProvider = provider_class(username, password)

    def login(self):
        try:
            self._init_headers()
            self._sso_login()
            self._provider_auth()
            self._consume_saml()
            print(f"✅ Login successful via {self.provider.name}.")
            return self.session.cookies
        except requests.RequestException as e:
            print(f"[Login Error] Network error: {type(e).__name__}")
            return None
        except ValueError as e:
            print(f"[Login Error] {e}")
            return None
        except KeyError as e:
            print(f"[Login Error] Missing expected field: {e}")
            return None

    def _init_headers(self):
        self.session.headers.update({
            **DEFAULT_HEADERS,
            'accept': 'text/html, application/xhtml+xml',
            'referer': AUTH_BASE_URL + '/',
            'origin': AUTH_BASE_URL
        })

    def _sso_login(self):
        r1 = self.session.get(f"{AUTH_BASE_URL}/login/sso")
        self.session.headers['X-XSRF-TOKEN'] = urllib.parse.unquote(r1.cookies['XSRF-TOKEN'])

        page_data = extract_html_value(r1.text, r'data-page="(.*?)"')
        version = re.search(r'"version"\s*:\s*"([a-f0-9]{32})"', page_data)
        x_inertia_version = version.group(1) if version else '66b32acea13402d3aef4488ccd239c93'

        self.session.headers.update({
            'x-requested-with': 'XMLHttpRequest',
            'x-inertia': 'true',
            'x-inertia-version': x_inertia_version
        })

        r2 = self.session.post(f"{AUTH_BASE_URL}/login/sso", json={"domain": self.provider.domain})
        redirect_url = r2.headers['x-inertia-location']
        redirect_response = self.session.get(redirect_url)

        # Pass session and redirect response to provider
        self.provider.set_session(self.session)
        self.provider.set_redirect_response(redirect_response)

    def _provider_auth(self):
        """Delegate authentication to the SSO provider."""
        self.saml_response_html = self.provider.authenticate()

    def _consume_saml(self):
        consume_url = extract_html_value(self.saml_response_html, r'form action="([^"]+)"')
        relay_state = extract_html_value(self.saml_response_html, r'name="RelayState" value="([^"]+)"')
        saml_response = extract_html_value(self.saml_response_html, r'name="SAMLResponse" value="([^"]+)"')

        self.session.post(consume_url, data={
            'RelayState': relay_state,
            'SAMLResponse': saml_response
        })

        self.session.get(f"{ANNY_BASE_URL}/en-us/login?target=/en-us/home?withoutIntent=true")
