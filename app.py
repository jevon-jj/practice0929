import os
import io
import base64
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify, abort
)
from werkzeug.security import check_password_hash
import qrcode

from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "order-system-secure-key-2026-practice")

# 初始化資料庫
with app.app_context():
    init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("請先登入系統以存取管理功能", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def generate_order_qrcode_base64(order_id, customer_name, total_amount, order_url):
    """產生出貨單專屬 QRCode (Base64 PNG)"""
    qr_content = f"出貨單號: {order_id}\n客戶: {customer_name}\n總金額: NT$ {total_amount:,}\n查驗網址: {order_url}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e293b", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_b64}"

@app.context_processor
def inject_globals():
    return {
        "current_user": session.get("display_name"),
        "is_logged_in": "user_id" in session,
        "now": datetime.now()
    }

# ----------------------------------------------------
# 認證路由 (Auth)
# ----------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("orders_list"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM admin_user WHERE username = ?;", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["display_name"] = user["display_name"]
            flash(f"歡迎回來，{user['display_name']}！", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("orders_list"))
        else:
            flash("帳號或密碼錯誤，請重新輸入（預設: admin / admin123）", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("您已安全登出系統", "info")
    return redirect(url_for("login"))

# ----------------------------------------------------
# 訂單管理 (Orders)
# ----------------------------------------------------
@app.route("/")
@app.route("/orders")
@login_required
def orders_list():
    status_filter = request.args.get("status", "")
    search_query = request.args.get("q", "").strip()

    conn = get_db_connection()
    
    query = """
        SELECT 
            o.order_id, 
            o.order_date, 
            o.status, 
            o.sales_rep,
            c.customer_id, 
            c.name AS customer_name,
            c.phone AS customer_phone,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_amount,
            COUNT(oi.product_id) AS total_items
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        LEFT JOIN order_item oi ON o.order_id = oi.order_id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND o.status = ?"
        params.append(status_filter)

    if search_query:
        query += " AND (o.order_id LIKE ? OR c.name LIKE ? OR o.sales_rep LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard])

    query += " GROUP BY o.order_id ORDER BY o.order_date DESC;"

    orders = conn.execute(query, params).fetchall()

    # 取得各狀態統計數量
    stats = {
        "all": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "處理中": conn.execute("SELECT COUNT(*) FROM orders WHERE status='處理中'").fetchone()[0],
        "已出貨": conn.execute("SELECT COUNT(*) FROM orders WHERE status='已出貨'").fetchone()[0],
        "已完成": conn.execute("SELECT COUNT(*) FROM orders WHERE status='已完成'").fetchone()[0],
        "已取消": conn.execute("SELECT COUNT(*) FROM orders WHERE status='已取消'").fetchone()[0],
    }
    conn.close()

    return render_template(
        "orders.html",
        orders=orders,
        status_filter=status_filter,
        search_query=search_query,
        stats=stats
    )

@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def order_create():
    conn = get_db_connection()

    if request.method == "POST":
        customer_id = request.form.get("customer_id", "").strip()
        sales_rep = request.form.get("sales_rep", "").strip()
        order_date = request.form.get("order_date", "").strip()
        
        if not order_date:
            order_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 取得勾選之商品與數量
        selected_product_ids = request.form.getlist("product_ids")

        if not customer_id:
            flash("請選擇客戶！", "danger")
            conn.close()
            return redirect(url_for("order_create"))

        if not selected_product_ids:
            flash("請至少勾選一項訂購商品！", "danger")
            conn.close()
            return redirect(url_for("order_create"))

        # 產生新訂單編號 (例如 ORD-YYYYMMDD-XXX)
        date_prefix = datetime.now().strftime("ORD-%Y%m%d-")
        count_today = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE order_id LIKE ?;", (f"{date_prefix}%",)
        ).fetchone()[0]
        order_id = f"{date_prefix}{count_today + 1:03d}"

        try:
            # 建立訂單主檔
            conn.execute(
                "INSERT INTO orders (order_id, customer_id, order_date, status, sales_rep) VALUES (?, ?, ?, ?, ?);",
                (order_id, customer_id, order_date, "處理中", sales_rep or session.get("display_name", "業務人員"))
            )

            # 寫入訂單明細 order_item (以「當下商品單價」進行保存，商品改價不影響歷史訂單)
            valid_items_count = 0
            for pid in selected_product_ids:
                qty_str = request.form.get(f"qty_{pid}", "1")
                try:
                    qty = int(qty_str)
                except ValueError:
                    qty = 1
                
                if qty <= 0:
                    continue

                # 讀取當下商品現行單價
                prod = conn.execute("SELECT price FROM product WHERE product_id = ?;", (pid,)).fetchone()
                if prod:
                    current_unit_price = prod["price"]
                    conn.execute(
                        "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?);",
                        (order_id, pid, qty, current_unit_price)
                    )
                    # 扣減庫存
                    conn.execute(
                        "UPDATE product SET stock = MAX(0, stock - ?) WHERE product_id = ?;",
                        (qty, pid)
                    )
                    valid_items_count += 1

            if valid_items_count == 0:
                conn.rollback()
                flash("商品數量必須大於 0！", "danger")
                conn.close()
                return redirect(url_for("order_create"))

            conn.commit()
            flash(f"訂單 {order_id} 建立成功！已鎖定當時商品單價與扣減庫存。", "success")
            conn.close()
            return redirect(url_for("order_detail", order_id=order_id))

        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f"新增訂單時發生錯誤: {str(e)}", "danger")
            return redirect(url_for("order_create"))

    # GET 請求: 讀取客戶清單與商品清單
    customers = conn.execute("SELECT * FROM customer ORDER BY customer_id ASC;").fetchall()
    products = conn.execute("SELECT * FROM product ORDER BY category ASC, product_id ASC;").fetchall()
    conn.close()

    default_order_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    default_sales_rep = session.get("display_name", "系統管理員")

    return render_template(
        "order_create.html",
        customers=customers,
        products=products,
        default_order_date=default_order_date,
        default_sales_rep=default_sales_rep
    )

@app.route("/orders/<order_id>/status", methods=["POST"])
@login_required
def order_update_status(order_id):
    """在列表或頁面直接更新訂單狀態"""
    new_status = request.form.get("status", "").strip()
    valid_statuses = ["處理中", "已出貨", "已完成", "已取消"]

    if new_status not in valid_statuses:
        flash("不正確的訂單狀態！", "danger")
        return redirect(request.referrer or url_for("orders_list"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE orders SET status = ? WHERE order_id = ?;",
        (new_status, order_id)
    )
    conn.commit()
    conn.close()

    flash(f"訂單 {order_id} 狀態已更新為【{new_status}】", "success")
    return redirect(request.referrer or url_for("orders_list"))

@app.route("/orders/<order_id>/delete", methods=["POST"])
@login_required
def order_delete(order_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM orders WHERE order_id = ?;", (order_id,))
    conn.commit()
    conn.close()
    flash(f"訂單 {order_id} 及其明細已成功刪除！", "info")
    return redirect(url_for("orders_list"))

# ----------------------------------------------------
# 專屬出貨單頁面與 QRCode (/order/<訂單編號>)
# ----------------------------------------------------
@app.route("/order/<order_id>")
def order_detail(order_id):
    conn = get_db_connection()
    
    order = conn.execute("""
        SELECT 
            o.order_id, 
            o.order_date, 
            o.status, 
            o.sales_rep,
            c.customer_id, 
            c.name AS customer_name,
            c.phone AS customer_phone,
            c.address AS customer_address
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?;
    """, (order_id,)).fetchone()

    if not order:
        conn.close()
        abort(404)

    # 讀取訂單明細 (保存的 unit_price，以及當時商品名稱)
    items = conn.execute("""
        SELECT 
            oi.product_id, 
            oi.quantity, 
            oi.unit_price,
            (oi.quantity * oi.unit_price) AS subtotal,
            p.name AS product_name,
            p.category AS product_category,
            p.price AS current_market_price
        FROM order_item oi
        JOIN product p ON oi.product_id = p.product_id
        WHERE oi.order_id = ?
        ORDER BY oi.product_id ASC;
    """, (order_id,)).fetchall()

    total_amount = sum(item["subtotal"] for item in items)
    conn.close()

    # 產生出貨單專屬 QRCode (含查驗 URL)
    order_url = url_for("order_detail", order_id=order_id, _external=True)
    qrcode_b64 = generate_order_qrcode_base64(
        order_id=order["order_id"],
        customer_name=order["customer_name"],
        total_amount=total_amount,
        order_url=order_url
    )

    return render_template(
        "order_detail.html",
        order=order,
        items=items,
        total_amount=total_amount,
        qrcode_b64=qrcode_b64,
        order_url=order_url
    )

# ----------------------------------------------------
# 客戶管理 (Customer CRUD)
# ----------------------------------------------------
@app.route("/customers")
@login_required
def customers_list():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    if q:
        wildcard = f"%{q}%"
        customers = conn.execute("""
            SELECT c.*, COUNT(o.order_id) AS order_count
            FROM customer c
            LEFT JOIN orders o ON c.customer_id = o.customer_id
            WHERE c.customer_id LIKE ? OR c.name LIKE ? OR c.phone LIKE ? OR c.address LIKE ?
            GROUP BY c.customer_id
            ORDER BY c.customer_id ASC;
        """, (wildcard, wildcard, wildcard, wildcard)).fetchall()
    else:
        customers = conn.execute("""
            SELECT c.*, COUNT(o.order_id) AS order_count
            FROM customer c
            LEFT JOIN orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_id
            ORDER BY c.customer_id ASC;
        """).fetchall()
    conn.close()
    return render_template("customers.html", customers=customers, search_query=q)

@app.route("/customers/save", methods=["POST"])
@login_required
def customer_save():
    mode = request.form.get("mode", "add") # add or edit
    customer_id = request.form.get("customer_id", "").strip()
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    if not customer_id or not name or not phone or not address:
        flash("所有客戶欄位均為必填！", "danger")
        return redirect(url_for("customers_list"))

    conn = get_db_connection()
    try:
        if mode == "add":
            exists = conn.execute("SELECT 1 FROM customer WHERE customer_id = ?;", (customer_id,)).fetchone()
            if exists:
                flash(f"客戶編號【{customer_id}】已存在，請使用不同編號！", "danger")
            else:
                conn.execute(
                    "INSERT INTO customer (customer_id, name, phone, address) VALUES (?, ?, ?, ?);",
                    (customer_id, name, phone, address)
                )
                conn.commit()
                flash(f"客戶【{name}】新增成功！", "success")
        else: # edit
            conn.execute(
                "UPDATE customer SET name = ?, phone = ?, address = ? WHERE customer_id = ?;",
                (name, phone, address, customer_id)
            )
            conn.commit()
            flash(f"客戶【{name}】資料已更新！", "success")
    except Exception as e:
        flash(f"儲存客戶時發生錯誤: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("customers_list"))

@app.route("/customers/<customer_id>/delete", methods=["POST"])
@login_required
def customer_delete(customer_id):
    conn = get_db_connection()
    # 檢查是否有歷史訂單
    has_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ?;", (customer_id,)).fetchone()[0]
    if has_orders > 0:
        flash(f"客戶【{customer_id}】已有 {has_orders} 筆關聯訂單，無法直接刪除！", "warning")
    else:
        conn.execute("DELETE FROM customer WHERE customer_id = ?;", (customer_id,))
        conn.commit()
        flash(f"客戶【{customer_id}】已刪除！", "info")
    conn.close()
    return redirect(url_for("customers_list"))

# ----------------------------------------------------
# 商品管理 (Product CRUD)
# ----------------------------------------------------
@app.route("/products")
@login_required
def products_list():
    q = request.args.get("q", "").strip()
    category_filter = request.args.get("category", "").strip()

    conn = get_db_connection()
    query = "SELECT * FROM product WHERE 1=1"
    params = []

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    if q:
        query += " AND (product_id LIKE ? OR name LIKE ? OR category LIKE ?)"
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard])

    query += " ORDER BY category ASC, product_id ASC;"
    products = conn.execute(query, params).fetchall()

    categories = [r[0] for r in conn.execute("SELECT DISTINCT category FROM product ORDER BY category ASC;").fetchall()]
    conn.close()

    return render_template(
        "products.html",
        products=products,
        categories=categories,
        search_query=q,
        category_filter=category_filter
    )

@app.route("/products/save", methods=["POST"])
@login_required
def product_save():
    mode = request.form.get("mode", "add")
    product_id = request.form.get("product_id", "").strip()
    name = request.form.get("name", "").strip()
    price_str = request.form.get("price", "0").strip()
    stock_str = request.form.get("stock", "0").strip()
    category = request.form.get("category", "").strip()

    try:
        price = int(price_str)
        stock = int(stock_str)
    except ValueError:
        flash("單價與庫存必須為整數！", "danger")
        return redirect(url_for("products_list"))

    if not product_id or not name or not category or price < 0:
        flash("請完整填寫商品資訊且單價不可為負！", "danger")
        return redirect(url_for("products_list"))

    conn = get_db_connection()
    try:
        if mode == "add":
            exists = conn.execute("SELECT 1 FROM product WHERE product_id = ?;", (product_id,)).fetchone()
            if exists:
                flash(f"商品編號【{product_id}】已存在！", "danger")
            else:
                conn.execute(
                    "INSERT INTO product (product_id, name, price, stock, category) VALUES (?, ?, ?, ?, ?);",
                    (product_id, name, price, stock, category)
                )
                conn.commit()
                flash(f"商品【{name}】新增成功！", "success")
        else:
            conn.execute(
                "UPDATE product SET name = ?, price = ?, stock = ?, category = ? WHERE product_id = ?;",
                (name, price, stock, category, product_id)
            )
            conn.commit()
            flash(f"商品【{name}】資料已更新！(注意: 此改價不會影響歷史已成立之訂單)", "success")
    except Exception as e:
        flash(f"儲存商品時發生錯誤: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("products_list"))

@app.route("/products/<product_id>/delete", methods=["POST"])
@login_required
def product_delete(product_id):
    conn = get_db_connection()
    has_orders = conn.execute("SELECT COUNT(*) FROM order_item WHERE product_id = ?;", (product_id,)).fetchone()[0]
    if has_orders > 0:
        flash(f"商品【{product_id}】已有 {has_orders} 筆關聯歷史訂單明細，無法直接刪除！", "warning")
    else:
        conn.execute("DELETE FROM product WHERE product_id = ?;", (product_id,))
        conn.commit()
        flash(f"商品【{product_id}】已成功刪除！", "info")
    conn.close()
    return redirect(url_for("products_list"))

# ----------------------------------------------------
# 錯誤處理
# ----------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
