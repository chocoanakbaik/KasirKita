"""Validated SQLite backup and restore operations."""
from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Optional

from kasirkita.infrastructure.database import DatabaseError, SCHEMA_VERSION


class BackupError(RuntimeError):
    """Raised when a backup or restore cannot be completed safely."""


_REQUIRED_COLUMNS = {
    "products": {"id", "sku", "name", "unit_price_rupiah", "stock_quantity", "is_active"},
    "sales": {"id", "receipt_number", "status", "subtotal_rupiah", "tax_rupiah", "total_rupiah", "tax_enabled", "tax_rate_basis_points", "tax_mode", "tax_label"},
    "sale_items": {"id", "sale_id", "product_id", "sku_snapshot", "product_name_snapshot", "quantity", "unit_price_rupiah", "line_total_rupiah"},
    "payments": {"id", "sale_id", "method", "amount_rupiah"},
    "stock_movements": {"id", "product_id", "sale_id", "movement_type", "quantity_delta"},
    "app_settings": {"key", "value"},
}
_REQUIRED_TABLES = set(_REQUIRED_COLUMNS)


def _open_existing_database(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise BackupError("File database tidak ditemukan.")
    try:
        connection = sqlite3.connect(str(path), timeout=5.0)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
    except sqlite3.Error as exc:
        raise BackupError("File database tidak dapat dibuka.") from exc


def _validate_connection(connection: sqlite3.Connection) -> None:
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise BackupError("Pemeriksaan integritas database gagal.")
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise BackupError("Database memiliki relasi foreign key yang tidak valid.")

        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version != SCHEMA_VERSION:
            raise BackupError(
                "Versi skema backup tidak didukung. "
                "Diperlukan versi " + str(SCHEMA_VERSION) + "."
            )
        names = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if not _REQUIRED_TABLES.issubset(names):
            raise BackupError("Backup tidak berisi semua tabel inti KasirKita.")
        for table_name, expected_columns in _REQUIRED_COLUMNS.items():
            actual_columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(" + table_name + ")"
                ).fetchall()
            }
            if not expected_columns.issubset(actual_columns):
                raise BackupError(
                    "Struktur tabel " + table_name + " tidak cocok dengan skema KasirKita."
                )
    except BackupError:
        raise
    except sqlite3.Error as exc:
        raise BackupError("Database tidak dapat divalidasi.") from exc


def _temporary_database_path(directory: Path, prefix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=prefix, suffix=".sqlite3", dir=str(directory))
    os.close(descriptor)
    return Path(name)


class DatabaseBackupService:
    """Create consistent backups and restore only validated KasirKita databases.

    The caller owns the live connection. Restore uses SQLite's backup API, so the
    existing connection object remains valid after a successful restore.
    """

    def __init__(
        self,
        live_connection: sqlite3.Connection,
        live_database_path: Optional[str] = None,
    ) -> None:
        self._live_connection = live_connection
        self._live_database_path = (
            Path(live_database_path).expanduser().resolve()
            if live_database_path is not None
            else None
        )

    def _reject_live_database_path(self, candidate: Path) -> None:
        if self._live_database_path is not None:
            try:
                if candidate.resolve() == self._live_database_path:
                    raise BackupError(
                        "File database aktif tidak boleh digunakan sebagai file backup."
                    )
            except OSError as exc:
                raise BackupError("Lokasi file tidak dapat diverifikasi.") from exc

    def create_backup(self, destination: str) -> Path:
        target = Path(destination).expanduser()
        if not target.name:
            raise BackupError("Lokasi backup tidak valid.")
        self._reject_live_database_path(target)
        if self._live_connection.in_transaction:
            raise BackupError("Backup tidak dapat dibuat saat transaksi database aktif.")

        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = _temporary_database_path(target.parent, ".kasirkita-backup-")
        try:
            with closing(sqlite3.connect(str(temporary), timeout=5.0)) as backup_connection:
                self._live_connection.backup(backup_connection)
                _validate_connection(backup_connection)
            os.replace(str(temporary), str(target))
            return target
        except BackupError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise BackupError("Backup gagal dibuat; file tujuan tidak diganti.") from exc
        finally:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                # Cleanup failure does not invalidate a successfully replaced backup.
                pass

    def restore_backup(self, source: str) -> None:
        source_path = Path(source).expanduser()
        if not source_path.is_file():
            raise BackupError("File backup tidak ditemukan.")
        self._reject_live_database_path(source_path)
        if self._live_connection.in_transaction:
            raise BackupError("Restore tidak dapat dilakukan saat transaksi database aktif.")

        temporary = _temporary_database_path(Path(tempfile.gettempdir()), ".kasirkita-safety-")
        try:
            with closing(_open_existing_database(source_path)) as source_connection:
                _validate_connection(source_connection)
                with closing(sqlite3.connect(str(temporary), timeout=5.0)) as safety_connection:
                    self._live_connection.backup(safety_connection)
                    _validate_connection(safety_connection)

                try:
                    source_connection.backup(self._live_connection)
                    _validate_connection(self._live_connection)
                except Exception as restore_error:
                    # Best-effort rollback at database-image level if post-restore
                    # validation fails. The safety image was validated beforehand.
                    try:
                        with closing(sqlite3.connect(str(temporary), timeout=5.0)) as safety_connection:
                            safety_connection.backup(self._live_connection)
                    except Exception as recovery_error:
                        raise BackupError(
                            "Restore gagal dan pemulihan otomatis juga gagal. "
                            "Jangan tutup aplikasi; segera salin file database yang ada."
                        ) from recovery_error
                    raise BackupError(
                        "Restore gagal. Database sebelumnya telah dipulihkan."
                    ) from restore_error
        except BackupError:
            raise
        except (OSError, sqlite3.Error, DatabaseError) as exc:
            raise BackupError("Restore tidak dapat diselesaikan dengan aman.") from exc
        finally:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass


__all__ = ["BackupError", "DatabaseBackupService"]
