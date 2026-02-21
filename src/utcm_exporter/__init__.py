import logging


LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    LOGGER.info("UTCM exporter project initialized. Run scripts/test_graph_connectivity.py to validate auth.")
