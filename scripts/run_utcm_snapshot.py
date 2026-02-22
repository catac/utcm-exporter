import argparse
import logging

from utcm_exporter.resources_catalog import load_resources_from_file
from utcm_exporter.utcm_client import create_snapshot_and_wait

LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a UTCM snapshot job. By default resources are loaded from resources.json."
        ),
    )
    parser.add_argument(
        "--resources-file",
        default="resources.json",
        help="Path to resources catalog JSON file (default: resources.json).",
    )
    parser.add_argument(
        "--resources",
        nargs="+",
        default=[],
        help=(
            "Optional resource list override for test runs. "
            "Examples: microsoft.entra.conditionalaccesspolicy "
            "microsoft.teams.meetingpolicy"
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=7200,
        help="Snapshot polling timeout in seconds (default: 7200).",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=10,
        help="Polling interval in seconds (default: 10).",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    args = _build_parser().parse_args()

    if args.resources:
        resources = sorted({item.strip() for item in args.resources if item.strip()})
        LOGGER.info(
            "Using %d resource(s) from --resources override",
            len(resources),
        )
    else:
        resources = load_resources_from_file(args.resources_file)
        LOGGER.info(
            "Loaded %d UTCM resources from %s",
            len(resources),
            args.resources_file,
        )

    job_id, resource_location = create_snapshot_and_wait(
        resources=resources,
        poll_interval_seconds=args.poll_interval_seconds,
        timeout_seconds=args.timeout_seconds,
    )

    LOGGER.info("UTCM snapshot job succeeded: %s", job_id)
    print(resource_location)


if __name__ == "__main__":
    main()
