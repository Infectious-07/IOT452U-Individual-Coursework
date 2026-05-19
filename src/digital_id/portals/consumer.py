from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from ..authorisation.roles import OrganisationRole
from ..cli.render import dvla_response_table, employer_response_table, tax_response_table
from ..domain.exceptions import ValidationError
from ..services.verification import VerificationService
from .base import Argument, Command, Portal


def _identity_arg() -> Argument:
    return Argument("identity_id", "Identity ID")


def build_tax_portal(verification: VerificationService) -> Portal:
    portal = Portal(
        OrganisationRole.TAX,
        "Tax Authority",
        "Verify identity status and check for suspensions within a reporting period.",
    )

    def verify(args: Mapping[str, str]):
        try:
            start = date.fromisoformat(args["period_start"])
            end = date.fromisoformat(args["period_end"])
        except ValueError as exc:
            raise ValidationError("period", "expected ISO dates YYYY-MM-DD") from exc
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
                Argument("period_start", "Period start (YYYY-MM-DD)"),
                Argument("period_end", "Period end (YYYY-MM-DD)"),
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
