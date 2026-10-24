# KasirKita Authentication and Account Management Specification

Status: implementation requirements for the offline desktop application.

## User interface

- Start with a plain, familiar login screen. Avoid decorative cards, oversized gradients, or a promotional landing page.
- Provide two distinct entry points: "Login sebagai Pemilik" and "Login sebagai Pegawai".
- Each entry point uses its own role-specific authentication and authorization checks. Hiding UI controls is not an authorization boundary.
- Show "Daftar" when no account exists. The first registration creates the owner account; subsequent employee accounts are created by an authorized owner.
- The login screen includes "Lupa kata sandi?" and clear validation errors that do not reveal whether an account exists.

## Account identifiers and credentials

- A user account has a unique username/identifier and role. The owner can create employee accounts.
- Use a locally chosen login ID rather than a national identity number. Accept 4–32 characters, starting with an ASCII letter or digit and continuing with letters, digits, dot, underscore, or hyphen; normalize to lowercase. Explain this is a local account name, not an identity-verification method.
- Store password verifiers using a modern salted password-hashing function (PBKDF2-HMAC-SHA-256 from the Python standard library, with a suitably high iteration count) and constant-time verification. Never store plaintext passwords or reversible password ciphertext.
- Do not request NIK or other government identity numbers for local POS authentication. Password recovery requires the login ID and a one-time recovery code; the code is invalidated after use. Rate-limit attempts and avoid account-enumeration messages.
- Keep all account management local in the first release. Do not make login or recovery depend on Choco AI, Supabase, or an internet connection.

## Password recovery and recovery files

- The app must not generate a text file containing the user's existing password, even in encrypted form. A program that can automatically decrypt a saved password on the same machine creates a second credential store and increases the impact of device compromise.
- Recovery should reset the password after the identity checks succeed; it should never reveal the old password.
- If an offline recovery file is implemented, it must contain a one-time recovery token or encrypted recovery material, never a password. It must be protected by a separate user-held secret, have a clear expiry/rotation policy where feasible, and be invalidated after use.
- Do not imply that scrambled-looking text is secure encryption. Use a vetted cryptographic construction and never hard-code the decryption key in the app.

## Local data and permissions

- Store account records in the existing SQLite database and migrate schema transactionally without deleting existing products, sales, or settings.
- Separate owner and employee permissions in service-layer checks. Employees should not be able to create owners, manage accounts, restore backups, or change sensitive store settings unless the owner explicitly grants that capability.
- Customer and supplier records are local SQLite data with create, read, update, search, and safe archive/deactivation behavior.
- The first release remains single-computer and offline. Cloud sync, multi-branch support, and online payment integrations are out of scope.

## Required verification before release

- Unit tests for registration, duplicate identifiers, password hashing and verification, role separation, invalid login, rate limiting, password reset, and one-time recovery invalidation.
- Migration tests proving pre-existing sales, products, and settings survive the schema upgrade.
- Integration tests for customer and supplier CRUD and for the interactions among discounts, returns, stock movements, expenses, and reports.
- Windows build verification, clean install/startup checks, backup-and-restore tests, and manual UI smoke tests before calling the app release-ready.
