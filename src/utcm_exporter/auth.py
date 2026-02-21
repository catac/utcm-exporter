import logging
import os
from typing import Sequence

from dotenv import load_dotenv
from msal import ConfidentialClientApplication

LOGGER = logging.getLogger(__name__)

_GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


class AuthConfigError(ValueError):
    """Raised when required auth environment variables are missing."""


def _read_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise AuthConfigError(f"Missing required environment variable: {name}")
    return value


def get_access_token(scopes: Sequence[str] | None = None) -> str:
    """Acquire an app-only Microsoft Graph access token using client credentials."""
    load_dotenv()

    tenant_id = _read_required_env("AZURE_TENANT_ID")
    client_id = _read_required_env("AZURE_CLIENT_ID")
    client_secret = _read_required_env("AZURE_CLIENT_SECRET")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    requested_scopes = list(scopes) if scopes else [_GRAPH_DEFAULT_SCOPE]

    app = ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )

    LOGGER.info("Acquiring app-only access token for Microsoft Graph")
    result = app.acquire_token_for_client(scopes=requested_scopes)

    access_token = result.get("access_token")
    if access_token:
        return access_token

    error = result.get("error", "unknown_error")
    description = result.get("error_description", "No description returned")
    correlation_id = result.get("correlation_id", "n/a")

    raise RuntimeError(
        "Failed to acquire access token "
        f"(error={error}, correlation_id={correlation_id}): {description}"
    )
