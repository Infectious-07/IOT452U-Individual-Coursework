from __future__ import annotations

from collections.abc import Sequence

from rich import box
from rich.table import Table

from ..domain.audit import AuditEvent
from ..domain.identity import DigitalID
from ..services.stats_service import Snapshot
from .theme import ACCENT, ACCENT2, BORDER, BORDER_DIM, MUTED, colour_status


def _codes(codes) -> str:
    return ", ".join(sorted(code.value for code in codes)) or "-"


def _detail_table(title: str) -> Table:
    table = Table(
        title=f"[bold]{title}[/]",
        show_header=False,
        box=box.ROUNDED,
        border_style=BORDER_DIM,
        title_style=ACCENT,
        padding=(0, 1),
    )
    table.add_column("field", style=ACCENT2, no_wrap=True, min_width=22)
    table.add_column("value")
    return table


def _list_table(title: str) -> Table:
    return Table(
        title=f"[bold]{title}[/]",
        box=box.ROUNDED,
        border_style=BORDER_DIM,
        title_style=ACCENT,
        header_style=ACCENT,
        row_styles=["", MUTED],
        padding=(0, 1),
    )


def identity_panel(identity: DigitalID) -> Table:
    table = _detail_table(f"Digital ID  {identity.id}")
    table.add_row("name", identity.name)
    table.add_row("dob", identity.dob.isoformat())
    table.add_row("nationality", identity.nationality)
    table.add_row("postcode", identity.postcode)
    table.add_row(
        "status",
        f"[{colour_status(identity.status)}]{identity.status.value}[/]",
    )
    table.add_row("tax reference", identity.tax_reference or "-")
    table.add_row("tax band", identity.tax_band.value if identity.tax_band else "-")
    table.add_row("driving entitlements", _codes(identity.driving_entitlements))
    table.add_row("driving restrictions", _codes(identity.driving_restrictions))
    table.add_row("right to work", "yes" if identity.right_to_work else "no")
    table.add_row("residency", identity.residency_status.value)
    table.add_row("updated at", identity.updated_at.isoformat(timespec="seconds"))
    return table


def identity_list_table(identities: Sequence[DigitalID]) -> Table:
    table = _list_table("Digital IDs")
    table.add_column("id", style=BORDER)
    table.add_column("name")
    table.add_column("status")
    table.add_column("nationality")
    table.add_column("tax band")
    table.add_column("right to work")
    for identity in identities:
        table.add_row(
            identity.id,
            identity.name,
            f"[{colour_status(identity.status)}]{identity.status.value}[/]",
            identity.nationality,
            identity.tax_band.value if identity.tax_band else "-",
            "yes" if identity.right_to_work else "no",
        )
    return table


def audit_table(events: Sequence[AuditEvent], title: str = "Audit events") -> Table:
    table = _list_table(title)
    table.add_column("occurred at", style=BORDER)
    table.add_column("actor")
    table.add_column("action", style="bold")
    table.add_column("identity")
    table.add_column("payload", style=MUTED)
    for event in events:
        table.add_row(
            event.occurred_at.isoformat(timespec="seconds"),
            event.actor_role,
            event.action.value,
            event.identity_id or "-",
            str(dict(event.payload)),
        )
    return table


def stats_table(snapshot: Snapshot) -> Table:
    table = _detail_table("System snapshot")
    table.add_row("total identities", str(snapshot.total))
    for status, count in snapshot.by_status.items():
        table.add_row(f"  {status.lower()}", str(count))
    table.add_row("events in last 7 days", str(snapshot.events_last_7_days))
    return table


def tax_response_table(response) -> Table:
    table = _detail_table(f"Tax check  {response.identity_id}")
    table.add_row("exists", "yes" if response.exists else "no")
    table.add_row("active now", "yes" if response.active_now else "no")
    table.add_row(
        "suspended in period",
        "[bold red]yes[/]" if response.suspended_in_period else "no",
    )
    table.add_row(
        "period",
        f"{response.period_start.isoformat()} .. {response.period_end.isoformat()}",
    )
    table.add_row("tax reference", response.tax_reference or "-")
    table.add_row(
        "tax band", response.tax_band.value if response.tax_band else "-"
    )
    return table


def dvla_response_table(response) -> Table:
    table = _detail_table(f"DVLA check  {response.identity_id}")
    table.add_row("exists", "yes" if response.exists else "no")
    table.add_row(
        "active now",
        "[bold green]yes[/]" if response.active_now else "[red]no[/]",
    )
    table.add_row(
        "restricted now",
        "[bold red]yes[/]" if response.restricted_now else "no",
    )
    table.add_row("entitlements", _codes(response.entitlements))
    table.add_row("restrictions", _codes(response.restrictions))
    return table


def employer_response_table(response) -> Table:
    table = _detail_table(f"Employer check  {response.identity_id}")
    table.add_row(
        "valid now",
        "[bold green]yes[/]" if response.valid_now else "[red]no[/]",
    )
    table.add_row("right to work", "yes" if response.right_to_work else "no")
    return table
