import argparse
import logging

from utcm_exporter.utcm_client import cleanup_snapshot_jobs

LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete old UTCM snapshot jobs based on age and status.",
    )
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=7,
        help="Delete jobs older than this many days (default: 7).",
    )
    parser.add_argument(
        "--statuses",
        nargs="+",
        default=["succeeded", "failed", "cancelled", "canceled"],
        help=(
            "Statuses eligible for deletion. "
            "Default: succeeded failed cancelled canceled"
        ),
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=500,
        help="Maximum number of jobs to inspect from Graph (default: 500).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log jobs that would be deleted without deleting them.",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    args = _build_parser().parse_args()

    deleted_or_selected = cleanup_snapshot_jobs(
        older_than_days=args.older_than_days,
        statuses=set(args.statuses),
        dry_run=args.dry_run,
        max_jobs=args.max_jobs,
    )
    action_label = "matched (dry run)" if args.dry_run else "deleted"
    LOGGER.info("Snapshot jobs %s: %d", action_label, len(deleted_or_selected))


if __name__ == "__main__":
    main()
