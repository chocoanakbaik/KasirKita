"""Tests for customer and supplier record management."""
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.contacts import ContactService, ContactValidationError


class ContactServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.service = ContactService(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_customer_create_search_update_and_deactivate(self):
        customer = self.service.add_customer("  Budi   Santoso ", "0812345678", "budi@example.com")
        self.assertEqual(customer["name"], "Budi Santoso")
        self.assertEqual(len(self.service.list_customers("Budi")), 1)
        updated = self.service.update_customer(customer["id"], "Budi S.", "0812345678")
        self.assertEqual(updated["name"], "Budi S.")
        self.service.set_customer_active(customer["id"], False)
        self.assertEqual(self.service.list_customers(), [])
        self.assertEqual(len(self.service.list_customers(include_inactive=True)), 1)

    def test_supplier_create_and_independent_records(self):
        supplier = self.service.add_supplier("Grosir Makmur", phone="081234567")
        self.assertEqual(supplier["name"], "Grosir Makmur")
        self.assertEqual(self.service.list_suppliers()[0]["id"], supplier["id"])
        self.assertEqual(self.service.list_customers(), [])

    def test_invalid_email_and_blank_name_are_rejected(self):
        with self.assertRaises(ContactValidationError):
            self.service.add_customer("Budi", email="bukan-email")
        with self.assertRaises(ContactValidationError):
            self.service.add_supplier("   ")

    def test_search_treats_like_wildcards_as_literal(self):
        self.service.add_customer("A% Store")
        self.service.add_customer("ABC Store")
        self.assertEqual(len(self.service.list_customers("%")), 1)


if __name__ == "__main__":
    unittest.main()
