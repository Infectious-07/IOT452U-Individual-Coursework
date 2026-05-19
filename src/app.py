from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping

from config import Settings, load
from database import AuditRepository, IdentityRepository, bootstrap, connect
from models import OrganisationRole, Portal, generate_identity_id, generate_tax_reference
from portals import (
    build_central_portal,
    build_dvla_portal,
    build_employer_portal,
    build_tax_portal,
)
from services import (
    AuditService,
    ExportService,
    IdentityService,
    NewIdentity,
    StatsService,
    VerificationService,
)
from shell import MenuShell


def build_portals(
    identity_service: IdentityService,
    audit_service: AuditService,
    verification: VerificationService,
    export_service: ExportService,
    stats_service: StatsService,
    id_generator: Callable[[], str] | None = None,
) -> Mapping[OrganisationRole, Portal]:
    return {
        OrganisationRole.CENTRAL_AUTHORITY: build_central_portal(
            identity_service, audit_service, export_service, stats_service,
            id_generator=id_generator,
        ),
        OrganisationRole.TAX: build_tax_portal(verification),
        OrganisationRole.DVLA: build_dvla_portal(verification),
        OrganisationRole.EMPLOYER: build_employer_portal(verification),
    }


# --- sample data seeding ---


_SAMPLE_PEOPLE = [
    {
        "name": "Ada Lovelace",
        "dob": "1990-03-15",
        "nationality": "GB",
        "postcode": "SW1A 2AA",
        "tax_band": "HIGHER",
        "driving_entitlements": "B,C1",
        "driving_restrictions": "GLASSES",
        "right_to_work": True,
        "residency_status": "CITIZEN",
    },
    {
        "name": "Alan Turing",
        "dob": "1985-06-23",
        "nationality": "GB",
        "postcode": "MK7 6AA",
        "tax_band": "ADDITIONAL",
        "driving_entitlements": "A,B",
        "right_to_work": True,
        "residency_status": "CITIZEN",
    },
    {
        "name": "Grace Hopper",
        "dob": "1992-12-09",
        "nationality": "US",
        "postcode": "EC2R 8AH",
        "tax_band": "BASIC",
        "driving_entitlements": "B",
        "driving_restrictions": "AUTOMATIC_ONLY",
        "right_to_work": True,
        "residency_status": "RESIDENT",
    },
    {
        "name": "Linus Torvalds",
        "dob": "1988-12-28",
        "nationality": "FI",
        "postcode": "M1 1AE",
        "tax_band": "HIGHER",
        "driving_entitlements": "B,D1",
        "right_to_work": True,
        "residency_status": "TEMPORARY",
    },
    {
        "name": "Tim Berners-Lee",
        "dob": "1975-06-08",
        "nationality": "GB",
        "postcode": "OX1 3QD",
        "tax_band": "ADDITIONAL",
        "driving_entitlements": "A,B,C,C1",
        "right_to_work": True,
        "residency_status": "CITIZEN",
    },
]


def seed_sample_data(identity_service: IdentityService) -> None:
    """Populate the platform with five sample identities on first run.

    Returns silently if the database already has any records, so the seed is
    idempotent across restarts.
    """
    if identity_service.list_all():
        return
    role = OrganisationRole.CENTRAL_AUTHORITY
    for person in _SAMPLE_PEOPLE:
        payload = NewIdentity(
            identity_id=generate_identity_id(),
            tax_reference=generate_tax_reference(),
            **person,
        )
        identity_service.create(role, payload)


# --- entry point ---


def run(settings: Settings | None = None) -> None:
    config = settings or load()
    connection: sqlite3.Connection = connect(config.database_path)
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit_repo = AuditRepository(connection)
    audit = AuditService(audit_repo)
    identity_service = IdentityService(identities, audit)
    verification = VerificationService(identities, audit)
    exports = ExportService(identities, audit_repo)
    stats = StatsService(identities, audit_repo)
    seed_sample_data(identity_service)
    portals = build_portals(identity_service, audit, verification, exports, stats)
    try:
        MenuShell(portals).run()
    finally:
        connection.close()


if __name__ == "__main__":  # pragma: no cover
    run()
