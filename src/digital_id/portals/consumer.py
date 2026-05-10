from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..authorisation.roles import OrganisationRole
from ..services.verification import VerificationService
from .base import Portal


def _require_args(args: list[str], expected: int, usage: str) -> None:
    if len(args) != expected:
        raise ValueError(f"usage: {usage}")


def build_tax_portal(
    verification: VerificationService, writer: Callable[[str], None]
) -> Portal:
    portal = Portal(OrganisationRole.TAX, "Tax Authority")
    role = OrganisationRole.TAX

    def verify(args: list[str]) -> None:
        _require_args(args, 3, "verify <id> <YYYY-MM-DD start> <YYYY-MM-DD end>")
        start = date.fromisoformat(args[1])
        end = date.fromisoformat(args[2])
        response = verification.verify_for_tax(role, args[0], start, end)
        writer(
            f"id={response.identity_id} exists={response.exists} "
            f"active_now={response.active_now} "
            f"suspended_in_period={response.suspended_in_period} "
            f"period={response.period_start.isoformat()}..{response.period_end.isoformat()}"
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
            f"active_now={response.active_now} "
            f"restricted_now={response.restricted_now}"
        )

    portal.register("verify", "check whether an id is active and unrestricted", verify)
    return portal


def build_validity_portal(
    role: OrganisationRole,
    title: str,
    verification: VerificationService,
    writer: Callable[[str], None],
) -> Portal:
    portal = Portal(role, title)

    def verify(args: list[str]) -> None:
        _require_args(args, 1, "verify <id>")
        response = verification.verify_validity(role, args[0])
        writer(f"id={response.identity_id} valid_now={response.valid_now}")

    portal.register("verify", "check whether an id is valid right now", verify)
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
        writer(
            f"id={response.identity_id} valid_now={response.valid_now} "
            f"name={response.name or ''}"
        )

    portal.register("verify", "check validity and look up the name", verify)
    return portal
