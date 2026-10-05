from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def hello_world():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("index.html", current_time=current_time, author="JJ1005")


if __name__ == "__main__":
    # debug=True 在開發環境中支援自動重新載入與錯誤除錯
    app.run(host="127.0.0.1", port=5000, debug=True)
