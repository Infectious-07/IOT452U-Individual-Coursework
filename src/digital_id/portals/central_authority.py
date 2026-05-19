from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from rich.console import Group
from rich.panel import Panel

from ..authorisation.roles import OrganisationRole
from ..cli.render import (
    audit_table,
    identity_list_table,
    identity_panel,
    stats_table,
)
from ..domain.validators import (
    generate_identity_id,
    generate_tax_reference,
    validate_dob,
    validate_driving_entitlements,
    validate_driving_restrictions,
    validate_identity_id,
    validate_name,
    validate_nationality,
    validate_postcode,
    validate_tax_reference,
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
    id_generator: Callable[[], str] | None = None,
) -> Portal:
    gen_id = id_generator or generate_identity_id

    portal = Portal(
        ROLE,
        "Central Authority",
        "Create, update and manage Digital ID records.",
    )

    def create(args: Mapping[str, str]):
        identity_id = gen_id()
        payload = NewIdentity(
            identity_id=identity_id,
            name=args["name"],
            dob=args["dob"],
            nationality=args["nationality"],
            postcode=args["postcode"],
            tax_reference=generate_tax_reference(),
            tax_band="BASIC",
            driving_entitlements="B",
            right_to_work=True,
            residency_status="TEMPORARY",
        )
        identity = identity_service.create(ROLE, payload)
        notice = Panel(
            f"[bold cyan]Your Digital ID:[/] [bold white]{identity.id}[/]\n"
            f"[bold yellow]Remember this ID for all future operations.[/]",
            border_style="green",
            title="[bold green]ID Created[/]",
        )
        return Group(notice, identity_panel(identity))

    def update_name(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_name(ROLE, args["identity_id"], args["name"])
        )

    def update_postcode(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_postcode(ROLE, args["identity_id"], args["postcode"])
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

    _id = Argument("identity_id", "Identity ID", validator=validate_identity_id)

    portal.add(
        Command(
            "create",
            "Create a Digital ID",
            "Issue a new Digital ID with the mandatory base attributes",
            (
                Argument("name", "Full name", validator=validate_name),
                Argument("dob", "Date of birth (YYYY-MM-DD)", validator=validate_dob),
                Argument("nationality", "Nationality (ISO 3166 alpha-2)", default="GB", validator=validate_nationality),
                Argument("postcode", "Postcode (e.g. SW1A 2AA)", validator=validate_postcode),
            ),
            create,
            group="Records",
        )
    )
    portal.add(Command("show", "Show a Digital ID", "Display the current record", (_id,), show, group="Records"))
    portal.add(Command("list", "List Digital IDs", "Show every record in the system", (), list_all, group="Records"))
    portal.add(
        Command(
            "update_name",
            "Update name",
            "Change the name on an existing record",
            (_id, Argument("name", "New name", validator=validate_name)),
            update_name,
            group="Updates",
        )
    )
    portal.add(
        Command(
            "update_postcode",
            "Update postcode",
            "Change the registered postcode",
            (_id, Argument("postcode", "New postcode (e.g. SW1A 2AA)", validator=validate_postcode)),
            update_postcode,
            group="Updates",
        )
    )
    portal.add(
        Command(
            "update_tax",
            "Update tax details",
            "Set or clear the tax reference and band",
            (
                _id,
                Argument("tax_reference", "Tax reference (blank to clear)", default="", validator=validate_tax_reference),
                Argument("tax_band", "Tax band", options=("BASIC", "HIGHER", "ADDITIONAL", "EXEMPT")),
            ),
            update_tax,
            group="Updates",
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
                    validator=validate_driving_entitlements,
                ),
                Argument(
                    "restrictions",
                    "Restriction codes, comma separated (GLASSES, AUTOMATIC_ONLY, DAYTIME_ONLY, HEARING_AID)",
                    default="",
                    validator=validate_driving_restrictions,
                ),
            ),
            update_driving,
            group="Updates",
        )
    )
    portal.add(
        Command(
            "update_eligibility",
            "Update right to work and residency",
            "Set the right to work flag and the residency status",
            (
                _id,
                Argument("right_to_work", "Right to work", options=("Yes", "No")),
                Argument("residency", "Residency status", options=("TEMPORARY", "CITIZEN", "RESIDENT", "NONE")),
            ),
            update_eligibility,
            group="Updates",
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
            group="Lifecycle",
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
            group="Lifecycle",
        )
    )
    portal.add(
        Command(
            "reactivate",
            "Reactivate an ID",
            "Move a suspended ID back to active",
            (_id,),
            reactivate,
            group="Lifecycle",
        )
    )
    portal.add(
        Command(
            "history",
            "Show history",
            "List the audit events recorded for an ID",
            (_id,),
            history,
            group="Reports",
        )
    )
    portal.add(
        Command(
            "export",
            "Export to CSV",
            "Write identities and audit events to two CSV files",
            (Argument("directory", "Output directory"),),
            export,
            group="Reports",
        )
    )
    portal.add(Command("stats", "Show statistics", "Counts by status and recent activity", (), stats, group="Reports"))
    return portal
