import contextlib
import io
from pathlib import Path

import pytest
from rich.console import Console

from digital_id.cli.app import build_portals
from digital_id.cli.prompter import ScriptedPrompter
from digital_id.cli.screen import Screen
from digital_id.cli.shell import _EXIT, MenuShell
from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository
from digital_id.services.audit_service import AuditService
from digital_id.services.export_service import ExportService
from digital_id.services.identity_service import IdentityService
from digital_id.services.stats_service import StatsService
from digital_id.services.verification import VerificationService

BASE_CREATE = [
    "ID-001",
    "Ada Lovelace",
    "1990-05-01",
    "GB",
    "10 Downing Street, London",
]


@pytest.fixture
def shell_setup(tmp_path: Path):
    connection = connect(tmp_path / "shell.sqlite")
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit_repo = AuditRepository(connection)
    audit = AuditService(audit_repo)
    identity_service = IdentityService(identities, audit)
    verification = VerificationService(identities, audit)
    exports = ExportService(identities, audit_repo)
    stats = StatsService(identities, audit_repo)
    portals = build_portals(identity_service, audit, verification, exports, stats)
    sink = io.StringIO()
    console = Console(file=sink, force_terminal=False, record=True, width=120)
    screen = Screen(console=console)
    return portals, screen, sink


def run_shell(shell_setup, answers):
    portals, screen, sink = shell_setup
    prompter = ScriptedPrompter(answers)
    shell = MenuShell(portals, prompter=prompter, screen=screen, pause_between_actions=False)
    with contextlib.suppress(SystemExit):
        shell.run()
    return sink.getvalue()


def test_create_and_show_identity(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "show",
            "ID-001",
            "__back__",
            _EXIT,
        ],
    )
    assert "ID-001" in output
    assert "Ada Lovelace" in output
    assert "ACTIVE" in output


def test_revoke_requires_confirmation_and_blocks_when_cancelled(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "revoke",
            "ID-001",
            False,
            "show",
            "ID-001",
            "__back__",
            _EXIT,
        ],
    )
    assert "ACTIVE" in output
    assert "Cancelled" in output


def test_revoke_completes_when_confirmed(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "revoke",
            "ID-001",
            True,
            "show",
            "ID-001",
            "__back__",
            _EXIT,
        ],
    )
    assert "REVOKED" in output


def test_dvla_verify_uses_driving_data(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "update_driving",
            "ID-001",
            "B,C1",
            "GLASSES",
            "__back__",
            "DVLA",
            "verify",
            "ID-001",
            "__back__",
            _EXIT,
        ],
    )
    assert "B" in output
    assert "C1" in output
    assert "GLASSES" in output


def test_employer_sees_right_to_work(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "update_eligibility",
            "ID-001",
            "yes",
            "CITIZEN",
            "__back__",
            "EMPLOYER",
            "verify",
            "ID-001",
            "__back__",
            _EXIT,
        ],
    )
    assert "right to work" in output.lower()
    assert "yes" in output


def test_tax_period_check(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "update_tax",
            "ID-001",
            "UTR12345",
            "HIGHER",
            "__back__",
            "TAX",
            "verify",
            "ID-001",
            "2026-01-01",
            "2026-12-31",
            "__back__",
            _EXIT,
        ],
    )
    assert "HIGHER" in output


def test_welfare_verify_shows_residency(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "update_eligibility",
            "ID-001",
            "yes",
            "CITIZEN",
            "__back__",
            "WELFARE",
            "verify",
            "ID-001",
            "__back__",
            _EXIT,
        ],
    )
    assert "CITIZEN" in output
    assert "Ada Lovelace" in output


def test_unknown_identity_is_rejected(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "show",
            "ID-999",
            "__back__",
            _EXIT,
        ],
    )
    assert "rejected: identity not found: ID-999" in output


def test_validation_error_is_rejected(shell_setup) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            "BAD",
            "Ada",
            "1990-05-01",
            "GB",
            "10 Downing Street",
            "__back__",
            _EXIT,
        ],
    )
    assert "rejected" in output


def test_export_writes_files(shell_setup, tmp_path: Path) -> None:
    output = run_shell(
        shell_setup,
        [
            "CENTRAL_AUTHORITY",
            "create",
            *BASE_CREATE,
            "export",
            tmp_path.as_posix(),
            "__back__",
            _EXIT,
        ],
    )
    assert "Exported" in output
    assert (tmp_path / "identities.csv").exists()
    assert (tmp_path / "audit.csv").exists()


def test_exit_from_portal_selection(shell_setup) -> None:
    output = run_shell(shell_setup, [_EXIT])
    assert "Goodbye" in output
