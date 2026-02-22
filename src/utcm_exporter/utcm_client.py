import logging
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from utcm_exporter.auth import get_access_token

LOGGER = logging.getLogger(__name__)

_GRAPH_BETA_BASE = "https://graph.microsoft.com/beta"
_CREATE_SNAPSHOT_URL = (
    f"{_GRAPH_BETA_BASE}/admin/configurationManagement/configurationSnapshots/createSnapshot"
)
_SNAPSHOT_JOBS_URL = (
    f"{_GRAPH_BETA_BASE}/admin/configurationManagement/configurationSnapshotJobs"
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

        if status in {"succeeded", "partiallySuccessful"}:
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


def _sanitize_display_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _build_unique_display_name(base_name: str) -> str:
    sanitized_base = _sanitize_display_name(base_name) or "GitBackup"
    timestamp = datetime.now(UTC).strftime("%Y%m%d %H%M%S")
    suffix = f" {timestamp}"

    # UTCM validation constraints: length 8..32 and only letters/numbers/spaces.
    max_base_len = 32 - len(suffix)
    truncated_base = sanitized_base[:max_base_len].rstrip() if max_base_len > 0 else ""
    candidate = f"{truncated_base}{suffix}".strip()

    if len(candidate) < 8:
        fallback = "GitBackup"
        max_fallback_len = 32 - len(suffix)
        candidate = f"{fallback[:max_fallback_len]}{suffix}".strip()

    return candidate


def _parse_graph_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def list_snapshot_jobs(*, max_jobs: int = 500) -> list[dict[str, Any]]:
    access_token = get_access_token()
    headers = _build_headers(access_token)

    jobs: list[dict[str, Any]] = []
    next_url = f"{_SNAPSHOT_JOBS_URL}?$top=50"

    while next_url and len(jobs) < max_jobs:
        response = requests.get(next_url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()

        page_items = payload.get("value", [])
        if isinstance(page_items, list):
            for item in page_items:
                if isinstance(item, dict):
                    jobs.append(item)
                    if len(jobs) >= max_jobs:
                        break

        next_link = payload.get("@odata.nextLink")
        next_url = str(next_link) if next_link else ""

    return jobs


def delete_snapshot_job(job_id: str) -> None:
    access_token = get_access_token()
    headers = _build_headers(access_token)
    url = f"{_SNAPSHOT_JOBS_URL}/{job_id}"
    response = requests.delete(url, headers=headers, timeout=30)
    if response.status_code not in (200, 202, 204):
        graph_error = _extract_graph_error_text(response)
        raise UTCMClientError(
            f"Failed to delete snapshot job {job_id} (HTTP {response.status_code}): {graph_error}"
        )


def cleanup_snapshot_jobs(
    *,
    older_than_days: int = 7,
    statuses: set[str] | None = None,
    dry_run: bool = False,
    max_jobs: int = 500,
) -> list[str]:
    target_statuses = statuses or {"succeeded", "failed", "cancelled", "canceled"}
    normalized_statuses = {status.lower() for status in target_statuses}
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)

    jobs = list_snapshot_jobs(max_jobs=max_jobs)
    deleted_ids: list[str] = []

    for job in jobs:
        status = str(job.get("status", "")).lower()
        if status not in normalized_statuses:
            continue

        created_at = _parse_graph_datetime(job.get("createdDateTime"))
        if created_at is None:
            continue
        if created_at >= cutoff:
            continue

        job_id = _extract_job_id(job)
        if dry_run:
            LOGGER.info(
                "Dry run: would delete snapshot job %s (status=%s, createdDateTime=%s)",
                job_id,
                status,
                created_at.isoformat(),
            )
            deleted_ids.append(job_id)
            continue

        LOGGER.info(
            "Deleting snapshot job %s (status=%s, createdDateTime=%s)",
            job_id,
            status,
            created_at.isoformat(),
        )
        delete_snapshot_job(job_id)
        deleted_ids.append(job_id)

    return deleted_ids


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
    initial_display_name = _build_unique_display_name(display_name)
    payload = {
        "displayName": initial_display_name,
        "description": description,
        "resources": snapshot_resources,
    }

    LOGGER.info(
        "Creating UTCM snapshot job for %d resources using displayName='%s'",
        len(snapshot_resources),
        initial_display_name,
    )
    create_response = _create_snapshot_request(headers=headers, payload=payload)
    if create_response.status_code == 409:
        graph_error = _extract_graph_error_text(create_response)
        LOGGER.warning("createSnapshot returned 409 conflict: %s", graph_error)
        job_id = _find_latest_active_job(headers)
        if job_id:
            LOGGER.info("Continuing with existing active snapshot job: %s", job_id)
        else:
            retry_display_name = _build_unique_display_name(display_name)
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
