from abc import ABC, abstractmethod
import requests


class SSOProvider(ABC):
    """Base class for SSO authentication providers."""

    # Override these in subclasses
    name: str = "base"
    domain: str = ""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session: requests.Session = None
        self.redirect_response: requests.Response = None
        self.saml_response_html: str = None

    def set_session(self, session: requests.Session):
        """Set the shared session from AnnySession."""
        self.session = session

    def set_redirect_response(self, response: requests.Response):
        """Set the redirect response from Anny SSO initiation."""
        self.redirect_response = response

    @abstractmethod
    def authenticate(self) -> str:
        """
        Perform institution-specific authentication.

        Returns:
            The HTML containing the SAML response, or raises an exception on failure.
        """
        pass
