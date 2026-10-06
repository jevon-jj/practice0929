import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "order_system.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 建立管理員資料表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL
    );
    """)

    # 1. 客戶資料表 customer
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL
    );
    """)

    # 2. 商品資料表 product
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product (
        product_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        category TEXT NOT NULL
    );
    """)

    # 3. 訂單資料表 orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        order_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT '處理中',
        sales_rep TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT
    );
    """)

    # 4. 訂單明細資料表 order_item (複合主鍵)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_item (
        order_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price INTEGER NOT NULL,
        PRIMARY KEY (order_id, product_id),
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE RESTRICT
    );
    """)

    conn.commit()

    # 檢查並插入初始資料 (5筆繁體中文測試資料與預設管理員)
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()

    # 預設管理員
    cursor.execute("SELECT COUNT(*) FROM admin_user;")
    if cursor.fetchone()[0] == 0:
        admin_pwd_hash = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO admin_user (username, password_hash, display_name) VALUES (?, ?, ?);",
            ("admin", admin_pwd_hash, "系統管理員")
        )

    # 1. 客戶 5 筆繁體中文資料
    cursor.execute("SELECT COUNT(*) FROM customer;")
    if cursor.fetchone()[0] == 0:
        customers = [
            ("CUST001", "宏達科技股份有限公司", "02-27891234", "台北市信義區信義路五段7號"),
            ("CUST002", "宇陽文創設計有限公司", "04-23115678", "台中市西屯區台灣大道三段99號"),
            ("CUST003", "綠洲生鮮超市連鎖", "07-3344556", "高雄市前金區五福三路58號"),
            ("CUST004", "藍天數位整合行銷", "03-5712345", "新竹市東區光復路二段101號"),
            ("CUST005", "豐盛生活實業社", "06-2289900", "台南市中西區西門路一段658號")
        ]
        cursor.executemany(
            "INSERT INTO customer (customer_id, name, phone, address) VALUES (?, ?, ?, ?);",
            customers
        )

    # 2. 商品 5 筆繁體中文資料
    cursor.execute("SELECT COUNT(*) FROM product;")
    if cursor.fetchone()[0] == 0:
        products = [
            ("PROD001", "智能人體工學辦公椅", 8500, 35, "辦公家具"),
            ("PROD002", "4K 極致極窄邊框螢幕 27吋", 12900, 20, "3C電子"),
            ("PROD003", "降噪無線藍牙耳機 Pro", 4500, 50, "影音設備"),
            ("PROD004", "義式全自動雙豆槽咖啡機", 26800, 12, "廚房家電"),
            ("PROD005", "頂級防潑水多功能電腦背包", 1980, 80, "生活配件")
        ]
        cursor.executemany(
            "INSERT INTO product (product_id, name, price, stock, category) VALUES (?, ?, ?, ?, ?);",
            products
        )

    # 3. 訂單與訂單明細 5 筆繁體中文資料
    cursor.execute("SELECT COUNT(*) FROM orders;")
    if cursor.fetchone()[0] == 0:
        orders_data = [
            ("ORD-20261001-001", "CUST001", "2026-10-01 10:30", "處理中", "陳建宏", [
                ("PROD001", 2, 8500),
                ("PROD002", 1, 12900)
            ]),
            ("ORD-20261002-002", "CUST002", "2026-10-02 14:15", "已出貨", "林雅婷", [
                ("PROD003", 3, 4500),
                ("PROD005", 2, 1980)
            ]),
            ("ORD-20261003-003", "CUST003", "2026-10-03 09:00", "已完成", "黃志強", [
                ("PROD004", 1, 26800)
            ]),
            ("ORD-20261004-004", "CUST004", "2026-10-04 16:45", "處理中", "吳佩玲", [
                ("PROD002", 2, 12900),
                ("PROD003", 1, 4500)
            ]),
            ("ORD-20261005-005", "CUST005", "2026-10-05 11:20", "已取消", "張偉哲", [
                ("PROD001", 1, 8500),
                ("PROD005", 4, 1980)
            ])
        ]

        for order_id, cust_id, odate, status, sales, items in orders_data:
            cursor.execute(
                "INSERT INTO orders (order_id, customer_id, order_date, status, sales_rep) VALUES (?, ?, ?, ?, ?);",
                (order_id, cust_id, odate, status, sales)
            )
            for prod_id, qty, unit_price in items:
                cursor.execute(
                    "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?);",
                    (order_id, prod_id, qty, unit_price)
                )

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with test data.")
