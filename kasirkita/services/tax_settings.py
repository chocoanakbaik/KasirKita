"""Validated persistence for optional sales-tax configuration."""
from __future__ import annotations

import sqlite3

from kasirkita.infrastructure.database import transaction


DEFAULT_TAX_CONFIG = {
    "enabled": False,
    "rate_basis_points": 0,
    "mode": "exclusive",
    "label": "PPN",
}
MAX_RATE_BASIS_POINTS = 10_000


class TaxSettingsError(ValueError):
    """Raised when tax settings are invalid or cannot be read safely."""


class TaxSettingsService:
    """Store optional tax settings as local app configuration."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_config(self) -> dict:
        rows = self._connection.execute(
            """
            SELECT key, value FROM app_settings
            WHERE key IN ('tax.enabled', 'tax.rate_basis_points', 'tax.mode', 'tax.label')
            """
        ).fetchall()
        stored = {str(row["key"]): str(row["value"]) for row in rows}
        enabled_value = stored.get("tax.enabled", "0")
        if enabled_value not in ("0", "1"):
            raise TaxSettingsError("Status pajak tersimpan tidak valid.")
        try:
            rate = int(stored.get("tax.rate_basis_points", "0"))
        except ValueError as exc:
            raise TaxSettingsError("Tarif pajak tersimpan tidak valid.") from exc
        mode = stored.get("tax.mode", "exclusive")
        label = stored.get("tax.label", "PPN")
        config = {
            "enabled": enabled_value == "1",
            "rate_basis_points": rate,
            "mode": mode,
            "label": label,
        }
        self._validate(config["enabled"], rate, mode, label, allow_disabled_zero=True)
        return config

    def save_config(
        self,
        enabled: object,
        rate_basis_points: object,
        mode: object,
        label: object = "PPN",
    ) -> dict:
        self._validate(enabled, rate_basis_points, mode, label, allow_disabled_zero=True)
        values = {
            "tax.enabled": "1" if enabled else "0",
            "tax.rate_basis_points": str(rate_basis_points),
            "tax.mode": str(mode),
            "tax.label": str(label).strip(),
        }
        with transaction(self._connection):
            for key, value in values.items():
                self._connection.execute(
                    """
                    INSERT INTO app_settings (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    """,
                    (key, value),
                )
        return self.get_config()

    @staticmethod
    def _validate(
        enabled: object,
        rate_basis_points: object,
        mode: object,
        label: object,
        allow_disabled_zero: bool,
    ) -> None:
        if not isinstance(enabled, bool):
            raise TaxSettingsError("Status pajak harus aktif atau nonaktif.")
        if isinstance(rate_basis_points, bool) or not isinstance(rate_basis_points, int):
            raise TaxSettingsError("Tarif pajak harus berupa bilangan bulat basis poin.")
        if rate_basis_points < 0 or rate_basis_points > MAX_RATE_BASIS_POINTS:
            raise TaxSettingsError("Tarif pajak harus antara 0% dan 100%.")
        if enabled and rate_basis_points == 0 and not allow_disabled_zero:
            raise TaxSettingsError("Tarif pajak harus lebih besar dari nol.")
        if mode not in ("exclusive", "inclusive"):
            raise TaxSettingsError("Mode harga harus termasuk pajak atau belum termasuk pajak.")
        if not isinstance(label, str):
            raise TaxSettingsError("Label pajak harus berupa teks.")
        cleaned_label = label.strip()
        if not cleaned_label or len(cleaned_label) > 40:
            raise TaxSettingsError("Label pajak harus berisi 1 sampai 40 karakter.")
        if enabled and rate_basis_points == 0:
            raise TaxSettingsError("Isi tarif pajak di atas 0% sebelum mengaktifkan pajak.")


__all__ = ["DEFAULT_TAX_CONFIG", "TaxSettingsError", "TaxSettingsService"]
