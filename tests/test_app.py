import unittest
from app import app

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hello, World!".encode("utf-8"), response.data)
        self.assertIn("JJ1005".encode("utf-8"), response.data)

if __name__ == "__main__":
    unittest.main()
