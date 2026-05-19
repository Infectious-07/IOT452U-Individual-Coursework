# Digital ID Platform

![CI](https://github.com/Infectious-07/IOT452U-Individual-Coursework/actions/workflows/ci.yml/badge.svg)

Repository: https://github.com/Infectious-07/IOT452U-Individual-Coursework

A console backend that lets a central authority manage Digital IDs while authorised consumer organisations verify them through dedicated portals. Built for the IOT452U Individual Coursework. The runtime uses Python 3.14 with questionary and rich for the terminal interface; pytest, coverage and ruff are used during development.

## Running

```
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m digital_id
```

The shell clears the screen and shows an ASCII art banner followed by an arrow key portal menu. After selecting a portal you pick a command from another arrow key menu. Each command then asks for its arguments one at a time. Destructive actions such as revoke and suspend prompt for confirmation before they run.

A `config.toml` at the working directory is read on start up. If absent, the defaults below are used.

```toml
[database]
path = "data/digital_id.sqlite"
```

## Portals

The system has four portals, each with a different level of access.

| portal | role | purpose |
| --- | --- | --- |
| Central Authority | `CENTRAL_AUTHORITY` | Full lifecycle management: create, update, suspend, revoke, reactivate, list, history, export, stats |
| Tax Authority | `TAX` | Period-based verification: checks identity exists, is active and was not suspended during a reporting period. Returns tax reference and band |
| Driving Licence Authority | `DVLA` | Licensing verification: checks active status and restriction flag. Returns driving entitlements and restrictions |
| Employer | `EMPLOYER` | Employment verification: checks identity is valid and returns right to work status |

Each consumer portal sees only the attributes its organisation needs. When an identity is not active the response hides sensitive fields and returns only the validity flag.

## Digital ID schema

Each Digital ID carries the following attributes.

| field | who sets it | who can see it |
| --- | --- | --- |
| id | central authority on create | every portal that holds it |
| name | central authority | central authority |
| dob | central authority on create | central authority |
| nationality | central authority on create | central authority |
| postcode | central authority | central authority |
| status | central authority via suspend, revoke, reactivate | every portal as a yes or no |
| tax_reference | central authority via update tax | tax |
| tax_band | central authority via update tax | tax |
| driving_entitlements | central authority via update driving | dvla |
| driving_restrictions | central authority via update driving | dvla |
| right_to_work | central authority via update eligibility | employer |
| residency_status | central authority via update eligibility | central authority |

## Architecture

```
src/digital_id
  domain/         identity entity, enums, roles, exceptions, transitions, validators
  persistence/    SQLite identity repository and append only audit repository
  services/       identity lifecycle, audit, verification, export and stats
  portals/        per organisation Command definitions wired to service handlers
  cli/            screen, prompter protocol, render helpers and the menu shell
  config.py       settings loader (reads config.toml with fallback defaults)
```

The codebase follows a layered architecture where each layer only depends on the one below it: `domain` has no imports from other layers, `persistence` depends only on `domain`, `services` depend on both, and `portals` plus `cli` sit at the top. This keeps the business rules testable without infrastructure and ensures changes to the UI or database do not ripple through unrelated code.

Lifecycle operations live in `IdentityService` and only accept the central authority role. Verification logic lives in `VerificationService` and returns a different response type per consumer role. Portals describe their commands as data: each `Command` lists its `Argument` set and an optional confirmation message. The shell drives the prompts and renders results as rich tables.

## Design decisions

**Frozen dataclasses for entities.** `DigitalID` and `AuditEvent` are immutable. Every mutation returns a new instance via `dataclasses.replace`, which prevents accidental aliasing bugs and makes it obvious when state has changed. The `with_*` methods on `DigitalID` enforce the `updated_at` timestamp and keep the replace call in one place.

**Repository pattern for persistence.** `IdentityRepository` and `AuditRepository` hide SQLite behind a narrow interface (add, get, update, list). Services never see SQL strings. This would let us swap to a different store without changing any business logic.

**Protocol-based Prompter for testability.** The `Prompter` Protocol defines four methods (choose, choose_many, ask, confirm). `QuestionaryPrompter` implements them with real terminal UI; `ScriptedPrompter` pops answers from a list. The menu shell accepts either, so every flow can be tested end to end without user interaction.

**Command and Argument dataclasses as declarative UI.** Each portal builds a list of `Command` objects that carry their arguments, validators, handler closure and optional confirmation message. The shell interprets this data generically. Adding a new command means adding one `portal.add(Command(...))` call; no shell code changes.

**Role-based authorisation at the service boundary.** Every service method calls `require(actor, action)` as its first line. The permission map is a plain dictionary in `roles.py`. Consumer portals additionally check the exact role before calling verification, so a tax actor can never call the employer endpoint.

**Append-only audit log.** Every lifecycle action and every verification request writes an `AuditEvent`. The audit repository has no update or delete methods. Tax verification replays the audit log to detect suspensions within a reporting period, including suspensions that started before the window.

## Domain rules

- A revoked Digital ID is terminal. Updates and further transitions are rejected.
- Suspend, revoke and reactivate are idempotent when the identity is already in the target state.
- Tax verification replays the audit log to determine whether the identity was suspended at any point during the reporting period, including suspensions that began before the period started.
- Each verification response carries only the attributes its role is entitled to see.

## Tests and lint

```
ruff check src tests
coverage run -m pytest
coverage report
```

CI runs the same commands on Python 3.14 on every push to `main` and on pull requests. The pipeline enforces a minimum 90 percent branch coverage threshold.
