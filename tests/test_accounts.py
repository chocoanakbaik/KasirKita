"""Tests for local account IDs, role separation, recovery, and schema migration."""
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.accounts import AccountService, AuthenticationError


OWNER_LOGIN_ID = "owner.main"
EMPLOYEE_LOGIN_ID = "kasir-01"
PASSWORD = "kataSandiAman123"


class AccountServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.service = AccountService(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_first_owner_registration_and_role_specific_login(self):
        owner = self.service.register_first_owner("Pemilik Toko", OWNER_LOGIN_ID, PASSWORD)
        self.assertEqual(owner["role"], "owner")
        self.assertEqual(len(owner["recovery_code"].replace("-", "")), 20)
        self.assertEqual(
            self.service.authenticate(OWNER_LOGIN_ID, PASSWORD, "owner")["id"],
            owner["id"],
        )
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(OWNER_LOGIN_ID, PASSWORD, "employee")

    def test_login_id_is_normalized_case_insensitively(self):
        owner = self.service.register_first_owner("Pemilik", "Owner.Main", PASSWORD)
        self.assertEqual(
            self.service.authenticate("owner.main", PASSWORD, "owner")["id"],
            owner["id"],
        )
        with self.assertRaises(AuthenticationError):
            self.service.create_employee(owner, "Pegawai", "OWNER.MAIN", PASSWORD)

    def test_owner_registration_is_closed_after_first_owner(self):
        self.service.register_first_owner("Pemilik", OWNER_LOGIN_ID, PASSWORD)
        with self.assertRaises(AuthenticationError):
            self.service.register_first_owner("Penyusup", EMPLOYEE_LOGIN_ID, PASSWORD)

    def test_duplicate_login_id_is_rejected_with_per_user_salts(self):
        self.service.register_first_owner("Pemilik", OWNER_LOGIN_ID, PASSWORD)
        owner = self.service.authenticate(OWNER_LOGIN_ID, PASSWORD, "owner")
        with self.assertRaises(AuthenticationError):
            self.service.create_employee(owner, "Pegawai", OWNER_LOGIN_ID, PASSWORD)

    def test_employee_can_only_be_created_by_owner_and_is_role_separated(self):
        owner = self.service.register_first_owner("Pemilik", OWNER_LOGIN_ID, PASSWORD)
        employee = self.service.create_employee(owner, "Kasir", EMPLOYEE_LOGIN_ID, PASSWORD)
        self.assertEqual(employee["role"], "employee")
        self.assertEqual(
            self.service.authenticate(EMPLOYEE_LOGIN_ID, PASSWORD, "employee")["id"],
            employee["id"],
        )
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(EMPLOYEE_LOGIN_ID, PASSWORD, "owner")
        with self.assertRaises(AuthenticationError):
            self.service.create_employee(employee, "Kasir Lain", "kasir-02", PASSWORD)

    def test_wrong_password_and_disabled_employee_are_rejected(self):
        owner = self.service.register_first_owner("Pemilik", OWNER_LOGIN_ID, PASSWORD)
        employee = self.service.create_employee(owner, "Kasir", EMPLOYEE_LOGIN_ID, PASSWORD)
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(EMPLOYEE_LOGIN_ID, "salah-password", "employee")
        self.service.set_employee_active(owner, employee["id"], False)
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(EMPLOYEE_LOGIN_ID, PASSWORD, "employee")

    def test_owner_recovery_requires_login_id_and_one_time_recovery_code(self):
        registered = self.service.register_first_owner("Pemilik", OWNER_LOGIN_ID, PASSWORD)
        self.service.recover_owner_password(
            OWNER_LOGIN_ID, registered["recovery_code"], "kataSandiBaru123"
        )
        self.assertEqual(
            self.service.authenticate(OWNER_LOGIN_ID, "kataSandiBaru123", "owner")["id"],
            registered["id"],
        )
        with self.assertRaises(AuthenticationError):
            self.service.recover_owner_password(
                OWNER_LOGIN_ID, registered["recovery_code"], PASSWORD
            )

    def test_login_id_format_and_password_policy_are_enforced(self):
        for invalid_login_id in ("abc", "with space", "-starts-wrong", "too-long-" + "x" * 30):
            with self.subTest(login_id=invalid_login_id):
                with self.assertRaises(AuthenticationError):
                    self.service.register_first_owner("Pemilik", invalid_login_id, PASSWORD)
        with self.assertRaises(AuthenticationError):
            self.service.register_first_owner("Pemilik", OWNER_LOGIN_ID, "pendek")

    def test_version_4_account_migrates_without_losing_login_access(self):
        owner = self.service.register_first_owner("Pemilik", OWNER_LOGIN_ID, PASSWORD)
        before = self.service.authenticate(OWNER_LOGIN_ID, PASSWORD, "owner")
        self.assertEqual(before["id"], owner["id"])

        self.connection.execute("ALTER TABLE users RENAME COLUMN login_id_hash TO nik_hash")
        self.connection.execute("ALTER TABLE users RENAME COLUMN login_id_salt TO nik_salt")
        self.connection.execute("PRAGMA user_version = 4")

        initialize_database(self.connection)

        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(users)").fetchall()
        }
        self.assertEqual(version, 5)
        self.assertIn("login_id_hash", columns)
        self.assertIn("login_id_salt", columns)
        self.assertNotIn("nik_hash", columns)
        self.assertNotIn("nik_salt", columns)
        self.assertEqual(
            self.service.authenticate(OWNER_LOGIN_ID, PASSWORD, "owner")["id"],
            owner["id"],
        )


if __name__ == "__main__":
    unittest.main()
