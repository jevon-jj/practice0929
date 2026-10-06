# 企業訂單管理系統 (Flask + SQLite + Bootstrap 5)

本專案為輕量且功能完善的訂單管理系統，具備歷史價格快照（Price Snapshot）、多商品勾選下單、出貨單專屬 QRCode 產生與列表即時狀態更新功能。

---

## 🚀 系統快速啟動方式

### 1. 啟用虛擬環境 (Virtual Environment)
在專案根目錄開啟終端機（PowerShell 或 CMD）：

```powershell
.\venv\Scripts\Activate.ps1
```
*(若未建立虛擬環境，可執行 `python -m venv venv` 並安裝套件 `pip install -r requirements.txt`)*

### 2. 啟動 Flask 伺服器
```powershell
python app.py
```
啟動後請使用瀏覽器開啟：[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🔐 預設管理員帳號與密碼

| 項目 | 預設值 | 說明 |
| :--- | :--- | :--- |
| **登入網址** | `http://127.0.0.1:5000/login` | 未登入存取受保護頁面將自動引導至登入頁 |
| **帳號 (Username)** | `admin` | 系統管理員 |
| **密碼 (Password)** | `admin123` | 使用 Werkzeug 安全雜湊加密儲存 |

---

## 📊 資料表結構 (SQLite Database Schema)

1. **`customer` (客戶主檔)**
   - `customer_id` (TEXT, **PK**): 客戶編號 (如 `CUST001`)
   - `name` (TEXT): 客戶/公司名稱
   - `phone` (TEXT): 聯絡電話
   - `address` (TEXT): 送貨地址

2. **`product` (商品主檔)**
   - `product_id` (TEXT, **PK**): 商品編號 (如 `PROD001`)
   - `name` (TEXT): 商品名稱
   - `price` (INTEGER): 現行商品定價
   - `stock` (INTEGER): 庫存數量
   - `category` (TEXT): 商品分類

3. **`orders` (訂單主檔)**
   - `order_id` (TEXT, **PK**): 訂單編號 (如 `ORD-20261001-001`)
   - `customer_id` (TEXT, **FK**): 關聯 `customer.customer_id`
   - `order_date` (TEXT): 下單日期時間
   - `status` (TEXT): 訂單狀態 (`處理中` / `已出貨` / `已完成` / `已取消`)
   - `sales_rep` (TEXT): 承辦業務人員

4. **`order_item` (訂單明細檔 - 複合主鍵 & 單價快照)**
   - `order_id` (TEXT, **FK**): 關聯 `orders.order_id` (ON DELETE CASCADE)
   - `product_id` (TEXT, **FK**): 關聯 `product.product_id`
   - `quantity` (INTEGER): 購買數量
   - `unit_price` (INTEGER): **下單當下的成交單價** (歷史改價不影響)
   - **PRIMARY KEY (`order_id`, `product_id`)**

---

## ✨ 核心功能特色

1. **管理員權限保護**：登入後可進行客戶、商品、訂單完整維護。
2. **多品項勾選下單**：
   - 客戶使用下拉選單，並即時預覽電話與送貨地址。
   - 商品列表可一次勾選多項商品，並可直接輸入購買數量。
   - 具備全選/取消按鈕與前端即時金額試算功能。
3. **單價快照保證 (Price Snapshot)**：
   - 下單時會將當下的商品單價寫入 `order_item.unit_price`。
   - 後續商品調漲或特價，歷史訂單與出貨單金額絕不變動。
4. **訂單列表即時更新狀態**：
   - 訂單列表中可直接切換「處理中 / 已出貨 / 已完成 / 已取消」，無需跳頁。
5. **專屬出貨單與 QRCode (`/order/<訂單編號>`)**：
   - 每張訂單具備專屬出貨單版面，內嵌由 Python `qrcode` 生成的驗證 QRCode。
   - 支援出貨單一鍵列印（內建 Print CSS 樣式）。
6. **UTF-8 全面防亂碼保證**：從 SQLite、Flask、Jinja2 到 HTML 標籤均採用標準 UTF-8 編碼。

---

## 🧪 執行自動化測試

```powershell
python -m unittest tests\test_system.py
```
