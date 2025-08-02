import requests
import urllib.parse
import re
import html
from config.constants import AUTH_BASE_URL, ANNY_BASE_URL, DEFAULT_HEADERS
from utils.helpers import extract_html_value

class AnnySession:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password

    def login(self):
        try:
            self._init_headers()
            self._sso_login()
            self._kit_auth()
            self._consume_saml()
            return self.session.cookies
        except Exception as e:
            print(f"[Login Error] {e}")
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

        r2 = self.session.post(f"{AUTH_BASE_URL}/login/sso", json={"domain": "kit.edu"})
        redirect_url = r2.headers['x-inertia-location']
        self.redirect_response = self.session.get(redirect_url)

    def _kit_auth(self):
        self.session.headers.pop('x-requested-with', None)
        self.session.headers.pop('x-inertia', None)
        self.session.headers.pop('x-inertia-version', None)

        csrf_token = extract_html_value(self.redirect_response.text, r'name="csrf_token" value="([^"]+)"')

        r4 = self.session.post(
            'https://idp.scc.kit.edu/idp/profile/SAML2/Redirect/SSO?execution=e1s1',
            data={
                'csrf_token': csrf_token,
                'j_username': self.username,
                'j_password': self.password,
                '_eventId_proceed': '',
                'fudis_web_authn_assertion_input': '',
            }
        )

        if "/consume" not in html.unescape(r4.text):
            raise Exception("KIT authentication failed")

        self.saml_response_html = r4.text

    def _consume_saml(self):
        consume_url = extract_html_value(self.saml_response_html, r'form action="([^"]+)"')
        relay_state = extract_html_value(self.saml_response_html, r'name="RelayState" value="([^"]+)"')
        saml_response = extract_html_value(self.saml_response_html, r'name="SAMLResponse" value="([^"]+)"')

        self.session.post(consume_url, data={
            'RelayState': relay_state,
            'SAMLResponse': saml_response
        })

        self.session.get(f"{ANNY_BASE_URL}/en-us/login?target=/en-us/home?withoutIntent=true")
