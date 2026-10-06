import unittest
from app import app
from database import get_db_connection

class OrderSystemTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def login(self, username="admin", password="admin123"):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def test_01_login_logout(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("歡迎回來".encode('utf-8'), response.data)
        self.assertIn("智慧訂單管理系統".encode('utf-8'), response.data)

        # Logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("您已安全登出系統".encode('utf-8'), response.data)

    def test_02_order_list_and_filter(self):
        self.login()
        response = self.client.get('/orders')
        self.assertEqual(response.status_code, 200)
        self.assertIn("宏達科技股份有限公司".encode('utf-8'), response.data)
        self.assertIn("ORD-20261001-001".encode('utf-8'), response.data)

    def test_03_order_status_update(self):
        self.login()
        # Direct status update in list
        response = self.client.post('/orders/ORD-20261001-001/status', data=dict(
            status="已完成"
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("狀態已更新為【已完成】".encode('utf-8'), response.data)

    def test_04_order_detail_and_qrcode(self):
        # Dedicated order page /order/<order_id>
        response = self.client.get('/order/ORD-20261001-001')
        self.assertEqual(response.status_code, 200)
        self.assertIn("出貨單據 DELIVERY SLIP".encode('utf-8'), response.data)
        self.assertIn("宏達科技股份有限公司".encode('utf-8'), response.data)
        self.assertIn("data:image/png;base64,".encode('utf-8'), response.data)
        self.assertIn("智能人體工學辦公椅".encode('utf-8'), response.data)

    def test_05_price_snapshot_guarantee(self):
        self.login()
        # 取得 PROD001 原始價格 (8500)
        conn = get_db_connection()
        prod_before = conn.execute("SELECT price FROM product WHERE product_id='PROD001'").fetchone()
        self.assertEqual(prod_before['price'], 8500)
        
        # 檢視歷史訂單 ORD-20261001-001 裡的 PROD001 單價
        item_before = conn.execute("SELECT unit_price FROM order_item WHERE order_id='ORD-20261001-001' AND product_id='PROD001'").fetchone()
        self.assertEqual(item_before['unit_price'], 8500)
        conn.close()

        # 修改商品定價 (由 8500 改為 99999)
        self.client.post('/products/save', data=dict(
            mode='edit',
            product_id='PROD001',
            name='智能人體工學辦公椅',
            price='99999',
            stock='30',
            category='辦公家具'
        ), follow_redirects=True)

        # 再次檢查歷史訂單 ORD-20261001-001：單價應依然維持 8500！
        conn = get_db_connection()
        item_after = conn.execute("SELECT unit_price FROM order_item WHERE order_id='ORD-20261001-001' AND product_id='PROD001'").fetchone()
        conn.close()
        self.assertEqual(item_after['unit_price'], 8500, "歷史訂單單價未受商品改價影響 (單價快照有效)")

        # 還原商品價格
        self.client.post('/products/save', data=dict(
            mode='edit',
            product_id='PROD001',
            name='智能人體工學辦公椅',
            price='8500',
            stock='35',
            category='辦公家具'
        ), follow_redirects=True)

    def test_06_create_order_flow(self):
        self.login()
        # 新增訂單：選客戶 CUST002，勾選 PROD002 (qty=2) 與 PROD003 (qty=1)
        response = self.client.post('/orders/new', data={
            'customer_id': 'CUST002',
            'sales_rep': '測試業務員',
            'order_date': '2026-10-06 18:00',
            'product_ids': ['PROD002', 'PROD003'],
            'qty_PROD002': '2',
            'qty_PROD003': '1'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("出貨單據 DELIVERY SLIP".encode('utf-8'), response.data)
        self.assertIn("宇陽文創設計有限公司".encode('utf-8'), response.data)

if __name__ == '__main__':
    unittest.main()
