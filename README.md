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
  models.py       identity entity, enums, roles, exceptions, transitions, validators, portal types
  database.py     SQLite schema, connection, identity and audit repositories
  services.py     identity lifecycle, audit, verification, export and stats services
  portals.py      per organisation Command definitions wired to service handlers
  shell.py        prompter protocol, screen, render helpers and the menu shell
  app.py          portal wiring, sample data seeding and application entry point
  config.py       settings loader (reads config.toml with fallback defaults)
```

The codebase follows a flat module layout where each module only depends on those above it in the list: `models` has no imports from other project modules, `database` depends only on `models`, `services` depends on both, and `shell`, `portals` plus `app` sit at the top. This keeps the business rules testable without infrastructure and ensures changes to the UI or database do not ripple through unrelated code.

Lifecycle operations live in `IdentityService` and only accept the central authority role. Verification logic lives in `VerificationService` and returns a different response type per consumer role. Portals describe their commands as data: each `Command` lists its `Argument` set and an optional confirmation message. The shell drives the prompts and renders results as rich tables.

## Data flow

A typical request moves through four layers.

```
User input                       Screen output
    |                                  ^
    v                                  |
 MenuShell  --- Prompter ----------> Screen / rich Console
    |                                  ^
    v                                  |
 Portal     --- Command.handler ----> render function
    |                                  ^
    v                                  |
 Service    --- business rules -----> response dataclass
    |                                  ^
    v                                  |
 Repository --- SQLite / audit log --> domain entity
```

1. The `MenuShell` shows portal and command menus through the `Prompter` protocol. It collects arguments, runs validators and asks for confirmation when the command says so.
2. The selected `Command` handler calls the appropriate service method, passing validated arguments.
3. The service enforces authorisation with `require()`, applies domain rules, persists the change through its repository and writes an audit event.
4. The handler passes the returned entity or response dataclass to a render function, which builds a rich `Table` or `Panel` that the shell prints to the console.

Verification follows the same path but the service returns a role-scoped response (for example `TaxResponse`) that omits fields the consumer is not entitled to see.

## Design decisions

**Frozen dataclasses for entities.** `DigitalID` and `AuditEvent` are immutable. Every mutation returns a new instance via `dataclasses.replace`, which prevents accidental aliasing bugs and makes it obvious when state has changed. The `with_*` methods on `DigitalID` enforce the `updated_at` timestamp and keep the replace call in one place.

**Repository pattern for persistence.** `IdentityRepository` and `AuditRepository` hide SQLite behind a narrow interface (add, get, update, list). Services never see SQL strings. This would let us swap to a different store without changing any business logic.

**Protocol-based Prompter for testability.** The `Prompter` Protocol defines four methods (choose, choose_many, ask, confirm). `QuestionaryPrompter` implements them with real terminal UI; `ScriptedPrompter` pops answers from a list. The menu shell accepts either, so every flow can be tested end to end without user interaction.

**Command and Argument dataclasses as declarative UI.** Each portal builds a list of `Command` objects that carry their arguments, validators, handler closure and optional confirmation message. The shell interprets this data generically. Adding a new command means adding one `portal.add(Command(...))` call; no shell code changes.

**Role-based authorisation at the service boundary.** Every service method calls `require(actor, action)` as its first line. The permission map is a plain dictionary in `models.py`. Consumer portals additionally check the exact role before calling verification, so a tax actor can never call the employer endpoint.

**Append-only audit log.** Every lifecycle action and every verification request writes an `AuditEvent`. The audit repository has no update or delete methods. Tax verification replays the audit log to detect suspensions within a reporting period, including suspensions that started before the window.

**Flat module layout with a strict dependency rule.** Seven modules in a single package, each only importing from modules earlier in the dependency chain: `models` (zero project imports), `database`, `services`, `shell`, `portals`, `app`, `config`. This makes the build order obvious, prevents circular imports and keeps the project navigable without nested packages.

**Error hierarchy rooted in DigitalIdError.** Every domain error inherits from one base class. The shell catches `DigitalIdError` to show a user-friendly message, while `ValueError` and unexpected exceptions propagate separately. This keeps error handling predictable without broad except clauses.

## Domain rules

Status transitions follow a strict state machine.

```
          suspend          revoke
 ACTIVE ---------> SUSPENDED ---------> REVOKED
    |                  |                  (terminal)
    |   reactivate     |
    |  <----------     |
    |                  |
    +--- revoke -----------------------> REVOKED
```

- A revoked Digital ID is terminal. Updates and further transitions are rejected.
- Suspend, revoke and reactivate are idempotent when the identity is already in the target state.
- Tax verification uses event replay to determine whether the identity was suspended at any point during the reporting period, including suspensions that began before the period started. This is a lightweight form of event sourcing: the audit log is the source of truth for historical status.
- Each verification response carries only the attributes its role is entitled to see. When an identity is inactive the response hides sensitive fields.
- All input is validated at the service boundary. Validators normalise casing and whitespace before checking format against compiled regex patterns.
- SQL queries use parameterised statements throughout to prevent injection.

## Tests and lint

```
ruff check src tests
coverage run -m pytest
coverage report
```

The test suite has 167 tests across 6 test modules:

| module | scope |
| --- | --- |
| `test_domain.py` | entity immutability, transitions, exceptions, validators, roles, config, screen, prompter |
| `test_persistence.py` | identity and audit repository roundtrips, schema migration |
| `test_services.py` | identity lifecycle, export, stats, noop-on-unchanged, idempotent transitions |
| `test_verification.py` | tax period checks, DVLA entitlements, employer right to work, cross-role authorisation |
| `test_render.py` | rich table and panel rendering for every response type |
| `test_shell_flows.py` | end-to-end shell flows, validation retries, seed data, edge cases |

Branch coverage is 99 percent with zero missing statements. CI runs the same commands on Python 3.14 on every push to `main` and on pull requests. The pipeline enforces a minimum 95 percent coverage threshold.
