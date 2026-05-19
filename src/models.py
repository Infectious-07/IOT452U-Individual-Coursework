from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# --- exceptions ---


# base class so the application can catch every domain error in one place
class DigitalIdError(Exception):
    pass


class IdentityNotFoundError(DigitalIdError):
    def __init__(self, identity_id: str) -> None:
        super().__init__(f"identity not found: {identity_id}")
        self.identity_id = identity_id


class DuplicateIdentityError(DigitalIdError):
    def __init__(self, identity_id: str) -> None:
        super().__init__(f"identity already exists: {identity_id}")
        self.identity_id = identity_id


class InvalidTransitionError(DigitalIdError):
    def __init__(self, current: str, requested: str) -> None:
        super().__init__(f"cannot move from {current} to {requested}")
        self.current = current
        self.requested = requested


class ValidationError(DigitalIdError):
    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"invalid {field}: {reason}")
        self.field = field
        self.reason = reason


class AuthorisationError(DigitalIdError):
    def __init__(self, role: str, action: str) -> None:
        super().__init__(f"{role} is not allowed to {action}")
        self.role = role
        self.action = action


# --- identity enums ---


class IdentityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class TaxBand(StrEnum):
    BASIC = "BASIC"
    HIGHER = "HIGHER"
    ADDITIONAL = "ADDITIONAL"
    EXEMPT = "EXEMPT"


class ResidencyStatus(StrEnum):
    CITIZEN = "CITIZEN"
    RESIDENT = "RESIDENT"
    TEMPORARY = "TEMPORARY"
    NONE = "NONE"


class DrivingEntitlement(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    C1 = "C1"
    D = "D"
    D1 = "D1"


class DrivingRestriction(StrEnum):
    GLASSES = "GLASSES"
    AUTOMATIC_ONLY = "AUTOMATIC_ONLY"
    DAYTIME_ONLY = "DAYTIME_ONLY"
    HEARING_AID = "HEARING_AID"


# --- identity entity ---


@dataclass(frozen=True)
class DigitalID:
    """Immutable record of a Digital ID.

    `id`, `dob` and `nationality` are fixed at creation. All other fields are
    amended through the central authority's lifecycle service, which calls the
    `with_*` methods to produce new instances rather than mutating in place.
    """

    id: str
    name: str
    dob: date
    nationality: str
    postcode: str
    status: IdentityStatus
    created_at: datetime
    updated_at: datetime
    tax_reference: str | None = None
    tax_band: TaxBand | None = None
    driving_entitlements: frozenset[DrivingEntitlement] = field(default_factory=frozenset)
    driving_restrictions: frozenset[DrivingRestriction] = field(default_factory=frozenset)
    right_to_work: bool = False
    residency_status: ResidencyStatus = ResidencyStatus.TEMPORARY

    def with_name(self, new_name: str, now: datetime) -> DigitalID:
        return replace(self, name=new_name, updated_at=now)

    def with_status(self, new_status: IdentityStatus, now: datetime) -> DigitalID:
        return replace(self, status=new_status, updated_at=now)

    def with_postcode(self, new_postcode: str, now: datetime) -> DigitalID:
        return replace(self, postcode=new_postcode, updated_at=now)

    def with_tax_details(
        self,
        reference: str | None,
        band: TaxBand | None,
        now: datetime,
    ) -> DigitalID:
        return replace(self, tax_reference=reference, tax_band=band, updated_at=now)

    def with_driving(
        self,
        entitlements: frozenset[DrivingEntitlement],
        restrictions: frozenset[DrivingRestriction],
        now: datetime,
    ) -> DigitalID:
        return replace(
            self,
            driving_entitlements=entitlements,
            driving_restrictions=restrictions,
            updated_at=now,
        )

    def with_eligibility(
        self,
        right_to_work: bool,
        residency: ResidencyStatus,
        now: datetime,
    ) -> DigitalID:
        return replace(
            self,
            right_to_work=right_to_work,
            residency_status=residency,
            updated_at=now,
        )


# --- audit types ---


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    SUSPEND = "SUSPEND"
    REVOKE = "REVOKE"
    REACTIVATE = "REACTIVATE"
    VERIFY = "VERIFY"


@dataclass(frozen=True)
class AuditEvent:
    """One immutable entry in the append-only audit log.

    Every lifecycle change and every verification call writes an event. The
    payload is action-specific (the field that changed, the from/to status, or
    the verification outcome).
    """

    occurred_at: datetime
    actor_role: str
    action: AuditAction
    identity_id: str | None
    payload: Mapping[str, Any] = field(default_factory=dict)


# --- status transitions ---


_ALLOWED: dict[IdentityStatus, set[IdentityStatus]] = {
    IdentityStatus.ACTIVE: {IdentityStatus.SUSPENDED, IdentityStatus.REVOKED},
    IdentityStatus.SUSPENDED: {IdentityStatus.ACTIVE, IdentityStatus.REVOKED},
    IdentityStatus.REVOKED: set(),
}


def is_valid_transition(current: IdentityStatus, target: IdentityStatus) -> bool:
    if current is target:
        return True
    return target in _ALLOWED[current]


def assert_allowed(current: IdentityStatus, target: IdentityStatus) -> None:
    if not is_valid_transition(current, target):
        raise InvalidTransitionError(current.value, target.value)


# --- organisation roles ---


class OrganisationRole(StrEnum):
    CENTRAL_AUTHORITY = "CENTRAL_AUTHORITY"
    TAX = "TAX"
    DVLA = "DVLA"
    EMPLOYER = "EMPLOYER"


LIFECYCLE_ACTIONS = {"create", "update", "suspend", "revoke", "reactivate"}
VERIFY_ACTIONS = {"verify"}
ADMIN_ACTIONS = {"history", "export", "stats", "list"}

_ROLE_PERMISSIONS: dict[OrganisationRole, set[str]] = {
    OrganisationRole.CENTRAL_AUTHORITY: LIFECYCLE_ACTIONS | VERIFY_ACTIONS | ADMIN_ACTIONS,
    OrganisationRole.TAX: VERIFY_ACTIONS,
    OrganisationRole.DVLA: VERIFY_ACTIONS,
    OrganisationRole.EMPLOYER: VERIFY_ACTIONS,
}


def is_role_allowed(role: OrganisationRole, action: str) -> bool:
    return action in _ROLE_PERMISSIONS.get(role, set())


def require(role: OrganisationRole, action: str) -> None:
    if not is_role_allowed(role, action):
        raise AuthorisationError(role.value, action)


# --- validators ---


_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '\-]{0,98}[A-Za-z.]$")
_ID_PATTERN = re.compile(r"^[A-Z0-9\-]{4,32}$")
_NATIONALITY_PATTERN = re.compile(r"^[A-Z]{2}$")
_TAX_REF_PATTERN = re.compile(r"^[A-Z0-9]{6,16}$")
_POSTCODE_PATTERN = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$")


def generate_identity_id() -> str:
    return f"DID-{uuid.uuid4().hex[:8].upper()}"


def generate_tax_reference() -> str:
    return f"UTR{uuid.uuid4().hex[:7].upper()}"


def validate_identity_id(identity_id: str) -> str:
    cleaned = (identity_id or "").strip().upper()
    if not _ID_PATTERN.fullmatch(cleaned):
        raise ValidationError("id", "must be 4 to 32 chars of A-Z, 0-9 or dash")
    return cleaned


def validate_name(name: str) -> str:
    cleaned = (name or "").strip()
    if len(cleaned) < 2:
        raise ValidationError("name", "must be at least two characters")
    if not _NAME_PATTERN.fullmatch(cleaned):
        raise ValidationError("name", "contains unsupported characters")
    return cleaned


def validate_dob(value: str | date) -> date:
    if isinstance(value, date):
        dob = value
    else:
        try:
            dob = date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError("dob", "expected ISO date YYYY-MM-DD") from exc
    if dob > date.today():
        raise ValidationError("dob", "cannot be in the future")
    return dob


def validate_nationality(value: str) -> str:
    cleaned = (value or "").strip().upper()
    if not _NATIONALITY_PATTERN.fullmatch(cleaned):
        raise ValidationError("nationality", "expected ISO 3166 alpha-2 code")
    return cleaned


def validate_postcode(value: str) -> str:
    cleaned = (value or "").strip().upper()
    if not cleaned:
        raise ValidationError("postcode", "cannot be empty")
    if not _POSTCODE_PATTERN.fullmatch(cleaned):
        raise ValidationError("postcode", "must be a valid UK postcode (e.g. SW1A 2AA)")
    return cleaned


def validate_tax_reference(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    cleaned = str(value).strip().upper()
    if not _TAX_REF_PATTERN.fullmatch(cleaned):
        raise ValidationError("tax_reference", "expected 6 to 16 alphanumerics")
    return cleaned


def validate_tax_band(value: str | None) -> TaxBand | None:
    if value is None or not str(value).strip():
        return None
    try:
        return TaxBand(str(value).strip().upper())
    except ValueError as exc:
        raise ValidationError("tax_band", "unknown tax band") from exc


def validate_residency_status(value: str | None) -> ResidencyStatus:
    if value is None or not str(value).strip():
        return ResidencyStatus.TEMPORARY
    try:
        return ResidencyStatus(str(value).strip().upper())
    except ValueError as exc:
        raise ValidationError("residency_status", "unknown residency status") from exc


def _validate_codes[E: StrEnum](
    field_name: str,
    value: str | list[str] | None,
    enum_cls: type[E],
) -> frozenset[E]:
    if value is None or value == "":
        return frozenset()
    if isinstance(value, str):
        parts = [piece.strip().upper() for piece in value.split(",") if piece.strip()]
    else:
        parts = [str(piece).strip().upper() for piece in value if str(piece).strip()]
    result = set()
    for piece in parts:
        try:
            result.add(enum_cls(piece))
        except ValueError as exc:
            raise ValidationError(field_name, f"unknown code: {piece}") from exc
    return frozenset(result)


def validate_driving_entitlements(
    value: str | list[str] | None,
) -> frozenset[DrivingEntitlement]:
    return _validate_codes("driving_entitlements", value, DrivingEntitlement)


def validate_driving_restrictions(
    value: str | list[str] | None,
) -> frozenset[DrivingRestriction]:
    return _validate_codes("driving_restrictions", value, DrivingRestriction)


# --- portal types ---


CommandHandler = Callable[[Mapping[str, str]], Any]
Validator = Callable[[str], object]


@dataclass(frozen=True)
class Argument:
    """Declarative description of one user input field on a command.

    When `options` is set the shell offers a constrained choice; with
    `multi_select` it offers a checkbox list. Otherwise the shell asks for free
    text and runs `validator` on the answer with a retry budget.
    """

    key: str
    label: str
    default: str | None = None
    validator: Validator | None = None
    options: tuple[str, ...] | None = None
    multi_select: bool = False


@dataclass(frozen=True)
class Command:
    """Declarative description of one menu command.

    The shell interprets a command generically: collect every `Argument`, ask
    for `confirmation` if set, then call `handler` with the collected values.
    Adding a new command means appending one of these to a portal.
    """

    key: str
    label: str
    description: str
    arguments: Sequence[Argument]
    handler: CommandHandler
    confirmation: str | None = None
    group: str = ""


@dataclass
class Portal:
    """A bundle of commands available to one organisation role.

    Each portal carries its role, a display title and the list of commands the
    shell shows to that organisation. The same `MenuShell` drives every portal,
    so adding a new organisation only means building a new Portal.
    """

    role: OrganisationRole
    title: str
    description: str = ""
    commands: list[Command] = field(default_factory=list)

    def add(self, command: Command) -> None:
        self.commands.append(command)

    def find(self, key: str) -> Command | None:
        return next((c for c in self.commands if c.key == key), None)
