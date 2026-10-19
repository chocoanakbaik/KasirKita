"""Local first-run onboarding state for offline KasirKita installations."""
from __future__ import annotations

import sqlite3

from kasirkita.infrastructure.database import transaction

ONBOARDING_KEY = "onboarding.v1.status"


class OnboardingService:
    """Persist onboarding state in the same local SQLite database as business data."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def has_seen_tutorial(self) -> bool:
        row = self._connection.execute(
            "SELECT value FROM app_settings WHERE key = ?", (ONBOARDING_KEY,)
        ).fetchone()
        return row is not None and row["value"] in ("completed", "skipped")

    def mark_completed(self) -> None:
        self._save_status("completed")

    def mark_skipped(self) -> None:
        self._save_status("skipped")

    def reset(self) -> None:
        with transaction(self._connection):
            self._connection.execute(
                "DELETE FROM app_settings WHERE key = ?", (ONBOARDING_KEY,)
            )

    def _save_status(self, status: str) -> None:
        if status not in ("completed", "skipped"):
            raise ValueError("Status tutorial tidak valid.")
        with transaction(self._connection):
            self._connection.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (ONBOARDING_KEY, status),
            )
