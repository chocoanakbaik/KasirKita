"""Exact integer tax calculations for configured sales tax."""
from __future__ import annotations

from typing import Mapping


MAX_MONEY_RUPIAH = 9_000_000_000_000_000
MAX_RATE_BASIS_POINTS = 10_000


class TaxCalculationError(ValueError):
    """Raised when a tax calculation input is invalid or overflows limits."""


def calculate_tax(amount_rupiah: object, config: Mapping[str, object]) -> dict:
    """Calculate tax without floating-point arithmetic.

    For exclusive pricing, amount_rupiah is the pre-tax subtotal.
    For inclusive pricing, amount_rupiah is the customer-facing gross total and
    the tax is extracted from that amount. Half-up rounding is applied to rupiah.
    """
    if isinstance(amount_rupiah, bool) or not isinstance(amount_rupiah, int):
        raise TaxCalculationError("Nilai transaksi harus berupa bilangan bulat rupiah.")
    if amount_rupiah < 0 or amount_rupiah > MAX_MONEY_RUPIAH:
        raise TaxCalculationError("Nilai transaksi berada di luar batas yang didukung.")
    if not isinstance(config, Mapping):
        raise TaxCalculationError("Konfigurasi pajak tidak valid.")

    enabled = config.get("enabled")
    rate = config.get("rate_basis_points")
    mode = config.get("mode")
    if not isinstance(enabled, bool):
        raise TaxCalculationError("Status pajak tidak valid.")
    if isinstance(rate, bool) or not isinstance(rate, int):
        raise TaxCalculationError("Tarif pajak harus berupa bilangan bulat.")
    if rate < 0 or rate > MAX_RATE_BASIS_POINTS:
        raise TaxCalculationError("Tarif pajak harus antara 0% dan 100%.")
    if mode not in ("exclusive", "inclusive"):
        raise TaxCalculationError("Mode harga pajak tidak valid.")

    if not enabled or rate == 0:
        return {"subtotal_rupiah": amount_rupiah, "tax_rupiah": 0, "total_rupiah": amount_rupiah}

    if mode == "exclusive":
        tax = (amount_rupiah * rate + 5000) // 10000
        total = amount_rupiah + tax
        if total > MAX_MONEY_RUPIAH:
            raise TaxCalculationError("Total setelah pajak melebihi batas yang didukung.")
        return {
            "subtotal_rupiah": amount_rupiah,
            "tax_rupiah": tax,
            "total_rupiah": total,
        }

    tax = (amount_rupiah * rate + (10000 + rate) // 2) // (10000 + rate)
    return {
        "subtotal_rupiah": amount_rupiah - tax,
        "tax_rupiah": tax,
        "total_rupiah": amount_rupiah,
    }


__all__ = ["TaxCalculationError", "calculate_tax"]
