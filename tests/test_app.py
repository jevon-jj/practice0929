import unittest
from app import app

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_root_redirects_to_login_when_unauthenticated(self):
        response = self.client.get("/")
        # 未登入時應轉址至 /login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_login_page_renders(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("管理員登入".encode("utf-8"), response.data)

if __name__ == "__main__":
    unittest.main()
