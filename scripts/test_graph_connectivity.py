import logging

import requests

from utcm_exporter.auth import get_access_token

LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    LOGGER.info("Calling Microsoft Graph /v1.0/organization")
    response = requests.get(
        "https://graph.microsoft.com/v1.0/organization",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    organizations = payload.get("value", [])
    if not organizations:
        LOGGER.warning("No organization records were returned")
        return

    for org in organizations:
        LOGGER.info(
            "Connected tenant: displayName=%s id=%s",
            org.get("displayName", "<unknown>"),
            org.get("id", "<unknown>"),
        )


if __name__ == "__main__":
    main()
