import argparse
import logging

from utcm_exporter.resources_catalog import (
    build_resource_catalog_from_docs,
    write_resource_catalog,
)

LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build resources.json from official UTCM Microsoft Graph docs pages.",
    )
    parser.add_argument(
        "--output",
        default="resources.json",
        help="Path to write generated resource catalog (default: resources.json)",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    args = _build_parser().parse_args()

    catalog = build_resource_catalog_from_docs()
    out = write_resource_catalog(args.output, catalog)
    LOGGER.info("Wrote resource catalog: %s", out)
    LOGGER.info("Discovered %d supported UTCM resources", catalog["resourceCount"])


if __name__ == "__main__":
    main()
