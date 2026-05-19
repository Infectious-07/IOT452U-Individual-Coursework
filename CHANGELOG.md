# Changelog

All notable changes to this project are recorded here. The format follows the spirit of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-19

First complete release for the IOT452U Individual Coursework.

### Added
- Central authority lifecycle commands (create, show, list, update name, update postcode,
  update tax details, update driving entitlements, update eligibility, suspend, revoke,
  reactivate, history, export, stats).
- Tax Authority portal with period-based verification using audit-log event replay.
- Driving Licence Authority portal returning active status, restriction flag,
  entitlements and restrictions.
- Employer portal returning validity and right to work.
- SQLite persistence with schema migration and an append-only audit log.
- Role-based authorisation at the service boundary.
- Sample data seeding on first run.
- Rich terminal UI with arrow key menus, banner and styled tables.
- 167 unit and end-to-end tests, 99 percent branch coverage.
- GitHub Actions CI: ruff lint plus pytest with a 98 percent coverage gate.

### Project organisation
- Five sprint milestones, 44 closed issues with labels.
- Flat seven-module source layout under `src/`.
