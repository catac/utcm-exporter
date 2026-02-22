import logging

from utcm_exporter.utcm_client import create_snapshot_and_wait

LOGGER = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    job_id, resource_location = create_snapshot_and_wait(
        resources=[
            "microsoft.entra.application",
            "microsoft.entra.namedlocationpolicy",
            "microsoft.entra.conditionalaccesspolicy",
            "microsoft.entra.grouplifecyclepolicy",
            "microsoft.entra.serviceprincipal",
            "microsoft.securityandcompliance.dlpcompliancepolicy",
            "microsoft.teams.meetingpolicy",
        ],
        poll_interval_seconds=10,
        timeout_seconds=900,
    )

    LOGGER.info("UTCM snapshot job succeeded: %s", job_id)
    print(resource_location)


if __name__ == "__main__":
    main()
