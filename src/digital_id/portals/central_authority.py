from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..authorisation.roles import OrganisationRole
from ..domain.identity import DigitalID
from ..services.audit_service import AuditService
from ..services.export_service import ExportService
from ..services.identity_service import IdentityService
from ..services.stats_service import StatsService
from .base import Portal


def _format_identity(identity: DigitalID) -> str:
    return (
        f"id={identity.id} name={identity.name} dob={identity.dob.isoformat()} "
        f"status={identity.status.value} updated_at={identity.updated_at.isoformat()}"
    )


def build_central_portal(
    identity_service: IdentityService,
    audit_service: AuditService,
    export_service: ExportService,
    stats_service: StatsService,
    writer: Callable[[str], None],
) -> Portal:
    portal = Portal(OrganisationRole.CENTRAL_AUTHORITY, "Central Authority")
    role = OrganisationRole.CENTRAL_AUTHORITY

    def _require_args(args: list[str], expected: int, usage: str) -> None:
        if len(args) != expected:
            raise ValueError(f"usage: {usage}")

    def create(args: list[str]) -> None:
        _require_args(args, 3, "create <id> <full name> <dob>")
        identity = identity_service.create(role, args[0], args[1], args[2])
        writer(_format_identity(identity))

    def update(args: list[str]) -> None:
        _require_args(args, 2, "update <id> <new name>")
        identity = identity_service.update_name(role, args[0], args[1])
        writer(_format_identity(identity))

    def suspend(args: list[str]) -> None:
        _require_args(args, 1, "suspend <id>")
        identity = identity_service.suspend(role, args[0])
        writer(_format_identity(identity))

    def revoke(args: list[str]) -> None:
        _require_args(args, 1, "revoke <id>")
        identity = identity_service.revoke(role, args[0])
        writer(_format_identity(identity))

    def reactivate(args: list[str]) -> None:
        _require_args(args, 1, "reactivate <id>")
        identity = identity_service.reactivate(role, args[0])
        writer(_format_identity(identity))

    def show(args: list[str]) -> None:
        _require_args(args, 1, "show <id>")
        identity = identity_service.get(args[0])
        writer(_format_identity(identity))

    def history(args: list[str]) -> None:
        _require_args(args, 1, "history <id>")
        events = audit_service.history_for(args[0])
        if not events:
            writer("no events recorded")
            return
        for event in events:
            writer(
                f"{event.occurred_at.isoformat()} {event.actor_role} "
                f"{event.action.value} {event.payload}"
            )

    def export(args: list[str]) -> None:
        _require_args(args, 1, "export <directory>")
        directory = Path(args[0])
        identities_count = export_service.export_identities(
            role, directory / "identities.csv"
        )
        audit_count = export_service.export_audit(role, directory / "audit.csv")
        writer(f"exported identities={identities_count} audit_events={audit_count}")

    def stats(args: list[str]) -> None:
        _require_args(args, 0, "stats")
        snapshot = stats_service.snapshot(role)
        writer(f"total={snapshot.total}")
        for status_name, count in snapshot.by_status.items():
            writer(f"  {status_name}={count}")
        writer(f"events_last_7_days={snapshot.events_last_7_days}")

    def list_all(args: list[str]) -> None:
        _require_args(args, 0, "list")
        records = identity_service.list_all()
        if not records:
            writer("no identities")
            return
        for identity in records:
            writer(_format_identity(identity))

    portal.register("create", "create a new Digital ID", create)
    portal.register("update", "change the name on an existing Digital ID", update)
    portal.register("suspend", "set a Digital ID to suspended", suspend)
    portal.register("revoke", "revoke a Digital ID permanently", revoke)
    portal.register("reactivate", "reactivate a suspended Digital ID", reactivate)
    portal.register("show", "show the current record for an id", show)
    portal.register("list", "list every Digital ID record", list_all)
    portal.register("history", "list audit events for an id", history)
    portal.register("export", "write identities and audit CSVs to a directory", export)
    portal.register("stats", "show counts by status and recent activity", stats)
    return portal
