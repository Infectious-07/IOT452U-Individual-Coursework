from __future__ import annotations

from models import OrganisationRole, generate_identity_id, generate_tax_reference
from services import IdentityService, NewIdentity

SAMPLE_PEOPLE = [
    {
        "name": "Ada Lovelace",
        "dob": "1990-03-15",
        "nationality": "GB",
        "postcode": "SW1A 2AA",
        "tax_band": "HIGHER",
        "driving_entitlements": "B,C1",
        "driving_restrictions": "GLASSES",
        "right_to_work": True,
        "residency_status": "CITIZEN",
    },
    {
        "name": "Alan Turing",
        "dob": "1985-06-23",
        "nationality": "GB",
        "postcode": "MK7 6AA",
        "tax_band": "ADDITIONAL",
        "driving_entitlements": "A,B",
        "right_to_work": True,
        "residency_status": "CITIZEN",
    },
    {
        "name": "Grace Hopper",
        "dob": "1992-12-09",
        "nationality": "US",
        "postcode": "EC2R 8AH",
        "tax_band": "BASIC",
        "driving_entitlements": "B",
        "driving_restrictions": "AUTOMATIC_ONLY",
        "right_to_work": True,
        "residency_status": "RESIDENT",
    },
    {
        "name": "Linus Torvalds",
        "dob": "1988-12-28",
        "nationality": "FI",
        "postcode": "M1 1AE",
        "tax_band": "HIGHER",
        "driving_entitlements": "B,D1",
        "right_to_work": True,
        "residency_status": "TEMPORARY",
    },
    {
        "name": "Tim Berners-Lee",
        "dob": "1975-06-08",
        "nationality": "GB",
        "postcode": "OX1 3QD",
        "tax_band": "ADDITIONAL",
        "driving_entitlements": "A,B,C,C1",
        "right_to_work": True,
        "residency_status": "CITIZEN",
    },
]


def seed_sample_data(identity_service: IdentityService) -> None:
    """Populate the platform with five sample identities on first run.

    Returns silently if the database already has any records, so the seed is
    idempotent across restarts.
    """
    if identity_service.list_all():
        return
    role = OrganisationRole.CENTRAL_AUTHORITY
    for person in SAMPLE_PEOPLE:
        payload = NewIdentity(
            identity_id=generate_identity_id(),
            tax_reference=generate_tax_reference(),
            **person,
        )
        identity_service.create(role, payload)
