"""Offline account management with role-separated authentication."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from typing import Dict, Optional

from kasirkita.infrastructure.database import transaction

PBKDF2_ITERATIONS = 180_000
LOGIN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{3,31}$")
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class AuthenticationError(ValueError):
    """Raised when account creation, authentication, or recovery is rejected."""


def _normalise_login_id(value: object) -> str:
    if not isinstance(value, str):
        raise AuthenticationError("ID login harus 4–32 karakter: huruf, angka, titik, garis bawah, atau tanda hubung.")
    login_id = value.strip().lower()
    if not LOGIN_ID_PATTERN.fullmatch(login_id):
        raise AuthenticationError("ID login harus 4–32 karakter: huruf/angka di awal, lalu boleh memakai titik, garis bawah, atau tanda hubung.")
    return login_id


def _normalise_name(value: object) -> str:
    if not isinstance(value, str):
        raise AuthenticationError("Nama wajib diisi.")
    name = " ".join(value.strip().split())
    if not name or len(name) > 100:
        raise AuthenticationError("Nama wajib diisi dan maksimal 100 karakter.")
    return name


def _normalise_password(value: object) -> str:
    if not isinstance(value, str) or len(value) < 10 or len(value) > 256:
        raise AuthenticationError("Kata sandi harus terdiri dari 10 sampai 256 karakter.")
    if not value.strip():
        raise AuthenticationError("Kata sandi tidak boleh kosong.")
    return value


def _derive(value: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt, PBKDF2_ITERATIONS)


def _new_recovery_code() -> str:
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(20))
    return "-".join(raw[index:index + 5] for index in range(0, 20, 5))


def _credential_hash(value: str, salt: bytes) -> str:
    return _derive(value, salt).hex()


def _login_id_hash(value: str, salt: bytes) -> str:
    return hashlib.sha256(salt + value.encode("utf-8")).hexdigest()


class AccountService:
    """Authenticate owners/employees and enforce account-management roles."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._failed_attempts: Dict[str, int] = {}

    def owner_exists(self) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM users WHERE role = 'owner' AND is_active = 1 LIMIT 1"
        ).fetchone()
        return row is not None

    def register_first_owner(self, name: object, login_id: object, password: object) -> Dict[str, object]:
        cleaned_name = _normalise_name(name)
        cleaned_login_id = _normalise_login_id(login_id)
        cleaned_password = _normalise_password(password)
        salt = secrets.token_bytes(16)
        login_id_salt = secrets.token_bytes(16)
        recovery_code = _new_recovery_code()
        recovery_salt = secrets.token_bytes(16)
        with transaction(self._connection):
            owner = self._connection.execute(
                "SELECT 1 FROM users WHERE role = 'owner' LIMIT 1"
            ).fetchone()
            if owner:
                raise AuthenticationError("Akun pemilik sudah ada. Pendaftaran awal ditutup.")
            duplicate = self._connection.execute(
                "SELECT 1 FROM users WHERE login_id_hash = ? LIMIT 1",
                (_login_id_hash(cleaned_login_id, login_id_salt),),
            ).fetchone()
            # Hashes use per-record salts, so uniqueness is checked using the supplied
            # ID login against existing salts rather than comparing differently salted hashes.
            if duplicate or self._login_id_exists(cleaned_login_id):
                raise AuthenticationError("ID login sudah digunakan.")
            cursor = self._connection.execute(
                """
                INSERT INTO users
                    (display_name, role, login_id_hash, login_id_salt, password_hash, password_salt,
                     password_iterations, recovery_hash, recovery_salt)
                VALUES (?, 'owner', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cleaned_name, _login_id_hash(cleaned_login_id, login_id_salt), login_id_salt.hex(),
                    _credential_hash(cleaned_password, salt), salt.hex(), PBKDF2_ITERATIONS,
                    _credential_hash(recovery_code.replace("-", ""), recovery_salt), recovery_salt.hex(),
                ),
            )
        return {
            "id": int(cursor.lastrowid),
            "display_name": cleaned_name,
            "role": "owner",
            "recovery_code": recovery_code,
        }

    def authenticate(self, login_id: object, password: object, expected_role: str) -> Dict[str, object]:
        cleaned_login_id = _normalise_login_id(login_id)
        if expected_role not in ("owner", "employee"):
            raise AuthenticationError("Jalur login tidak valid.")
        if not isinstance(password, str) or len(password) > 256:
            raise AuthenticationError("ID login atau kata sandi salah.")
        key = expected_role + ":" + cleaned_login_id
        if self._failed_attempts.get(key, 0) >= 5:
            raise AuthenticationError("Terlalu banyak percobaan. Tutup lalu buka kembali aplikasi untuk mencoba lagi.")
        rows = self._connection.execute(
            "SELECT id, display_name, role, login_id_hash, login_id_salt, password_hash, password_salt, password_iterations, is_active "
            "FROM users WHERE role = ? AND is_active = 1",
            (expected_role,),
        ).fetchall()
        match: Optional[sqlite3.Row] = None
        for row in rows:
            candidate = _login_id_hash(cleaned_login_id, bytes.fromhex(row["login_id_salt"]))
            if hmac.compare_digest(candidate, row["login_id_hash"]):
                match = row
                break
        valid = False
        if match is not None:
            candidate_password = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"),
                bytes.fromhex(match["password_salt"]),
                int(match["password_iterations"]),
            ).hex()
            valid = hmac.compare_digest(candidate_password, match["password_hash"])
        if not valid:
            self._failed_attempts[key] = self._failed_attempts.get(key, 0) + 1
            raise AuthenticationError("ID login atau kata sandi salah untuk jalur login ini.")
        self._failed_attempts.pop(key, None)
        return {
            "id": int(match["id"]),
            "display_name": str(match["display_name"]),
            "role": str(match["role"]),
        }

    def create_employee(self, actor: Dict[str, object], name: object, login_id: object,
                        password: object) -> Dict[str, object]:
        self._require_owner(actor)
        cleaned_name = _normalise_name(name)
        cleaned_login_id = _normalise_login_id(login_id)
        cleaned_password = _normalise_password(password)
        if self._login_id_exists(cleaned_login_id):
            raise AuthenticationError("ID login sudah digunakan.")
        password_salt = secrets.token_bytes(16)
        login_id_salt = secrets.token_bytes(16)
        with transaction(self._connection):
            if self._login_id_exists(cleaned_login_id):
                raise AuthenticationError("ID login sudah digunakan.")
            cursor = self._connection.execute(
                """
                INSERT INTO users
                    (display_name, role, login_id_hash, login_id_salt, password_hash, password_salt,
                     password_iterations)
                VALUES (?, 'employee', ?, ?, ?, ?, ?)
                """,
                (
                    cleaned_name, _login_id_hash(cleaned_login_id, login_id_salt), login_id_salt.hex(),
                    _credential_hash(cleaned_password, password_salt), password_salt.hex(),
                    PBKDF2_ITERATIONS,
                ),
            )
        return {"id": int(cursor.lastrowid), "display_name": cleaned_name, "role": "employee"}

    def list_employees(self, actor: Dict[str, object]):
        self._require_owner(actor)
        rows = self._connection.execute(
            "SELECT id, display_name, role, is_active, created_at FROM users "
            "WHERE role = 'employee' ORDER BY display_name COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]

    def set_employee_active(self, actor: Dict[str, object], employee_id: object,
                            active: object) -> None:
        self._require_owner(actor)
        if isinstance(employee_id, bool) or not isinstance(employee_id, int) or employee_id <= 0:
            raise AuthenticationError("Akun pegawai tidak valid.")
        if not isinstance(active, bool):
            raise AuthenticationError("Status akun tidak valid.")
        with transaction(self._connection):
            cursor = self._connection.execute(
                "UPDATE users SET is_active = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                "WHERE id = ? AND role = 'employee'",
                (1 if active else 0, employee_id),
            )
            if cursor.rowcount != 1:
                raise AuthenticationError("Akun pegawai tidak ditemukan.")

    def reset_employee_password(self, actor: Dict[str, object], employee_id: object,
                                new_password: object) -> None:
        self._require_owner(actor)
        password = _normalise_password(new_password)
        if isinstance(employee_id, bool) or not isinstance(employee_id, int) or employee_id <= 0:
            raise AuthenticationError("Akun pegawai tidak valid.")
        salt = secrets.token_bytes(16)
        with transaction(self._connection):
            cursor = self._connection.execute(
                "UPDATE users SET password_hash = ?, password_salt = ?, password_iterations = ?, "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                "WHERE id = ? AND role = 'employee'",
                (_credential_hash(password, salt), salt.hex(), PBKDF2_ITERATIONS, employee_id),
            )
            if cursor.rowcount != 1:
                raise AuthenticationError("Akun pegawai tidak ditemukan.")

    def recover_owner_password(self, login_id: object, recovery_code: object,
                               new_password: object) -> bool:
        cleaned_login_id = _normalise_login_id(login_id)
        password = _normalise_password(new_password)
        if not isinstance(recovery_code, str):
            raise AuthenticationError("Kode pemulihan tidak valid.")
        normalized_code = recovery_code.replace("-", "").replace(" ", "").upper()
        if len(normalized_code) != 20 or any(c not in RECOVERY_ALPHABET for c in normalized_code):
            raise AuthenticationError("ID login atau kode pemulihan salah.")
        row = self._connection.execute(
            "SELECT id, login_id_hash, login_id_salt, recovery_hash, recovery_salt "
            "FROM users WHERE role = 'owner' AND is_active = 1"
        ).fetchone()
        if row is None:
            raise AuthenticationError("Akun pemilik tidak ditemukan.")
        valid_login_id = hmac.compare_digest(
            _login_id_hash(cleaned_login_id, bytes.fromhex(row["login_id_salt"])), row["login_id_hash"]
        )
        valid_code = bool(row["recovery_hash"]) and hmac.compare_digest(
            _credential_hash(normalized_code, bytes.fromhex(row["recovery_salt"])),
            row["recovery_hash"],
        )
        if not (valid_login_id and valid_code):
            raise AuthenticationError("ID login atau kode pemulihan salah.")
        salt = secrets.token_bytes(16)
        with transaction(self._connection):
            self._connection.execute(
                "UPDATE users SET password_hash = ?, password_salt = ?, password_iterations = ?, "
                "recovery_hash = NULL, recovery_salt = NULL, "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (_credential_hash(password, salt), salt.hex(), PBKDF2_ITERATIONS, int(row["id"])),
            )
        return True

    def _login_id_exists(self, login_id: str) -> bool:
        rows = self._connection.execute("SELECT login_id_hash, login_id_salt FROM users").fetchall()
        for row in rows:
            if hmac.compare_digest(
                _login_id_hash(login_id, bytes.fromhex(row["login_id_salt"])), row["login_id_hash"]
            ):
                return True
        return False

    @staticmethod
    def _require_owner(actor: Dict[str, object]) -> None:
        if not isinstance(actor, dict) or actor.get("role") != "owner":
            raise AuthenticationError("Fitur ini hanya dapat digunakan oleh pemilik.")


__all__ = ["AccountService", "AuthenticationError", "PBKDF2_ITERATIONS"]
