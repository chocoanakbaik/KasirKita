"""Tests for offline first-run tutorial persistence."""
import unittest

from kasirkita.infrastructure.database import connect_database, initialize_database
from kasirkita.services.onboarding import OnboardingService


class OnboardingServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.service = OnboardingService(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_new_install_shows_tutorial(self):
        self.assertFalse(self.service.has_seen_tutorial())

    def test_completed_tutorial_is_persisted(self):
        self.service.mark_completed()
        self.assertTrue(self.service.has_seen_tutorial())

    def test_skipping_tutorial_prevents_automatic_repeat(self):
        self.service.mark_skipped()
        self.assertTrue(self.service.has_seen_tutorial())

    def test_reset_allows_tutorial_to_show_again(self):
        self.service.mark_completed()
        self.service.reset()
        self.assertFalse(self.service.has_seen_tutorial())

    def test_state_survives_service_recreation(self):
        self.service.mark_completed()
        self.assertTrue(OnboardingService(self.connection).has_seen_tutorial())


if __name__ == "__main__":
    unittest.main()
