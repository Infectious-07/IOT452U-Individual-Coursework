from datetime import date, datetime
from io import StringIO

from rich.console import Console
from tests.conftest import make_sample_identity

from digital_id.models import (
    AuditAction,
    AuditEvent,
    DrivingEntitlement,
    DrivingRestriction,
    TaxBand,
)
from digital_id.services import DvlaResponse, EmployerResponse, Snapshot, TaxResponse
from digital_id.shell import (
    audit_table,
    dvla_response_table,
    employer_response_table,
    identity_list_table,
    identity_panel,
    stats_table,
    tax_response_table,
)


def _render(renderable) -> str:
    buf = StringIO()
    Console(file=buf, force_terminal=False, width=120).print(renderable)
    return buf.getvalue()


def test_identity_panel_contains_all_fields() -> None:
    table = identity_panel(make_sample_identity())
    rendered = _render(table)
    assert "Ada Lovelace" in rendered
    assert "ID-001" in rendered
    assert "ACTIVE" in rendered
    assert "CITIZEN" in rendered


def test_identity_list_table_renders_rows() -> None:
    ids = [make_sample_identity("ID-001"), make_sample_identity("ID-002")]
    rendered = _render(identity_list_table(ids))
    assert "ID-001" in rendered
    assert "ID-002" in rendered


def test_audit_table_renders_events() -> None:
    events = [
        AuditEvent(
            occurred_at=datetime(2026, 1, 1, 10, 0),
            actor_role="CENTRAL_AUTHORITY",
            action=AuditAction.CREATE,
            identity_id="ID-001",
            payload={"name": "Ada"},
        ),
        AuditEvent(
            occurred_at=datetime(2026, 1, 2, 10, 0),
            actor_role="CENTRAL_AUTHORITY",
            action=AuditAction.SUSPEND,
            identity_id="ID-001",
            payload={},
        ),
    ]
    rendered = _render(audit_table(events, title="Test history"))
    assert "CREATE" in rendered
    assert "SUSPEND" in rendered


def test_stats_table_renders_snapshot() -> None:
    snapshot = Snapshot(
        total=5,
        by_status={"ACTIVE": 3, "SUSPENDED": 1, "REVOKED": 1},
        events_last_7_days=12,
    )
    rendered = _render(stats_table(snapshot))
    assert "5" in rendered
    assert "12" in rendered


def test_tax_response_table_renders() -> None:
    response = TaxResponse(
        identity_id="ID-001",
        exists=True,
        active_now=True,
        suspended_in_period=False,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        tax_reference="UTR12345",
        tax_band=TaxBand.HIGHER,
    )
    rendered = _render(tax_response_table(response))
    assert "ID-001" in rendered
    assert "UTR12345" in rendered


def test_tax_response_table_shows_suspended_flag() -> None:
    response = TaxResponse(
        identity_id="ID-001",
        exists=True,
        active_now=False,
        suspended_in_period=True,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        tax_reference=None,
        tax_band=None,
    )
    rendered = _render(tax_response_table(response))
    assert "yes" in rendered


def test_dvla_response_table_renders() -> None:
    response = DvlaResponse(
        identity_id="ID-001",
        exists=True,
        active_now=True,
        restricted_now=False,
        entitlements=frozenset({DrivingEntitlement.B}),
        restrictions=frozenset({DrivingRestriction.GLASSES}),
    )
    rendered = _render(dvla_response_table(response))
    assert "ID-001" in rendered
    assert "B" in rendered


def test_employer_response_table_renders() -> None:
    response = EmployerResponse(
        identity_id="ID-001",
        valid_now=True,
        right_to_work=True,
    )
    rendered = _render(employer_response_table(response))
    assert "ID-001" in rendered
    assert "yes" in rendered
