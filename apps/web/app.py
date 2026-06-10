import datetime
import json
import logging
import os
import time
import uuid

import psutil

# Import Core
from core.utils import jst_converter
from flask import Flask, Response, g, request
from routes.api import api_bp
from routes.nutrition import nutrition_bp

# Import Routes (Blueprints)
from routes.personal import personal_bp
from routes.standard import standard_bp
from werkzeug.middleware.proxy_fix import ProxyFix

# Flaskアプリケーションの初期化
app = Flask(__name__)
# プロキシ配下での動作に対応
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# --- ロギング設定 ---
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.Formatter.converter = jst_converter

logging.basicConfig(
    filename=os.path.join(log_dir, "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
    encoding="utf-8",
)

# Register Blueprints
app.register_blueprint(personal_bp)
app.register_blueprint(standard_bp)
app.register_blueprint(nutrition_bp)
app.register_blueprint(api_bp)


@app.before_request
def before_request() -> None:
    g.start_time = time.time()

    # CookieからユーザーIDを取得、なければ新規生成
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())
        g.set_new_user_id = True
    else:
        g.set_new_user_id = False

    g.user_id = user_id


@app.context_processor
def inject_user_id() -> dict[str, str]:
    return {"user_id": getattr(g, "user_id", "unknown")}


@app.after_request
def after_request(response: Response) -> Response:
    if request.path.startswith("/static"):
        return response

    diff = time.time() - g.start_time
    cpu_percent = psutil.cpu_percent(interval=None)

    log_data = {
        "method": request.method,
        "path": request.path,
        "status": response.status_code,
        "duration_sec": round(diff, 4),
        "cpu_percent": cpu_percent,
        "ip": request.remote_addr,
        "user_id": getattr(g, "user_id", "unknown"),
    }

    if getattr(g, "set_new_user_id", False):
        # 1年間有効なCookieを設定
        expires = datetime.datetime.now() + datetime.timedelta(days=365)
        response.set_cookie("user_id", g.user_id, expires=expires)

    if request.path == "/search" and request.method == "POST":
        log_data["search_query"] = request.form.get("query")
        # インデックス/結果ページの検索は 'personal' とする
        log_data["search_mode"] = "personal"
    elif request.path == "/standard_search" and request.method == "POST":
        log_data["search_query"] = request.form.get("query")
        # 標準レシピ検索は 'standard' とする
        log_data["search_mode"] = "standard"

    app.logger.info(f"ACCESS_LOG: {json.dumps(log_data, ensure_ascii=False)}")
    return response


if __name__ == "__main__":
    # ローカルでの動作確認用
    app.run(debug=True, host="0.0.0.0", port=5000)
