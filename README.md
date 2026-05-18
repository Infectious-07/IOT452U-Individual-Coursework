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

The shell clears the screen and shows an arrow key portal menu. After selecting a portal you pick a command from another arrow key menu. Each command then asks for its arguments one at a time. Destructive actions such as revoke and suspend prompt for confirmation before they run.

A `config.toml` at the working directory is read on start up. If absent, the defaults below are used.

```
[database]
path = "data/digital_id.sqlite"
```

## Digital ID schema

Each Digital ID carries the following attributes.

| field | who sets it | who can see it |
| --- | --- | --- |
| id | central authority on create | every portal that holds it |
| name | central authority | central authority, welfare, local authority |
| dob | central authority on create | central authority |
| nationality | central authority on create | central authority |
| address | central authority | central authority |
| status | central authority via suspend, revoke, reactivate | every portal as a yes or no |
| tax_reference | central authority via update tax | tax |
| tax_band | central authority via update tax | tax |
| driving_entitlements | central authority via update driving | dvla |
| driving_restrictions | central authority via update driving | dvla |
| right_to_work | central authority via update eligibility | employer |
| residency_status | central authority via update eligibility | welfare, local authority |

Each consumer portal sees only the attributes its organisation needs.

## Architecture

```
src/digital_id
  domain/         entities, status and attribute enums, exceptions, transitions, validators
  persistence/    SQLite identity repository and append only audit repository
  authorisation/  organisation roles and permission resolver
  services/       identity lifecycle, audit, verification, export and stats
  portals/        per organisation Command definitions
  cli/            screen, theme, prompter, render and the menu shell
  config/         settings loader
```

Lifecycle operations live in `IdentityService` and only accept the central authority role. Verification logic lives in `VerificationService` and returns a different response type per consumer role. Portals describe their commands as data: each `Command` lists its `Argument` set and an optional confirmation message. The shell drives the prompts and renders results as rich tables.

Domain rules to note:
- A revoked Digital ID is terminal. Updates and further transitions are rejected.
- Suspend, revoke and reactivate are idempotent when the identity is already in the target state.
- Tax verification looks at the audit log to decide whether the identity was suspended at any point during the reporting period, including suspensions that began before the period started.
- Each verification response carries only the attributes its role is entitled to see.

## Tests and lint

```
ruff check src tests
coverage run -m pytest
coverage report
```

CI runs the same commands on Python 3.14 on every push to `main` and on pull requests.
