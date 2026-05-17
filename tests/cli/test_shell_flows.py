import io
from pathlib import Path

import pytest

from digital_id.authorisation.roles import OrganisationRole
from digital_id.cli.shell import Shell
from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository
from digital_id.portals.central_authority import build_central_portal
from digital_id.portals.consumer import (
    build_dvla_portal,
    build_lookup_portal,
    build_tax_portal,
    build_validity_portal,
)
from digital_id.services.audit_service import AuditService
from digital_id.services.export_service import ExportService
from digital_id.services.identity_service import IdentityService
from digital_id.services.stats_service import StatsService
from digital_id.services.verification import VerificationService


def _scripted_reader(lines: list[str]):
    iterator = iter(lines)

    def _read(_prompt: str) -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise EOFError from exc

    return _read


@pytest.fixture
def wired(tmp_path: Path):
    connection = connect(tmp_path / "shell.sqlite")
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit_repo = AuditRepository(connection)
    audit = AuditService(audit_repo)
    identity_service = IdentityService(identities, audit)
    verification = VerificationService(identities, audit)
    exports = ExportService(identities, audit_repo)
    stats = StatsService(identities, audit_repo)
    writer = io.StringIO()

    def to_writer(message: str) -> None:
        writer.write(message + "\n")

    portals = {
        OrganisationRole.CENTRAL_AUTHORITY: build_central_portal(
            identity_service, audit, exports, stats, to_writer
        ),
        OrganisationRole.TAX: build_tax_portal(verification, to_writer),
        OrganisationRole.DVLA: build_dvla_portal(verification, to_writer),
        OrganisationRole.BANK: build_validity_portal(
            OrganisationRole.BANK, "Bank", verification, to_writer
        ),
        OrganisationRole.WELFARE: build_lookup_portal(
            OrganisationRole.WELFARE, "Welfare", verification, to_writer
        ),
    }
    return portals, writer


def test_central_authority_flow(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(
            [
                "1",
                "create ID-001 \"Ada Lovelace\" 1990-05-01",
                "show ID-001",
                "suspend ID-001",
                "show ID-001",
                "stats",
                "quit",
            ]
        ),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    assert "id=ID-001" in output
    assert "status=ACTIVE" in output
    assert "status=SUSPENDED" in output
    assert "total=1" in output


def test_dvla_flow_after_central_creates(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(
            [
                "1",
                "create ID-001 \"Ada Lovelace\" 1990-05-01",
                "portal",
                "3",
                "verify ID-001",
                "quit",
            ]
        ),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    assert "active_now=True" in output
    assert "restricted_now=False" in output


def test_tax_portal_period_verification(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(
            [
                "1",
                "create ID-001 \"Ada Lovelace\" 1990-05-01",
                "portal",
                "2",
                "verify ID-001 2026-01-01 2026-12-31",
                "quit",
            ]
        ),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    assert "active_now=True" in output
    assert "suspended_in_period=False" in output


def test_welfare_lookup_portal(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(
            [
                "1",
                "create ID-001 \"Ada Lovelace\" 1990-05-01",
                "portal",
                "5",
                "verify ID-001",
                "quit",
            ]
        ),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    assert "valid_now=True" in output
    assert "name=Ada Lovelace" in output


def test_unknown_command_is_reported(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(["1", "nope", "quit"]),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    assert "unknown command: nope" in output


def test_usage_message_prints_plainly(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(["1", "create ID-001 Ada", "quit"]),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    assert "usage: create <id> <full name> <dob>" in output
    assert "rejected: usage:" not in output


def test_domain_error_prints_with_rejected_prefix(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(["1", "show ID-999", "quit"]),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    assert "rejected: identity not found: ID-999" in output


def test_bank_cannot_run_lifecycle_commands(wired) -> None:
    portals, writer = wired
    shell = Shell(
        portals,
        reader=_scripted_reader(
            [
                "4",
                "verify ID-999",
                "quit",
            ]
        ),
        writer=writer,
    )
    shell.run()
    output = writer.getvalue()
    # bank portal has only verify; create is not registered there
    assert "id=ID-999 valid_now=False" in output
