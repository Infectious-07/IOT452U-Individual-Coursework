from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..authorisation.roles import OrganisationRole
from ..cli.render import (
    audit_table,
    identity_list_table,
    identity_panel,
    stats_table,
)
from ..services.audit_service import AuditService
from ..services.export_service import ExportService
from ..services.identity_service import IdentityService, NewIdentity
from ..services.stats_service import StatsService
from .base import Argument, Command, Portal

ROLE = OrganisationRole.CENTRAL_AUTHORITY


def build_central_portal(
    identity_service: IdentityService,
    audit_service: AuditService,
    export_service: ExportService,
    stats_service: StatsService,
) -> Portal:
    portal = Portal(
        ROLE,
        "Central Authority",
        "Create, update and manage Digital ID records.",
    )

    def create(args: Mapping[str, str]):
        payload = NewIdentity(
            identity_id=args["identity_id"],
            name=args["name"],
            dob=args["dob"],
            nationality=args["nationality"],
            address=args["address"],
        )
        return identity_panel(identity_service.create(ROLE, payload))

    def update_name(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_name(ROLE, args["identity_id"], args["name"])
        )

    def update_address(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_address(ROLE, args["identity_id"], args["address"])
        )

    def update_tax(args: Mapping[str, str]):
        ref = args["tax_reference"] or None
        band = args["tax_band"] or None
        return identity_panel(
            identity_service.update_tax_details(ROLE, args["identity_id"], ref, band)
        )

    def update_driving(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_driving(
                ROLE,
                args["identity_id"],
                args["entitlements"],
                args["restrictions"],
            )
        )

    def update_eligibility(args: Mapping[str, str]):
        right = args["right_to_work"].strip().lower() in {"yes", "y", "true", "1"}
        return identity_panel(
            identity_service.update_eligibility(
                ROLE,
                args["identity_id"],
                right,
                args["residency"],
            )
        )

    def suspend(args: Mapping[str, str]):
        return identity_panel(identity_service.suspend(ROLE, args["identity_id"]))

    def revoke(args: Mapping[str, str]):
        return identity_panel(identity_service.revoke(ROLE, args["identity_id"]))

    def reactivate(args: Mapping[str, str]):
        return identity_panel(identity_service.reactivate(ROLE, args["identity_id"]))

    def show(args: Mapping[str, str]):
        return identity_panel(identity_service.get(args["identity_id"]))

    def list_all(_args: Mapping[str, str]):
        records = identity_service.list_all()
        if not records:
            return "[yellow]no identities yet[/]"
        return identity_list_table(records)

    def history(args: Mapping[str, str]):
        events = audit_service.history_for(args["identity_id"])
        if not events:
            return "[yellow]no events recorded[/]"
        return audit_table(events, title=f"History  {args['identity_id']}")

    def export(args: Mapping[str, str]):
        directory = Path(args["directory"])
        identities_count = export_service.export_identities(
            ROLE, directory / "identities.csv"
        )
        audit_count = export_service.export_audit(ROLE, directory / "audit.csv")
        return (
            f"[bold green]Exported[/] {identities_count} identity rows and "
            f"{audit_count} audit rows to {directory}"
        )

    def stats(_args: Mapping[str, str]):
        return stats_table(stats_service.snapshot(ROLE))

    _id = Argument("identity_id", "Identity ID")

    portal.add(
        Command(
            "create",
            "Create a Digital ID",
            "Issue a new Digital ID with the mandatory base attributes",
            (
                Argument("identity_id", "Identity ID"),
                Argument("name", "Full name"),
                Argument("dob", "Date of birth (YYYY-MM-DD)"),
                Argument("nationality", "Nationality (ISO 3166 alpha-2)", default="GB"),
                Argument("address", "Address"),
            ),
            create,
        )
    )
    portal.add(
        Command(
            "update_name",
            "Update name",
            "Change the name on an existing record",
            (_id, Argument("name", "New name")),
            update_name,
        )
    )
    portal.add(
        Command(
            "update_address",
            "Update address",
            "Change the registered address",
            (_id, Argument("address", "New address")),
            update_address,
        )
    )
    portal.add(
        Command(
            "update_tax",
            "Update tax details",
            "Set or clear the tax reference and band",
            (
                _id,
                Argument("tax_reference", "Tax reference (blank to clear)", default=""),
                Argument("tax_band", "Tax band (BASIC, HIGHER, ADDITIONAL, EXEMPT)", default=""),
            ),
            update_tax,
        )
    )
    portal.add(
        Command(
            "update_driving",
            "Update driving entitlements",
            "Set the driving entitlement and restriction sets",
            (
                _id,
                Argument(
                    "entitlements",
                    "Entitlement codes, comma separated (A, B, C, C1, D, D1)",
                    default="",
                ),
                Argument(
                    "restrictions",
                    "Restriction codes, comma separated (GLASSES, AUTOMATIC_ONLY, DAYTIME_ONLY, HEARING_AID)",
                    default="",
                ),
            ),
            update_driving,
        )
    )
    portal.add(
        Command(
            "update_eligibility",
            "Update right to work and residency",
            "Set the right to work flag and the residency status",
            (
                _id,
                Argument("right_to_work", "Right to work (yes/no)", default="no"),
                Argument(
                    "residency",
                    "Residency (CITIZEN, RESIDENT, TEMPORARY, NONE)",
                    default="NONE",
                ),
            ),
            update_eligibility,
        )
    )
    portal.add(
        Command(
            "suspend",
            "Suspend an ID",
            "Temporarily suspend a Digital ID",
            (_id,),
            suspend,
            confirmation="Suspending a Digital ID blocks all consumer checks. Continue?",
        )
    )
    portal.add(
        Command(
            "revoke",
            "Revoke an ID",
            "Permanently revoke a Digital ID; this cannot be undone",
            (_id,),
            revoke,
            confirmation="Revoking a Digital ID is permanent and cannot be undone. Continue?",
        )
    )
    portal.add(
        Command(
            "reactivate",
            "Reactivate an ID",
            "Move a suspended ID back to active",
            (_id,),
            reactivate,
        )
    )
    portal.add(Command("show", "Show a Digital ID", "Display the current record", (_id,), show))
    portal.add(Command("list", "List Digital IDs", "Show every record in the system", (), list_all))
    portal.add(
        Command(
            "history",
            "Show history",
            "List the audit events recorded for an ID",
            (_id,),
            history,
        )
    )
    portal.add(
        Command(
            "export",
            "Export to CSV",
            "Write identities and audit events to two CSV files",
            (Argument("directory", "Output directory"),),
            export,
        )
    )
    portal.add(Command("stats", "Show statistics", "Counts by status and recent activity", (), stats))
    return portal
