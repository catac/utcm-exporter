import logging
import time
from typing import Any

import requests

from utcm_exporter.auth import get_access_token

LOGGER = logging.getLogger(__name__)

_GRAPH_BETA_BASE = "https://graph.microsoft.com/beta"
_CREATE_SNAPSHOT_URL = (
    f"{_GRAPH_BETA_BASE}/admin/configurationManagement/configurationSnapshots/createSnapshot"
)

_TEST_RESOURCES = [
    "microsoft.entra.conditionalaccesspolicy",
    "microsoft.entra.grouplifecyclepolicy",
]


class UTCMClientError(RuntimeError):
    """Raised when UTCM snapshot operations fail."""


def _build_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _extract_job_id(snapshot_job: dict[str, Any]) -> str:
    job_id = snapshot_job.get("jobId") or snapshot_job.get("id")
    if not job_id:
        raise UTCMClientError(
            "Snapshot job response did not include 'jobId' or 'id'. "
            f"Response keys: {sorted(snapshot_job.keys())}"
        )
    return str(job_id)


def _poll_snapshot_job(
    *,
    headers: dict[str, str],
    job_id: str,
    poll_interval_seconds: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    status_url = (
        f"{_GRAPH_BETA_BASE}/admin/configurationManagement/configurationSnapshotJobs/{job_id}"
    )
    deadline = time.monotonic() + timeout_seconds

    while True:
        response = requests.get(status_url, headers=headers, timeout=30)
        response.raise_for_status()

        job_payload = response.json()
        status = job_payload.get("status", "unknown")
        LOGGER.info("Snapshot job %s status: %s", job_id, status)

        if status == "succeeded":
            return job_payload

        if status in {"failed", "cancelled", "canceled"}:
            raise UTCMClientError(
                f"Snapshot job {job_id} ended with status '{status}': {job_payload}"
            )

        if time.monotonic() >= deadline:
            raise UTCMClientError(
                f"Timed out waiting for snapshot job {job_id} after {timeout_seconds}s"
            )

        time.sleep(poll_interval_seconds)


def create_snapshot_and_wait(
    *,
    display_name: str = "GitBackup",
    description: str = "Automated Backup",
    resources: list[str] | None = None,
    poll_interval_seconds: int = 10,
    timeout_seconds: int = 900,
) -> tuple[str, str]:
    """Create a UTCM snapshot job and wait for completion.

    Returns:
        tuple[str, str]: (job_id, resource_location)
    """
    access_token = get_access_token()
    headers = _build_headers(access_token)

    snapshot_resources = resources or _TEST_RESOURCES
    payload = {
        "displayName": display_name,
        "description": description,
        "resources": snapshot_resources,
    }

    LOGGER.info("Creating UTCM snapshot job for %d resources", len(snapshot_resources))
    create_response = requests.post(
        _CREATE_SNAPSHOT_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    create_response.raise_for_status()

    create_payload = create_response.json()
    job_id = _extract_job_id(create_payload)
    LOGGER.info("Created snapshot job: %s", job_id)

    completed_job = _poll_snapshot_job(
        headers=headers,
        job_id=job_id,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )

    resource_location = completed_job.get("resourceLocation")
    if not resource_location:
        raise UTCMClientError(
            f"Snapshot job {job_id} succeeded but 'resourceLocation' is missing: {completed_job}"
        )

    LOGGER.info("Snapshot job %s completed", job_id)
    return job_id, str(resource_location)
