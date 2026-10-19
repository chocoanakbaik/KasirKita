# KasirKita Desktop — Architecture Baseline

**Status:** Initial design baseline; compatibility and implementation remain to be verified.

## 1. Technology direction

Use Python for application logic, Tkinter/ttk for the initial native desktop interface, and SQLite for local persistence. These are available through the Python standard library, which keeps the initial dependency surface small and avoids a required server, paid service, or network connection.

This is a deliberate baseline, not a claim that packaging or every Windows release is already verified. The exact Python version and installer strategy must be selected only after checking the intended Windows support matrix. In particular, support for older Windows versions must be tested on the actual target environment before it is advertised.

### Why this baseline

- No mandatory network or hosted backend.
- SQLite supports local transactions and relational constraints.
- The Python standard library provides integer arithmetic, sqlite3, unittest, and Tkinter/ttk.
- A small dependency surface is easier to audit and package.
- UI styling can be improved after core workflows and data integrity are stable.

## 2. Proposed package boundaries

The codebase should keep interface code separate from business rules and persistence:

- kasirkita/app.py: application composition and startup.
- kasirkita/ui/: windows, dialogs, widgets, and UI state only.
- kasirkita/domain/: validated domain values and business rules.
- kasirkita/services/: use cases coordinating domain logic and repositories.
- kasirkita/infrastructure/database/: database connection, schema versioning, migrations, and repository implementations.
- kasirkita/infrastructure/backup/: validated backup and restore operations.
- tests/unit/: fast tests for deterministic business rules.
- tests/integration/: database and service interaction tests.
- docs/: requirements, architecture decisions, test evidence, and release notes.

UI handlers must not contain authoritative pricing, tax, stock, or transaction algorithms. They should call application services and render returned results.

## 3. Transaction invariants

A completed sale is one logical operation. Persisting a sale header, sale lines, payment information, and stock movement must use a single database transaction. If any required step fails, the entire operation must roll back.

The service layer must re-read authoritative product prices and stock within the transaction. It must validate product status, quantity, price representation, and stock policy before finalizing a sale. Duplicate submissions must not accidentally create duplicate sales; the final design must define a stable idempotency or submission guard appropriate to the desktop workflow.

Historical sales must retain the actual unit price and tax configuration applied at sale time. Editing a product later must not rewrite historical receipts or reports.

## 4. Money and rounding

Represent IDR amounts as integer rupiah values when fractions of a rupiah are not part of the supported model. Never use binary floating-point values for financial arithmetic. Quantity representation must be decided explicitly before supporting fractional-unit goods; version 1 may restrict quantity to positive whole units unless the requirements are amended.

Tax-inclusive versus tax-exclusive pricing and rounding policy are not yet finalized. They must be decided and tested before tax is implemented.

## 5. Database lifecycle

- Store application data in a per-user writable data directory, not beside the executable by default.
- Enable foreign-key enforcement on every database connection.
- Use explicit, versioned migrations.
- Configure a suitable busy timeout and use short transactions.
- Never delete or replace the live database during backup validation.
- Restore into a separate temporary database, validate schema and integrity, then perform a controlled replacement with recovery handling.
- Provide a documented way to identify the active data directory and create a backup.
- Keep credentials and sensitive payment data out of logs. Version 1 should not store card credentials.

## 6. Error handling and observability

Domain and service layers should return explicit success/failure outcomes or raise documented domain-specific exceptions. The UI must show actionable messages without exposing tracebacks to ordinary users. Technical logs may include diagnostic context but must avoid secrets and unnecessary personal data.

Unexpected errors must not be silently swallowed. Tests should verify rollback behavior and ensure the user can distinguish a failed transaction from a completed one.

## 7. Test strategy

Use Python's unittest as the baseline test runner to avoid mandatory third-party test dependencies. Tests should cover:
- Valid and invalid domain inputs.
- Monetary totals and boundary cases.
- Tax-disabled and tax-enabled calculations once the tax policy is approved.
- Sale commit and rollback behavior.
- Stock changes and prevention of negative stock where that policy applies.
- Foreign-key and uniqueness constraints.
- Historical transaction stability.
- Backup/restore validation and failure recovery.
- UI smoke checks where they can be reliably automated.

A test passing on one operating system does not prove compatibility with all Windows versions. Keep runtime tests, packaging tests, and OS compatibility tests as separate evidence.

## 8. Implementation sequence

1. Confirm requirements and platform support matrix.
2. Establish project layout and test command.
3. Implement database connection lifecycle and schema migration foundation.
4. Implement domain money and quantity rules.
5. Implement product catalogue persistence.
6. Implement sale calculation and atomic checkout.
7. Implement stock movement and transaction history.
8. Implement reporting from persisted records.
9. Implement tax only after the policy is specified.
10. Build UI workflows on top of tested services.
11. Implement backup/restore, packaging, accessibility checks, and regression testing.
12. Prepare a release checklist and user guide.

No later layer should invent business rules independently of the domain/service layer.
