from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from ..authorisation.roles import OrganisationRole
from ..cli.render import (
    dvla_response_table,
    employer_response_table,
    lookup_response_table,
    tax_response_table,
    validity_response_table,
)
from ..domain.exceptions import ValidationError
from ..services.verification import VerificationService
from .base import Argument, Command, Portal


def _identity_arg() -> Argument:
    return Argument("identity_id", "Identity ID")


def build_tax_portal(verification: VerificationService) -> Portal:
    portal = Portal(
        OrganisationRole.TAX,
        "Tax Authority",
        "Confirm an identity and check for any suspension within a reporting period.",
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
            "Check whether an ID exists, is currently active and was suspended in the period.",
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
        "Check active status, restrictions and entitlements for licensing.",
    )

    def verify(args: Mapping[str, str]):
        return dvla_response_table(
            verification.verify_for_dvla(OrganisationRole.DVLA, args["identity_id"])
        )

    portal.add(
        Command(
            "verify",
            "Verify a Digital ID for licensing",
            "Returns active status, restriction flag and entitlements.",
            (_identity_arg(),),
            verify,
        )
    )
    return portal


def build_bank_portal(verification: VerificationService) -> Portal:
    portal = Portal(
        OrganisationRole.BANK,
        "Bank",
        "Lightweight validity check for account operations.",
    )

    def verify(args: Mapping[str, str]):
        return validity_response_table(
            verification.verify_for_bank(OrganisationRole.BANK, args["identity_id"])
        )

    portal.add(
        Command("verify", "Verify validity", "Yes or no on validity right now.", (_identity_arg(),), verify)
    )
    return portal


def build_employer_portal(verification: VerificationService) -> Portal:
    portal = Portal(
        OrganisationRole.EMPLOYER,
        "Employer",
        "Validity plus right to work check.",
    )

    def verify(args: Mapping[str, str]):
        return employer_response_table(
            verification.verify_for_employer(OrganisationRole.EMPLOYER, args["identity_id"])
        )

    portal.add(
        Command(
            "verify",
            "Verify validity and right to work",
            "Returns valid_now and right_to_work for an ID.",
            (_identity_arg(),),
            verify,
        )
    )
    return portal


def build_lookup_portal(role: OrganisationRole, title: str, verification: VerificationService) -> Portal:
    portal = Portal(role, title, "Validity, name and residency status.")

    def verify(args: Mapping[str, str]):
        return lookup_response_table(
            verification.verify_lookup(role, args["identity_id"])
        )

    portal.add(Command("verify", "Verify and look up", "Returns validity, name and residency.", (_identity_arg(),), verify))
    return portal
