# KasirKita — Product Requirements (Desktop v1)

**Status:** Draft baseline; implementation must follow approved requirements.  
**Product:** KasirKita Desktop  
**Target platform:** Laptop and desktop computers.  
**Primary market:** Indonesian micro and small businesses.

## 1. Product objective

Build a reliable desktop point-of-sale application that can be packaged and sold as a digital product. The first release prioritizes correct transaction handling, durable local data, clear workflows, and maintainability over a large feature count.

## 2. Version 1 boundaries

### Included in the initial release plan

- Local desktop application for laptop and desktop computers.
- Product catalogue and product search.
- Cashier/cart workflow and transaction totals.
- Configurable payment method records, beginning with cash.
- Transaction history and receipt representation.
- Stock movements tied to completed sales and permitted stock adjustments.
- Basic sales summaries derived from persisted transactions.
- Store profile and application settings.
- Optional tax configuration. Tax must be explicitly configurable and disabled by default until the business configures it.
- Local database backup and restore with validation.
- Input validation, clear error messages, and audit-relevant timestamps.
- Automated tests for business rules and database operations.

### Excluded unless explicitly approved later

- Android or mobile app.
- Cloud services, hosted database, mandatory account, or mandatory internet access.
- Multi-device live synchronization.
- Online payment gateway integrations.
- Payroll, accounting, or tax filing.
- Claims of legal or tax compliance without a separate review of current Indonesian requirements.
- Automatic updates that silently replace user data or application files.

## 3. Desktop and compatibility policy

The initial product is desktop-first. The implementation must document its supported Windows versions based on actual test results, not assumptions. The developer's available test environment may include older Windows versions, so avoid choosing dependencies solely because they are fashionable or recent.

Prefer a small, locally available technology stack and avoid unnecessary external services. Before selecting a GUI framework or packaging method, record compatibility constraints and test the proposed stack on the oldest intended supported Windows version. If a version cannot be tested, label compatibility as unverified.

## 4. Data integrity principles

- Use a local relational database with transactions for operations that must succeed or fail together.
- Store monetary values as integer minor units (for example, rupiah as whole integer amounts) or another explicitly documented exact representation. Do not use binary floating-point arithmetic for financial totals.
- Calculate transaction totals from validated line items and explicit pricing/tax rules; do not trust UI-displayed totals as authoritative input.
- A completed sale, its sale lines, payment records, and stock movements must be committed atomically.
- Failed or cancelled sales must not leave partial stock deductions or partial financial records.
- Give each persisted record a stable identifier and timestamps where appropriate.
- Use database constraints and application validation together; neither replaces the other.
- Backups must be written safely, and restores must be validated before replacing current data.
- Avoid destructive migrations. Schema changes must be versioned and tested against a copy of representative data.

## 5. Tax and PPN behavior

Tax is a configurable business feature, not a forced default. The application must allow tax to be disabled. When enabled, the configured tax rules must be clearly shown in settings and reflected consistently in transaction calculations, receipts, and reports. The application must not assume that every business is required to charge PPN or that every business can charge it. The business owner is responsible for configuring the application according to their actual tax status and applicable rules.

Tax calculation policy, rounding, whether prices are tax-inclusive or tax-exclusive, and how historical transactions retain the rule used at sale time must be specified and tested before tax functionality is implemented.

## 6. Quality gates

A module is not considered complete merely because it runs once.

Before a module is marked complete:
1. Requirements and public interfaces are documented.
2. Normal, boundary, invalid-input, and failure cases are identified.
3. Automated tests cover core business rules.
4. Database operations are tested for rollback and consistency where applicable.
5. Integration points with existing modules are checked.
6. Regression tests pass.
7. Manual checks are recorded when automation cannot cover a behavior.
8. Any unresolved defect or unverified behavior is explicitly documented.

The goal is zero known defects at release gates. Absolute absence of every possible defect cannot be honestly guaranteed; verification status must always reflect tests actually run.

## 7. Engineering workflow

1. Inspect the repository and current requirements before modifying code.
2. Work in small, reviewable changes that each have one clear purpose.
3. Make changes sequentially when they depend on the same files or state.
4. Run relevant tests after each change and the full suite at integration checkpoints.
5. Do not claim a test, manual check, compatibility check, or review occurred unless it actually occurred.
6. Preserve existing user data and unrelated repository content.
7. Record design decisions and limitations in documentation.
8. Keep README scope and implementation status synchronized.

## 8. Initial acceptance criteria

The project may proceed to implementation when:
- Desktop-first scope is explicit.
- The supported platform strategy is documented with compatibility caveats.
- The core data model and transaction invariants are designed before UI code depends on them.
- Tax behavior is defined before tax totals are wired into sales and reports.
- Tests can run locally without network access or paid services.

## 9. Status honesty

This document establishes requirements only. It does not mean any feature has been implemented, tested, packaged, or certified. Each implementation stage must report its actual state and evidence separately.
