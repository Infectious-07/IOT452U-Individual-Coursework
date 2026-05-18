from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..authorisation.roles import OrganisationRole
from ..domain.exceptions import ValidationError
from ..services.verification import VerificationService
from .base import Portal


def _require_args(args: list[str], expected: int, usage: str) -> None:
    if len(args) != expected:
        raise ValueError(f"usage: {usage}")


def _codes_summary(codes) -> str:
    items = sorted(item.value for item in codes)
    return ",".join(items) if items else "-"


def build_tax_portal(
    verification: VerificationService, writer: Callable[[str], None]
) -> Portal:
    portal = Portal(OrganisationRole.TAX, "Tax Authority")
    role = OrganisationRole.TAX

    def verify(args: list[str]) -> None:
        _require_args(args, 3, "verify <id> <YYYY-MM-DD start> <YYYY-MM-DD end>")
        try:
            start = date.fromisoformat(args[1])
            end = date.fromisoformat(args[2])
        except ValueError as exc:
            raise ValidationError("period", "expected ISO dates YYYY-MM-DD") from exc
        response = verification.verify_for_tax(role, args[0], start, end)
        band_value = response.tax_band.value if response.tax_band else "-"
        writer(
            f"id={response.identity_id} exists={response.exists} "
            f"active_now={response.active_now} "
            f"suspended_in_period={response.suspended_in_period} "
            f"period={response.period_start.isoformat()}..{response.period_end.isoformat()} "
            f"tax_reference={response.tax_reference or '-'} tax_band={band_value}"
        )

    portal.register("verify", "check an id for a reporting period", verify)
    return portal


def build_dvla_portal(
    verification: VerificationService, writer: Callable[[str], None]
) -> Portal:
    portal = Portal(OrganisationRole.DVLA, "Driving Licence Authority")
    role = OrganisationRole.DVLA

    def verify(args: list[str]) -> None:
        _require_args(args, 1, "verify <id>")
        response = verification.verify_for_dvla(role, args[0])
        writer(
            f"id={response.identity_id} exists={response.exists} "
            f"active_now={response.active_now} restricted_now={response.restricted_now} "
            f"entitlements={_codes_summary(response.entitlements)} "
            f"restrictions={_codes_summary(response.restrictions)}"
        )

    portal.register("verify", "check whether an id is active and unrestricted", verify)
    return portal


def build_bank_portal(
    verification: VerificationService, writer: Callable[[str], None]
) -> Portal:
    portal = Portal(OrganisationRole.BANK, "Bank")
    role = OrganisationRole.BANK

    def verify(args: list[str]) -> None:
        _require_args(args, 1, "verify <id>")
        response = verification.verify_for_bank(role, args[0])
        writer(f"id={response.identity_id} valid_now={response.valid_now}")

    portal.register("verify", "check whether an id is valid right now", verify)
    return portal


def build_employer_portal(
    verification: VerificationService, writer: Callable[[str], None]
) -> Portal:
    portal = Portal(OrganisationRole.EMPLOYER, "Employer")
    role = OrganisationRole.EMPLOYER

    def verify(args: list[str]) -> None:
        _require_args(args, 1, "verify <id>")
        response = verification.verify_for_employer(role, args[0])
        writer(
            f"id={response.identity_id} valid_now={response.valid_now} "
            f"right_to_work={response.right_to_work}"
        )

    portal.register("verify", "check validity and right to work", verify)
    return portal


def build_lookup_portal(
    role: OrganisationRole,
    title: str,
    verification: VerificationService,
    writer: Callable[[str], None],
) -> Portal:
    portal = Portal(role, title)

    def verify(args: list[str]) -> None:
        _require_args(args, 1, "verify <id>")
        response = verification.verify_lookup(role, args[0])
        residency = response.residency_status.value if response.residency_status else "-"
        writer(
            f"id={response.identity_id} valid_now={response.valid_now} "
            f"name={response.name or '-'} residency_status={residency}"
        )

    portal.register("verify", "check validity, name and residency", verify)
    return portal
