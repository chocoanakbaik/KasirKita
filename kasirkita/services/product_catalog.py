"""Validated product-catalogue use cases."""
from __future__ import annotations

from typing import List

from kasirkita.infrastructure.product_repository import (
    DuplicateSKUError,
    ProductNotFoundError,
    ProductRepository,
)


class ProductValidationError(ValueError):
    """Raised when product input violates catalogue rules."""


MAX_PRICE_RUPIAH = 9_000_000_000_000_000
MAX_STOCK_QUANTITY = 2_147_483_647
MAX_SKU_LENGTH = 64
MAX_PRODUCT_NAME_LENGTH = 160


def _require_text(value: object, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ProductValidationError(field_name + " harus berupa teks.")
    cleaned = value.strip()
    if not cleaned:
        raise ProductValidationError(field_name + " tidak boleh kosong.")
    if len(cleaned) > max_length:
        raise ProductValidationError(
            field_name + " maksimal " + str(max_length) + " karakter."
        )
    return cleaned


def _require_nonnegative_integer(value: object, field_name: str, maximum: int) -> int:
    # bool is a subclass of int in Python, so reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProductValidationError(field_name + " harus berupa bilangan bulat.")
    if value < 0:
        raise ProductValidationError(field_name + " tidak boleh negatif.")
    if value > maximum:
        raise ProductValidationError(field_name + " melebihi batas yang didukung.")
    return value


class ProductCatalog:
    """Application service for creating, searching, editing, and archiving products."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def create_product(
        self,
        sku: object,
        name: object,
        unit_price_rupiah: object,
        stock_quantity: object = 0,
    ) -> dict:
        normalized_sku = _require_text(sku, "SKU", MAX_SKU_LENGTH).upper()
        normalized_name = _require_text(name, "Nama produk", MAX_PRODUCT_NAME_LENGTH)
        price = _require_nonnegative_integer(
            unit_price_rupiah, "Harga", MAX_PRICE_RUPIAH
        )
        stock = _require_nonnegative_integer(
            stock_quantity, "Stok awal", MAX_STOCK_QUANTITY
        )
        return self._repository.create(normalized_sku, normalized_name, price, stock)

    def get_product(self, product_id: object) -> dict:
        valid_id = self._require_product_id(product_id)
        product = self._repository.get_by_id(valid_id)
        if product is None:
            raise ProductNotFoundError("Produk tidak ditemukan.")
        return product

    def list_products(
        self,
        search: object = "",
        include_inactive: bool = False,
    ) -> List[dict]:
        if not isinstance(search, str):
            raise ProductValidationError("Pencarian harus berupa teks.")
        if not isinstance(include_inactive, bool):
            raise ProductValidationError("Pilihan produk nonaktif tidak valid.")
        return self._repository.list_products(search, include_inactive)

    def update_product(
        self,
        product_id: object,
        sku: object,
        name: object,
        unit_price_rupiah: object,
    ) -> dict:
        valid_id = self._require_product_id(product_id)
        normalized_sku = _require_text(sku, "SKU", MAX_SKU_LENGTH).upper()
        normalized_name = _require_text(name, "Nama produk", MAX_PRODUCT_NAME_LENGTH)
        price = _require_nonnegative_integer(
            unit_price_rupiah, "Harga", MAX_PRICE_RUPIAH
        )
        return self._repository.update_details(
            valid_id, normalized_sku, normalized_name, price
        )

    def set_product_active(self, product_id: object, is_active: object) -> dict:
        valid_id = self._require_product_id(product_id)
        if not isinstance(is_active, bool):
            raise ProductValidationError("Status produk tidak valid.")
        return self._repository.set_active(valid_id, is_active)

    @staticmethod
    def _require_product_id(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ProductValidationError("ID produk tidak valid.")
        return value


__all__ = [
    "DuplicateSKUError",
    "ProductCatalog",
    "ProductNotFoundError",
    "ProductValidationError",
]
