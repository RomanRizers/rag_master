import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.main import create_app


class AppLifecycleTestCase(unittest.TestCase):
    def test_services_initialized_in_app_state(self):
        app = create_app()
        fake_services = SimpleNamespace(close=Mock())
        with patch("backend.main.build_services", return_value=fake_services):
            with TestClient(app) as client:
                response = client.get("/")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(hasattr(client.app.state, "services"))
                self.assertIs(client.app.state.services, fake_services)
        fake_services.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
