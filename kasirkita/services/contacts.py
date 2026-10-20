"""Local customer and supplier records for offline store operations."""
from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional

from kasirkita.infrastructure.database import transaction


class ContactValidationError(ValueError):
    """Raised when customer or supplier data is invalid."""


class ContactService:
    """Manage customers and suppliers with validation and soft deletion."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_customers(self, query: str = "", include_inactive: bool = False) -> List[dict]:
        return self._list("customers", query, include_inactive)

    def list_suppliers(self, query: str = "", include_inactive: bool = False) -> List[dict]:
        return self._list("suppliers", query, include_inactive)

    def add_customer(self, name: object, phone: object = "", email: object = "",
                     address: object = "", note: object = "") -> Dict[str, object]:
        return self._add("customers", name, phone, email, address, note)

    def add_supplier(self, name: object, phone: object = "", email: object = "",
                     address: object = "", note: object = "") -> Dict[str, object]:
        return self._add("suppliers", name, phone, email, address, note)

    def update_customer(self, record_id: object, name: object, phone: object = "",
                        email: object = "", address: object = "", note: object = "") -> Dict[str, object]:
        return self._update("customers", record_id, name, phone, email, address, note)

    def update_supplier(self, record_id: object, name: object, phone: object = "",
                        email: object = "", address: object = "", note: object = "") -> Dict[str, object]:
        return self._update("suppliers", record_id, name, phone, email, address, note)

    def set_customer_active(self, record_id: object, active: object) -> None:
        self._set_active("customers", record_id, active)

    def set_supplier_active(self, record_id: object, active: object) -> None:
        self._set_active("suppliers", record_id, active)

    def _list(self, table: str, query: str, include_inactive: bool) -> List[dict]:
        cleaned = self._text(query, "Pencarian", 100, allow_empty=True)
        where = "WHERE is_active = 1" if not include_inactive else "WHERE 1 = 1"
        pattern = "%" + cleaned.replace("%", "\\%").replace("_", "\\_") + "%"
        rows = self._connection.execute(
            "SELECT id, name, phone, email, address, note, is_active, created_at, updated_at "
            "FROM " + table + " " + where +
            " AND (name LIKE ? ESCAPE '\\' OR phone LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\') "
            "ORDER BY name COLLATE NOCASE",
            (pattern, pattern, pattern),
        ).fetchall()
        return [dict(row) for row in rows]

    def _add(self, table: str, name: object, phone: object, email: object,
             address: object, note: object) -> Dict[str, object]:
        values = self._validate(name, phone, email, address, note)
        with transaction(self._connection):
            cursor = self._connection.execute(
                "INSERT INTO " + table + " (name, phone, email, address, note) VALUES (?, ?, ?, ?, ?)",
                values,
            )
        row = self._connection.execute("SELECT * FROM " + table + " WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def _update(self, table: str, record_id: object, name: object, phone: object,
                email: object, address: object, note: object) -> Dict[str, object]:
        valid_id = self._id(record_id)
        values = self._validate(name, phone, email, address, note)
        with transaction(self._connection):
            cursor = self._connection.execute(
                "UPDATE " + table + " SET name = ?, phone = ?, email = ?, address = ?, note = ?, "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                values + (valid_id,),
            )
            if cursor.rowcount != 1:
                raise ContactValidationError("Data tidak ditemukan.")
        row = self._connection.execute("SELECT * FROM " + table + " WHERE id = ?", (valid_id,)).fetchone()
        return dict(row)

    def _set_active(self, table: str, record_id: object, active: object) -> None:
        valid_id = self._id(record_id)
        if not isinstance(active, bool):
            raise ContactValidationError("Status data tidak valid.")
        with transaction(self._connection):
            cursor = self._connection.execute(
                "UPDATE " + table + " SET is_active = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                "WHERE id = ?",
                (1 if active else 0, valid_id),
            )
            if cursor.rowcount != 1:
                raise ContactValidationError("Data tidak ditemukan.")

    @staticmethod
    def _id(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ContactValidationError("ID data tidak valid.")
        return value

    @staticmethod
    def _text(value: object, label: str, max_length: int, allow_empty: bool = False) -> str:
        if not isinstance(value, str):
            raise ContactValidationError(label + " harus berupa teks.")
        cleaned = " ".join(value.strip().split())
        if not cleaned and not allow_empty:
            raise ContactValidationError(label + " wajib diisi.")
        if len(cleaned) > max_length:
            raise ContactValidationError(label + " maksimal " + str(max_length) + " karakter.")
        return cleaned

    @classmethod
    def _validate(cls, name: object, phone: object, email: object,
                  address: object, note: object):
        values = (
            cls._text(name, "Nama", 120),
            cls._text(phone, "Nomor telepon", 40, True),
            cls._text(email, "Email", 120, True),
            cls._text(address, "Alamat", 300, True),
            cls._text(note, "Catatan", 500, True),
        )
        if values[2] and ("@" not in values[2] or values[2].startswith("@") or values[2].endswith("@")):
            raise ContactValidationError("Format email tidak valid.")
        return values


__all__ = ["ContactService", "ContactValidationError"]
