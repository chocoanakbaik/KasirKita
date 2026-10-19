# KasirKita Desktop — Release Gate Checklist

**Current release status: NOT READY FOR SALE.** Checkboxes must only be marked after the action has actually been completed and evidence has been recorded.

## Automated verification

- [ ] Latest main-branch workflow passes on Windows and Ubuntu for all configured Python versions.
- [ ] Database migration tests cover fresh databases, supported upgrades, and rollback after migration failure.
- [ ] Checkout tests cover normal sales, duplicate cart items, insufficient payment, insufficient stock, inactive products, tax modes, and atomic rollback.
- [ ] Stock adjustment tests cover increases, decreases, invalid reasons, and prevention of negative stock.
- [ ] Backup/restore tests cover valid files, invalid files, recovery behavior, and Windows file-handle cleanup.
- [ ] UI smoke test passes on Windows.
- [ ] First-run tutorial appears on a fresh local profile, persists completion/skip state, does not repeat on next launch, and can be reopened from the help control.
- [ ] Tutorial and its persisted state behave correctly after backup/restore and application upgrade.
- [ ] No known failing tests or unresolved high-severity defects remain.

## Manual desktop verification

- [ ] Launch on a clean Windows installation with no development tools installed.
- [ ] Launch on Windows 8.1 x64 on real hardware before claiming support for that OS.
- [ ] Launch on each other Windows version advertised as supported.
- [ ] Confirm the app creates data only in the intended user data directory.
- [ ] Confirm the first-run tutorial appears once, can be skipped, and is available later from Panduan / Tutorial.
- [ ] Confirm no internet connection is required for onboarding or core cashier workflows.
- [ ] Confirm a user without write access to the data directory receives a clear error.
- [ ] Add, edit, search, disable, and re-enable products.
- [ ] Adjust stock and verify the audit trail.
- [ ] Complete a cash sale and verify stock, payment, receipt, and report totals.
- [ ] Test keyboard-emulated scanner input and manually typed SKU; unknown codes must not alter the cart.
- [ ] Verify XLSX summary/daily sheets and PDF report readability, file extensions, and content.
- [ ] Try insufficient cash and insufficient stock; verify no partial sale is saved.
- [ ] Verify disabled-tax, exclusive-tax, and inclusive-tax cases against independently calculated examples.
- [ ] Change tax settings and verify old receipt snapshots do not change.
- [ ] Create a backup, restore it, and verify products, sales, stock, and settings.
- [ ] Try a malformed backup and verify the active database remains intact.
- [ ] Verify reports around local midnight and across a date boundary.
- [ ] Verify keyboard navigation, readable labels, window resizing, and high-DPI behavior.
- [ ] Verify error messages do not expose tracebacks or sensitive details.

## Packaging and delivery

- [ ] Choose and document the supported Python/runtime packaging strategy.
- [ ] Build a clean installer or portable package with no undeclared dependencies.
- [ ] Verify application icon, product name, version, and uninstall behavior.
- [ ] Verify an upgrade does not overwrite user data.
- [ ] Verify uninstall behavior is explicit about whether user data is retained.
- [ ] Record checksums and version metadata for release artifacts.
- [ ] Prepare a backup warning and recovery instructions for users.
- [ ] Review the license, sales terms, support expectations, and privacy notice.
- [ ] Review Indonesian tax wording and remove any unsupported compliance claims.
- [ ] Publish only after every mandatory item has evidence and approval.

## Evidence log

For each release candidate, record the commit SHA, workflow run URL, operating system, Python/runtime version, test date, tester, results, and unresolved limitations. A green CI run alone does not establish compatibility with every Windows version or prove that manual workflows are correct.
