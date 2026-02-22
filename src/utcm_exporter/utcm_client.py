import logging
import time
from datetime import UTC, datetime
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


def _extract_graph_error_text(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or "<no response body>"

    error_obj = payload.get("error")
    if isinstance(error_obj, dict):
        code = error_obj.get("code", "unknown")
        message = error_obj.get("message", "No message returned")
        details = error_obj.get("details")
        if isinstance(details, list) and details:
            detail_messages: list[str] = []
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                detail_code = detail.get("code", "unknown")
                detail_message = detail.get("message", "")
                target = detail.get("target")
                if target:
                    detail_messages.append(
                        f"{detail_code} ({target}): {detail_message}"
                    )
                else:
                    detail_messages.append(f"{detail_code}: {detail_message}")
            if detail_messages:
                return f"{code}: {message} | details: {'; '.join(detail_messages)}"
        return f"{code}: {message}"
    return str(payload)


def _find_latest_active_job(headers: dict[str, str]) -> str | None:
    jobs_url = f"{_GRAPH_BETA_BASE}/admin/configurationManagement/configurationSnapshotJobs?$top=50"
    response = requests.get(jobs_url, headers=headers, timeout=30)
    response.raise_for_status()

    payload = response.json()
    jobs = payload.get("value", [])
    if not isinstance(jobs, list):
        return None

    active_statuses = {"notstarted", "running"}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        status = str(job.get("status", "")).lower()
        if status in active_statuses:
            active_job_id = _extract_job_id(job)
            LOGGER.info(
                "Reusing active snapshot job %s with status=%s after 409 conflict",
                active_job_id,
                status,
            )
            return active_job_id

    return None


def _create_snapshot_request(
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> requests.Response:
    return requests.post(
        _CREATE_SNAPSHOT_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )


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
    create_response = _create_snapshot_request(headers=headers, payload=payload)
    if create_response.status_code == 409:
        graph_error = _extract_graph_error_text(create_response)
        LOGGER.warning("createSnapshot returned 409 conflict: %s", graph_error)
        job_id = _find_latest_active_job(headers)
        if job_id:
            LOGGER.info("Continuing with existing active snapshot job: %s", job_id)
        else:
            retry_display_name = (
                f"{display_name} {datetime.now(UTC).strftime('%Y%m%d %H%M%S')}"
            )
            retry_payload = {**payload, "displayName": retry_display_name}
            LOGGER.info(
                "Retrying createSnapshot with unique displayName: %s",
                retry_display_name,
            )
            retry_response = _create_snapshot_request(
                headers=headers,
                payload=retry_payload,
            )
            if not retry_response.ok:
                retry_error = _extract_graph_error_text(retry_response)
                raise UTCMClientError(
                    "createSnapshot returned 409 and retry with unique displayName failed. "
                    f"Initial error: {graph_error}. Retry error (HTTP {retry_response.status_code}): {retry_error}"
                )
            create_payload = retry_response.json()
            job_id = _extract_job_id(create_payload)
            LOGGER.info("Created snapshot job on retry: %s", job_id)
    else:
        if not create_response.ok:
            graph_error = _extract_graph_error_text(create_response)
            raise UTCMClientError(
                f"createSnapshot failed with HTTP {create_response.status_code}: {graph_error}"
            )
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
