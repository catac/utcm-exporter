import argparse
import logging

from utcm_exporter.parser import download_and_parse_snapshot

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
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    args = _build_parser().parse_args()
    written_files = download_and_parse_snapshot(
        resource_location=args.resource_location,
        output_root=args.output_dir,
    )
    LOGGER.info("Parser finished. Files written: %d", len(written_files))


if __name__ == "__main__":
    main()
