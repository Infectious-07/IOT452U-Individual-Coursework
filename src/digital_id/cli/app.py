from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from ..authorisation.roles import OrganisationRole
from ..config.settings import Settings, load
from ..persistence.audit_repository import AuditRepository
from ..persistence.database import bootstrap, connect
from ..persistence.identity_repository import IdentityRepository
from ..portals.base import Portal
from ..portals.central_authority import build_central_portal
from ..portals.consumer import build_dvla_portal, build_employer_portal, build_tax_portal
from ..services.audit_service import AuditService
from ..services.export_service import ExportService
from ..services.identity_service import IdentityService
from ..services.stats_service import StatsService
from ..services.verification import VerificationService
from .shell import MenuShell


def build_portals(
    identity_service: IdentityService,
    audit_service: AuditService,
    verification: VerificationService,
    export_service: ExportService,
    stats_service: StatsService,
) -> Mapping[OrganisationRole, Portal]:
    return {
        OrganisationRole.CENTRAL_AUTHORITY: build_central_portal(
            identity_service, audit_service, export_service, stats_service
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
    portals = build_portals(identity_service, audit, verification, exports, stats)
    MenuShell(portals).run()
