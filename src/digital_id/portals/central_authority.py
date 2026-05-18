from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..authorisation.roles import OrganisationRole
from ..domain.identity import DigitalID
from ..services.audit_service import AuditService
from ..services.export_service import ExportService
from ..services.identity_service import IdentityService, NewIdentity
from ..services.stats_service import StatsService
from .base import Portal


def _format_identity(identity: DigitalID) -> str:
    return (
        f"id={identity.id} name={identity.name} dob={identity.dob.isoformat()} "
        f"nationality={identity.nationality} status={identity.status.value} "
        f"updated_at={identity.updated_at.isoformat()}"
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
        _require_args(args, 5, "create <id> <full name> <dob> <nationality> <address>")
        payload = NewIdentity(
            identity_id=args[0],
            name=args[1],
            dob=args[2],
            nationality=args[3],
            address=args[4],
        )
        identity = identity_service.create(role, payload)
        writer(_format_identity(identity))

    def update_name(args: list[str]) -> None:
        _require_args(args, 2, "update-name <id> <new name>")
        identity = identity_service.update_name(role, args[0], args[1])
        writer(_format_identity(identity))

    def update_address(args: list[str]) -> None:
        _require_args(args, 2, "update-address <id> <new address>")
        identity = identity_service.update_address(role, args[0], args[1])
        writer(_format_identity(identity))

    def update_tax(args: list[str]) -> None:
        _require_args(args, 3, "update-tax <id> <reference or ->  <band or ->")
        ref = None if args[1] == "-" else args[1]
        band = None if args[2] == "-" else args[2]
        identity = identity_service.update_tax_details(role, args[0], ref, band)
        writer(_format_identity(identity))

    def update_driving(args: list[str]) -> None:
        _require_args(args, 3, "update-driving <id> <entitlements csv or ->  <restrictions csv or ->")
        ents = "" if args[1] == "-" else args[1]
        rests = "" if args[2] == "-" else args[2]
        identity = identity_service.update_driving(role, args[0], ents, rests)
        writer(_format_identity(identity))

    def update_eligibility(args: list[str]) -> None:
        _require_args(args, 3, "update-eligibility <id> <right_to_work yes|no> <residency>")
        right = args[1].lower() in {"yes", "true", "1"}
        identity = identity_service.update_eligibility(role, args[0], right, args[2])
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

    def list_all(args: list[str]) -> None:
        _require_args(args, 0, "list")
        records = identity_service.list_all()
        if not records:
            writer("no identities")
            return
        for identity in records:
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

    portal.register("create", "create a new Digital ID", create)
    portal.register("update-name", "change the name on a Digital ID", update_name)
    portal.register("update-address", "change the registered address", update_address)
    portal.register("update-tax", "set tax reference and band", update_tax)
    portal.register("update-driving", "set driving entitlements and restrictions", update_driving)
    portal.register("update-eligibility", "set right to work and residency", update_eligibility)
    portal.register("suspend", "set a Digital ID to suspended", suspend)
    portal.register("revoke", "revoke a Digital ID permanently", revoke)
    portal.register("reactivate", "reactivate a suspended Digital ID", reactivate)
    portal.register("show", "show the current record for an id", show)
    portal.register("list", "list every Digital ID record", list_all)
    portal.register("history", "list audit events for an id", history)
    portal.register("export", "write identities and audit CSVs to a directory", export)
    portal.register("stats", "show counts by status and recent activity", stats)
    return portal
