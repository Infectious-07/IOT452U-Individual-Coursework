from pathlib import Path

from digital_id.cli.app import _seed_sample_data
from digital_id.persistence.audit_repository import AuditRepository
from digital_id.persistence.database import bootstrap, connect
from digital_id.persistence.identity_repository import IdentityRepository
from digital_id.services.audit_service import AuditService
from digital_id.services.identity_service import IdentityService


def _service(tmp_path: Path) -> IdentityService:
    connection = connect(tmp_path / "seed.sqlite")
    bootstrap(connection)
    identities = IdentityRepository(connection)
    audit = AuditService(AuditRepository(connection))
    return IdentityService(identities, audit)


def test_seed_populates_empty_database(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _seed_sample_data(service)
    assert len(service.list_all()) == 5


def test_seed_skips_when_data_exists(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _seed_sample_data(service)
    _seed_sample_data(service)
    assert len(service.list_all()) == 5


def test_seed_creates_varied_statuses(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _seed_sample_data(service)
    identities = service.list_all()
    nationalities = {i.nationality for i in identities}
    assert len(nationalities) >= 2
