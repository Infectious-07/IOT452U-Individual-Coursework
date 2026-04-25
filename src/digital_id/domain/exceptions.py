from __future__ import annotations


class DigitalIdError(Exception):
    # base class so the application can catch every domain error in one place
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
