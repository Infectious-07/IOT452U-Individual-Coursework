# Digital ID Platform

![CI](https://github.com/Infectious-07/IOT452U-Individual-Coursework/actions/workflows/ci.yml/badge.svg)

Repository: https://github.com/Infectious-07/IOT452U-Individual-Coursework

A console based backend that lets a central authority manage Digital IDs while authorised consumer organisations verify them through dedicated portals. Built for the IOT452U Individual Coursework. Implementation is Python 3.14, standard library at runtime, with pytest, coverage and ruff used for development.

## Running

```
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m digital_id
```

The shell opens at portal selection. Pick a number to enter a portal, type `help` to see the commands for that portal, `portal` to return to the selection screen, and `quit` to leave the shell.

A `config.toml` at the working directory is read on start up. If absent, the system uses the defaults below.

```
[database]
path = "data/digital_id.sqlite"

[audit]
retention_days = 365
```

## Worked example

```
1. Central Authority (CENTRAL_AUTHORITY)
2. Tax Authority (TAX)
3. Driving Licence Authority (DVLA)
4. Bank (BANK)
5. Employer (EMPLOYER)
6. Welfare Services (WELFARE)
7. Local Authority (LOCAL_AUTHORITY)
portal> 1
entered Central Authority; type help for commands
central_authority> create ID-001 "Ada Lovelace" 1990-05-01
id=ID-001 name=Ada Lovelace dob=1990-05-01 status=ACTIVE updated_at=...
central_authority> suspend ID-001
id=ID-001 name=Ada Lovelace dob=1990-05-01 status=SUSPENDED updated_at=...
central_authority> portal
portal> 3
entered Driving Licence Authority; type help for commands
dvla> verify ID-001
id=ID-001 exists=True active_now=False restricted_now=True
```

## Architecture

The system is organised into thin layers.

```
src/digital_id
  domain/         entities, status enum, exceptions, transition rules, validators
  persistence/    SQLite identity repository and append only audit repository
  authorisation/  organisation roles and permission resolver
  services/       identity lifecycle, audit, verification, export and stats
  portals/        per organisation command sets that wrap services
  cli/            console shell and application entry point
  config/         settings loader
```

Lifecycle operations live in `IdentityService` and only accept the central authority role. Verification logic lives in `VerificationService` and returns a different response type per consumer role so each portal only sees the fields it needs. Both record audit events through a shared `AuditService`. Portals never call repositories directly.

Domain rules to note:
- A revoked Digital ID is terminal. Updates and further transitions are rejected.
- Suspend, revoke and reactivate are idempotent when the identity is already in the target state.
- Tax verification looks at the audit log to decide whether the identity was suspended at any point during the reporting period, including suspensions that began before the period started.
- Bank and employer responses carry only `valid_now`. Welfare and local authority also share the name when valid. DVLA receives `active_now` and `restricted_now`. Tax receives the full period view.

## Tests and lint

```
ruff check src tests
coverage run -m pytest
coverage report
```

CI runs the same commands on Python 3.14 on every push to `main` and on pull requests.

## Project layout

```
.
├── .github/workflows/ci.yml
├── pyproject.toml
├── requirements-dev.txt
├── README.md
├── src/digital_id/...
└── tests/...
```
