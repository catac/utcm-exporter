import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from utcm_exporter.parser import download_snapshot_json, parse_snapshot_to_yaml

LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a UTCM snapshot JSON from resourceLocation and write YAML files.",
    )
    parser.add_argument(
        "resource_location",
        help="The Graph resourceLocation URL returned by configurationSnapshotJobs.",
    )
    parser.add_argument(
        "--output-dir",
        default="tenant_state",
        help="Output folder for parsed tenant state (default: tenant_state)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        default=True,
        help="Delete stale YAML files not present in the current snapshot output (default: on).",
    )
    parser.add_argument(
        "--no-clean",
        action="store_false",
        dest="clean",
        help="Disable pruning of stale YAML files.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Dump raw snapshot JSON to a debug file before parsing.",
    )
    parser.add_argument(
        "--debug-file",
        default="",
        help=(
            "Optional path for raw snapshot JSON dump. "
            "Default when --debug is set: output_dir/_debug/snapshot_<timestamp>.json"
        ),
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    args = _build_parser().parse_args()
    payload = download_snapshot_json(args.resource_location)

    if args.debug:
        if args.debug_file:
            debug_path = Path(args.debug_file)
        else:
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            debug_path = Path(args.output_dir) / "_debug" / f"snapshot_{ts}.json"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        with debug_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        LOGGER.info("Wrote debug snapshot JSON: %s", debug_path)

    written_files = parse_snapshot_to_yaml(
        snapshot_payload=payload,
        output_root=args.output_dir,
        clean=args.clean,
    )
    LOGGER.info("Parser finished. Files written: %d", len(written_files))


if __name__ == "__main__":
    main()
