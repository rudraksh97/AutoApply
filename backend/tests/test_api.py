import unittest
from fastapi.testclient import TestClient
import sys
import os

# Ensure backend path is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Import app after modifying path
from unittest.mock import MagicMock
sys.modules["browser_use"] = MagicMock()
sys.modules["playwright"] = MagicMock()
sys.modules["playwright.async_api"] = MagicMock()

# Mock src.agent to avoid importing real agent if browser-use fails
mock_agent = MagicMock()
sys.modules["src.agent"] = mock_agent

from api.server import app

client = TestClient(app)

class TestAPI(unittest.TestCase):
    def test_01_register_login_flow(self):
        print("\nTesting Register/Login Flow...")
        # 1. Register
        reg_payload = {"email": "test_unit@example.com", "username": "testunit", "password": "password123"}
        response = client.post("/auth/register", json=reg_payload)
        if response.status_code == 400:
            print("User already exists, proceeding to login.")
        else:
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["email"], "test_unit@example.com")
            self.assertIn("customer", data["roles"])

        # 2. Login
        login_payload = {"username": "testunit", "password": "password123"}
        response = client.post("/auth/login", json=login_payload)
        self.assertEqual(response.status_code, 200)
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.assertTrue(self.access_token)

        # 3. Get Me
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = client.get("/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "testunit")

    def test_02_admin_flow(self):
        print("\nTesting Admin Flow...")
        # Login Admin
        login_payload = {"username": "admin", "password": "admin123"}
        response = client.post("/auth/login", json=login_payload)
        self.assertEqual(response.status_code, 200, "Admin login failed")
        admin_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # List Users
        response = client.get("/admin/users", headers=headers)
        self.assertEqual(response.status_code, 200)
        users = response.json()
        self.assertGreaterEqual(len(users), 1)

        # Find testunit user
        test_user = next((u for u in users if u["username"] == "testunit"), None)
        if not test_user:
             # Create if missing (idempotency)
             self.test_01_register_login_flow()
             response = client.get("/admin/users", headers=headers)
             users = response.json()
             test_user = next((u for u in users if u["username"] == "testunit"), None)
        
        self.assertIsNotNone(test_user)
        test_user_id = test_user["id"]
        
        # Update Role
        update_payload = {"roles": ["customer", "basic"]}
        response = client.put(f"/admin/users/{test_user_id}/roles", json=update_payload, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("basic", response.json()["roles"])

    def test_03_feed_permissions(self):
        print("\nTesting Feed Permissions...")
        # 1. Login User (testunit)
        login_payload = {"username": "testunit", "password": "password123"}
        response = client.post("/auth/login", json=login_payload)
        user_token = response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 2. Add Private Feed
        feed_payload = {"url": "http://example.com/rss_unit", "name": "My Feed Unit"}
        response = client.post("/feeds", json=feed_payload, headers=user_headers)
        if response.status_code == 400: pass
        else:
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["is_global"])

        # 3. Try Add Global Feed (Should Fail)
        feed_global = {"url": "http://global.com/rss_unit", "name": "Global Feed Unit", "is_global": True}
        response = client.post("/feeds", json=feed_global, headers=user_headers)
        self.assertEqual(response.status_code, 403)

        # 4. Login Admin
        login_payload = {"username": "admin", "password": "admin123"}
        response = client.post("/auth/login", json=login_payload)
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 5. Add Global Feed (Should Succeed)
        response = client.post("/feeds", json=feed_global, headers=admin_headers)
        if response.status_code == 400: pass # Exists
        else:
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["is_global"])

        # 6. List Feeds as User (Should see Global + My Feed)
        # Note: 'testunit' must have include_global_feeds=True (default)
        response = client.get("/feeds", headers=user_headers)
        self.assertEqual(response.status_code, 200)
        feeds = response.json()
        urls = [f["url"] for f in feeds]
        self.assertIn("http://example.com/rss_unit", urls)
        self.assertIn("http://global.com/rss_unit", urls)

if __name__ == "__main__":
    unittest.main()
