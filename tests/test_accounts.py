"""Tests for offline account registration, role separation, and recovery."""
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.accounts import AccountService, AuthenticationError


OWNER_NIK = "3201010101010001"
EMPLOYEE_NIK = "3201010101010002"
PASSWORD = "kataSandiAman123"


class AccountServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.service = AccountService(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_first_owner_registration_and_role_specific_login(self):
        owner = self.service.register_first_owner("Pemilik Toko", OWNER_NIK, PASSWORD)
        self.assertEqual(owner["role"], "owner")
        self.assertEqual(len(owner["recovery_code"].replace("-", "")), 20)
        self.assertEqual(self.service.authenticate(OWNER_NIK, PASSWORD, "owner")["id"], owner["id"])
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(OWNER_NIK, PASSWORD, "employee")

    def test_owner_registration_is_closed_after_first_owner(self):
        self.service.register_first_owner("Pemilik", OWNER_NIK, PASSWORD)
        with self.assertRaises(AuthenticationError):
            self.service.register_first_owner("Penyusup", EMPLOYEE_NIK, PASSWORD)

    def test_duplicate_nik_is_rejected_even_with_per_user_salts(self):
        self.service.register_first_owner("Pemilik", OWNER_NIK, PASSWORD)
        owner = self.service.authenticate(OWNER_NIK, PASSWORD, "owner")
        with self.assertRaises(AuthenticationError):
            self.service.create_employee(owner, "Pegawai", OWNER_NIK, PASSWORD)

    def test_employee_can_only_be_created_by_owner_and_is_role_separated(self):
        owner = self.service.register_first_owner("Pemilik", OWNER_NIK, PASSWORD)
        employee = self.service.create_employee(owner, "Kasir", EMPLOYEE_NIK, PASSWORD)
        self.assertEqual(employee["role"], "employee")
        self.assertEqual(self.service.authenticate(EMPLOYEE_NIK, PASSWORD, "employee")["id"], employee["id"])
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(EMPLOYEE_NIK, PASSWORD, "owner")
        with self.assertRaises(AuthenticationError):
            self.service.create_employee(employee, "Kasir Lain", "3201010101010003", PASSWORD)

    def test_wrong_password_and_disabled_employee_are_rejected(self):
        owner = self.service.register_first_owner("Pemilik", OWNER_NIK, PASSWORD)
        employee = self.service.create_employee(owner, "Kasir", EMPLOYEE_NIK, PASSWORD)
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(EMPLOYEE_NIK, "salah-password", "employee")
        self.service.set_employee_active(owner, employee["id"], False)
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(EMPLOYEE_NIK, PASSWORD, "employee")

    def test_owner_recovery_requires_nik_and_one_time_recovery_code(self):
        registered = self.service.register_first_owner("Pemilik", OWNER_NIK, PASSWORD)
        self.service.recover_owner_password(OWNER_NIK, registered["recovery_code"], "kataSandiBaru123")
        self.assertEqual(self.service.authenticate(OWNER_NIK, "kataSandiBaru123", "owner")["id"], registered["id"])
        with self.assertRaises(AuthenticationError):
            self.service.recover_owner_password(OWNER_NIK, registered["recovery_code"], PASSWORD)

    def test_password_policy_and_nik_format_are_enforced(self):
        with self.assertRaises(AuthenticationError):
            self.service.register_first_owner("Pemilik", "123", PASSWORD)
        with self.assertRaises(AuthenticationError):
            self.service.register_first_owner("Pemilik", OWNER_NIK, "pendek")


if __name__ == "__main__":
    unittest.main()
