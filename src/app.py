from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping

from config import Settings, load
from database import AuditRepository, IdentityRepository, bootstrap, connect
from exports import ExportService
from models import OrganisationRole, Portal
from portals import (
    build_central_portal,
    build_dvla_portal,
    build_employer_portal,
    build_tax_portal,
)
from seed import seed_sample_data
from services import (
    AuditService,
    IdentityService,
    StatsService,
)
from shell import MenuShell
from verification import VerificationService


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
