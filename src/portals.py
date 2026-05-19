from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

from rich.console import Group
from rich.panel import Panel

from exports import ExportService
from models import (
    Argument,
    Command,
    OrganisationRole,
    Portal,
    ValidationError,
    generate_identity_id,
    generate_tax_reference,
    validate_dob,
    validate_identity_id,
    validate_name,
    validate_nationality,
    validate_postcode,
    validate_tax_reference,
)
from render import (
    audit_table,
    dvla_response_table,
    employer_response_table,
    identity_list_table,
    identity_panel,
    stats_table,
    tax_response_table,
)
from services import (
    AuditService,
    IdentityService,
    NewIdentity,
    StatsService,
)
from verification import VerificationService

# --- central authority portal ---


def build_central_portal(
    identity_service: IdentityService,
    audit_service: AuditService,
    export_service: ExportService,
    stats_service: StatsService,
    id_generator: Callable[[], str] | None = None,
) -> Portal:
    role = OrganisationRole.CENTRAL_AUTHORITY
    gen_id = id_generator or generate_identity_id

    portal = Portal(
        role,
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
        identity = identity_service.create(role, payload)
        notice = Panel(
            f"[bold cyan]Your Digital ID:[/] [bold white]{identity.id}[/]\n"
            f"[bold yellow]Remember this ID for all future operations.[/]",
            border_style="green",
            title="[bold green]ID Created[/]",
        )
        return Group(notice, identity_panel(identity))

    def update_name(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_name(role, args["identity_id"], args["name"])
        )

    def update_postcode(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_postcode(role, args["identity_id"], args["postcode"])
        )

    def update_tax(args: Mapping[str, str]):
        ref = args["tax_reference"] or None
        band = args["tax_band"] or None
        return identity_panel(
            identity_service.update_tax_details(role, args["identity_id"], ref, band)
        )

    def update_driving(args: Mapping[str, str]):
        return identity_panel(
            identity_service.update_driving(
                role,
                args["identity_id"],
                args["entitlements"],
                args["restrictions"],
            )
        )

    def update_eligibility(args: Mapping[str, str]):
        right = args["right_to_work"] == "Yes"
        return identity_panel(
            identity_service.update_eligibility(
                role,
                args["identity_id"],
                right,
                args["residency"],
            )
        )

    def suspend(args: Mapping[str, str]):
        return identity_panel(identity_service.suspend(role, args["identity_id"]))

    def revoke(args: Mapping[str, str]):
        return identity_panel(identity_service.revoke(role, args["identity_id"]))

    def reactivate(args: Mapping[str, str]):
        return identity_panel(identity_service.reactivate(role, args["identity_id"]))

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
            role, directory / "identities.csv"
        )
        audit_count = export_service.export_audit(role, directory / "audit.csv")
        return (
            f"[bold green]Exported[/] {identities_count} identity rows and "
            f"{audit_count} audit rows to {directory}"
        )

    def stats(_args: Mapping[str, str]):
        return stats_table(stats_service.snapshot(role))

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
                    "Driving entitlements",
                    options=("A", "B", "C", "C1", "D", "D1"),
                    multi_select=True,
                ),
                Argument(
                    "restrictions",
                    "Driving restrictions",
                    options=("GLASSES", "AUTOMATIC_ONLY", "DAYTIME_ONLY", "HEARING_AID"),
                    multi_select=True,
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
            (Argument("directory", "Output directory", default="."),),
            export,
            group="Reports",
        )
    )
    portal.add(Command("stats", "Show statistics", "Counts by status and recent activity", (), stats, group="Reports"))
    return portal


# --- consumer portals ---


def _validate_date(value: str) -> None:
    try:
        date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("date", "expected ISO date YYYY-MM-DD") from exc


def _identity_arg() -> Argument:
    return Argument("identity_id", "Identity ID", validator=validate_identity_id)


def build_tax_portal(verification: VerificationService) -> Portal:
    portal = Portal(
        OrganisationRole.TAX,
        "Tax Authority",
        "Verify identity status and check for suspensions within a reporting period.",
    )

    def verify(args: Mapping[str, str]):
        start = date.fromisoformat(args["period_start"])
        end = date.fromisoformat(args["period_end"])
        response = verification.verify_for_tax(
            OrganisationRole.TAX, args["identity_id"], start, end
        )
        return tax_response_table(response)

    portal.add(
        Command(
            "verify",
            "Verify for a reporting period",
            "Check identity exists, is active and was not suspended in the period.",
            (
                _identity_arg(),
                Argument("period_start", "Period start (YYYY-MM-DD)", validator=_validate_date),
                Argument("period_end", "Period end (YYYY-MM-DD)", validator=_validate_date),
            ),
            verify,
        )
    )
    return portal


def build_dvla_portal(verification: VerificationService) -> Portal:
    portal = Portal(
        OrganisationRole.DVLA,
        "Driving Licence Authority",
        "Verify active status, restrictions and driving entitlements.",
    )

    def verify(args: Mapping[str, str]):
        return dvla_response_table(
            verification.verify_for_dvla(OrganisationRole.DVLA, args["identity_id"])
        )

    portal.add(
        Command(
            "verify",
            "Verify for licensing",
            "Returns active status, restriction flag, entitlements and restrictions.",
            (_identity_arg(),),
            verify,
        )
    )
    return portal


def build_employer_portal(verification: VerificationService) -> Portal:
    portal = Portal(
        OrganisationRole.EMPLOYER,
        "Employer",
        "Verify identity validity and right to work status.",
    )

    def verify(args: Mapping[str, str]):
        return employer_response_table(
            verification.verify_for_employer(OrganisationRole.EMPLOYER, args["identity_id"])
        )

    portal.add(
        Command(
            "verify",
            "Verify validity and right to work",
            "Returns whether the identity is valid and has the right to work.",
            (_identity_arg(),),
            verify,
        )
    )
    return portal
