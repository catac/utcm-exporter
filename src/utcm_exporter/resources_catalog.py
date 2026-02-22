import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import requests

LOGGER = logging.getLogger(__name__)

_DOCS_BASE = "https://raw.githubusercontent.com/microsoftgraph/microsoft-graph-docs-contrib/main"
_DEFAULT_DOC_PAGES = [
    "concepts/utcm-entra-resources.md",
    "concepts/utcm-exchange-resources.md",
    "concepts/utcm-intune-resources.md",
    "concepts/utcm-securityandcompliance-resources.md",
    "concepts/utcm-sharepoint-resources.md",
    "concepts/utcm-teams-resources.md",
]
_INCLUDE_PATTERN = re.compile(r"\[!INCLUDE \[[^\]]+\]\(([^)]+)\)\]")


class ResourceCatalogError(RuntimeError):
    """Raised when UTCM resource catalog operations fail."""


def _fetch_text(url: str) -> str:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def _resource_from_include_path(include_path: str) -> str | None:
    file_name = Path(include_path).name
    stem = file_name.removesuffix(".md")
    if not stem.startswith("microsoft-"):
        return None

    remainder = stem[len("microsoft-") :]
    if "-" not in remainder:
        return None

    workload, resource = remainder.split("-", 1)
    workload = workload.strip().lower()
    resource = resource.strip().lower().replace("-", "")
    if not workload or not resource:
        return None

    return f"microsoft.{workload}.{resource}"


def _normalize_include_path(doc_page: str, include_path: str) -> str:
    clean = include_path.strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean
    if clean.startswith("/"):
        return f"{_DOCS_BASE}{clean}"

    page_dir = str(Path(doc_page).parent)
    if page_dir == ".":
        return f"{_DOCS_BASE}/{clean}"
    return f"{_DOCS_BASE}/{page_dir}/{clean}"


def build_resource_catalog_from_docs(
    doc_pages: list[str] | None = None,
) -> dict[str, object]:
    pages = doc_pages or _DEFAULT_DOC_PAGES
    discovered: set[str] = set()

    for page in pages:
        page_url = f"{_DOCS_BASE}/{page}"
        LOGGER.info("Fetching UTCM docs page: %s", page_url)
        try:
            markdown = _fetch_text(page_url)
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 404:
                LOGGER.warning("Skipping missing docs page: %s", page_url)
                continue
            raise

        include_paths = _INCLUDE_PATTERN.findall(markdown)
        for include_path in include_paths:
            normalized_url = _normalize_include_path(page, include_path)
            resource_id = _resource_from_include_path(include_path)
            if resource_id:
                discovered.add(resource_id)
            else:
                LOGGER.debug(
                    "Skipping include that does not map to a UTCM resource id: %s (%s)",
                    include_path,
                    normalized_url,
                )

    resources = sorted(discovered)
    if not resources:
        raise ResourceCatalogError("No resources were discovered from docs pages")

    return {
        "generatedFrom": "microsoft-graph-docs-contrib",
        "generatedAtUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resourceCount": len(resources),
        "resources": resources,
    }


def write_resource_catalog(output_path: Path | str, catalog: dict[str, object]) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return out


def load_resources_from_file(path: Path | str = Path("resources.json")) -> list[str]:
    config_path = Path(path)
    if not config_path.exists():
        raise ResourceCatalogError(
            f"Resource catalog not found: {config_path}. Run scripts/build_resources_catalog.py first."
        )

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ResourceCatalogError(f"Resource catalog is not valid JSON: {config_path}") from exc

    resources = payload.get("resources") if isinstance(payload, dict) else None
    if not isinstance(resources, list) or not all(isinstance(item, str) for item in resources):
        raise ResourceCatalogError(
            f"Resource catalog has invalid 'resources' format in {config_path}"
        )

    cleaned = sorted({item.strip() for item in resources if item.strip()})
    if not cleaned:
        raise ResourceCatalogError(f"Resource catalog contains no resources: {config_path}")
    return cleaned
