# Flask Practice 0929

![CI/CD Pipeline](https://github.com/jevon-jj/practice0929/actions/workflows/cicd.yml/badge.svg)

這是一個使用 Python Flask 框架所建構的現代化一頁式網站應用，支援自動化 CI/CD 測試與部署至 Render。

## 🌟 專案特色

- **現代化設計**：毛玻璃效果（Glassmorphism）、微動畫與優雅的漸層配色。
- **製作者**：JJ1005
- **自動化 CI/CD**：透過 GitHub Actions 執行自動化單元測試，並無縫部署至 Render。
- **生產環境就緒**：支援 Gunicorn WSGI 伺服器。

## 🛠️ 本地開發與執行

### 1. 啟用虛擬環境 (Virtualenv)

```powershell
# 建立虛擬環境
python -m venv venv

# 啟用虛擬環境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

### 3. 啟動伺服器

```bash
python app.py
```

瀏覽器訪問：[http://127.0.0.1:5000](http://127.0.0.1:5000)

### 4. 執行單元測試

```bash
python -m unittest discover tests
```
