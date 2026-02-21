import logging
import re
from pathlib import Path
from typing import Any

import requests
import yaml

from utcm_exporter.auth import get_access_token

LOGGER = logging.getLogger(__name__)

_INVALID_FILENAME_CHARS = re.compile(r"[\\/:*?\"<>|]")
_NAME_KEYS = ("displayName", "name", "id", "DisplayName", "Name", "Id", "ID")


class SnapshotParserError(RuntimeError):
    """Raised when snapshot download or parse operations fail."""


def sanitize_filename(value: str) -> str:
    sanitized = _INVALID_FILENAME_CHARS.sub("_", value).strip()
    sanitized = re.sub(r"\s+", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized or "unnamed"


def download_snapshot_json(resource_location: str) -> dict[str, Any]:
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    LOGGER.info("Downloading snapshot JSON from resourceLocation")
    response = requests.get(resource_location, headers=headers, timeout=60)
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        raise SnapshotParserError(
            f"Expected snapshot payload to be a JSON object, got {type(payload).__name__}"
        )
    return payload


def _derive_folder_names(resource_type: str) -> tuple[str, str]:
    parts = resource_type.lower().split(".")
    workload = parts[1] if len(parts) > 1 else "unknown"
    resource_folder = parts[-1] if parts else "unknown"
    return sanitize_filename(workload), sanitize_filename(resource_folder)


def _looks_like_instance(candidate: dict[str, Any]) -> bool:
    return any(key in candidate for key in _NAME_KEYS)


def _extract_instances(resource: dict[str, Any]) -> list[tuple[dict[str, Any], str | None]]:
    properties = resource.get("properties")
    instances: list[tuple[dict[str, Any], str | None]] = []

    if isinstance(properties, list):
        for item in properties:
            if isinstance(item, dict):
                instances.append((item, None))
        return instances

    if isinstance(properties, dict):
        if _looks_like_instance(properties):
            return [(properties, None)]

        list_keys = ("items", "value", "values", "instances", "resources")
        for list_key in list_keys:
            candidate_list = properties.get(list_key)
            if isinstance(candidate_list, list):
                for item in candidate_list:
                    if isinstance(item, dict):
                        instances.append((item, None))
                if instances:
                    return instances

        for key, value in properties.items():
            if isinstance(value, dict):
                instances.append((value, key))
            elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
                for idx, item in enumerate(value, start=1):
                    instances.append((item, f"{key}_{idx}"))

        if instances:
            return instances
        return [(properties, None)]

    if isinstance(resource, dict):
        return [(resource, None)]

    return []


def _resolve_instance_name(
    *,
    instance: dict[str, Any],
    suggested_name: str | None,
    default_name: str,
) -> str:
    for key in _NAME_KEYS:
        value = instance.get(key)
        if value is not None and str(value).strip():
            return str(value)
    if suggested_name and suggested_name.strip():
        return suggested_name
    return default_name


def _dedupe_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2

    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def parse_snapshot_to_yaml(
    snapshot_payload: dict[str, Any],
    output_root: Path | str = Path("tenant_state"),
) -> list[Path]:
    output_base = Path(output_root)
    resources = snapshot_payload.get("resources", [])
    if not isinstance(resources, list):
        raise SnapshotParserError("Snapshot JSON does not contain a list at 'resources'")

    written_files: list[Path] = []
    if not resources:
        LOGGER.warning("Snapshot payload contains no resources")
        return written_files

    for resource in resources:
        if not isinstance(resource, dict):
            LOGGER.warning("Skipping non-object resource entry")
            continue

        resource_type = str(resource.get("resourceType", "unknown.unknown"))
        workload, resource_folder = _derive_folder_names(resource_type)
        target_dir = output_base / workload / resource_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        instances = _extract_instances(resource)
        if not instances:
            LOGGER.warning("No parseable instances for resourceType=%s", resource_type)
            continue

        for idx, (instance, suggested_name) in enumerate(instances, start=1):
            default_name = f"item_{idx:03d}"
            raw_name = _resolve_instance_name(
                instance=instance,
                suggested_name=suggested_name,
                default_name=default_name,
            )
            file_name = f"{sanitize_filename(raw_name)}.yaml"
            file_path = _dedupe_path(target_dir / file_name)

            with file_path.open("w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    instance,
                    handle,
                    sort_keys=True,
                    indent=2,
                    default_flow_style=False,
                    allow_unicode=False,
                )

            written_files.append(file_path)

    LOGGER.info("Wrote %d YAML resource files under %s", len(written_files), output_base)
    return written_files


def download_and_parse_snapshot(
    resource_location: str,
    output_root: Path | str = Path("tenant_state"),
) -> list[Path]:
    payload = download_snapshot_json(resource_location)
    return parse_snapshot_to_yaml(payload, output_root=output_root)
