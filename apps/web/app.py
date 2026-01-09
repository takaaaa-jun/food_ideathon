import sys
import random
import os
import json
import csv
import logging
import time
import datetime
import psutil
import uuid
from flask import Flask, render_template, request, g, jsonify, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

# Import from new modules
from core.database import get_db_connection
from core.utils import jst_converter
from services.search import search_recipes, get_recipe_details

# Flaskアプリケーションの初期化
app = Flask(__name__)
# プロキシ配下での動作に対応
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# --- ロギング設定 ---
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.Formatter.converter = jst_converter

logging.basicConfig(
    filename=os.path.join(log_dir, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a',
    encoding='utf-8'
)

@app.before_request
def before_request():
    g.start_time = time.time()
    
    # CookieからユーザーIDを取得、なければ新規生成
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        g.set_new_user_id = True
    else:
        g.set_new_user_id = False
    
    g.user_id = user_id

@app.context_processor
def inject_user_id():
    return dict(user_id=getattr(g, 'user_id', 'unknown'))

@app.after_request
def after_request(response):
    if request.path.startswith('/static'):
        return response

    diff = time.time() - g.start_time
    cpu_percent = psutil.cpu_percent(interval=None)
    
    log_data = {
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'duration_sec': round(diff, 4),
        'cpu_percent': cpu_percent,
        'ip': request.remote_addr,
        'user_id': getattr(g, 'user_id', 'unknown')
    }

    if getattr(g, 'set_new_user_id', False):
        # 1年間有効なCookieを設定
        expires = datetime.datetime.now() + datetime.timedelta(days=365)
        response.set_cookie('user_id', g.user_id, expires=expires)

    # 検索単語の収集
    if request.path == '/search' and request.method == 'POST':
        log_data['search_query'] = request.form.get('query')
        # インデックス/結果ページの検索は 'personal' とする
        log_data['search_mode'] = 'personal'
    elif request.path == '/standard_search' and request.method == 'POST':
        log_data['search_query'] = request.form.get('query')
        # 標準レシピ検索は 'standard' とする
        log_data['search_mode'] = 'standard'
    
    app.logger.info(f"ACCESS_LOG: {json.dumps(log_data, ensure_ascii=False)}")
    return response

@app.route('/api/log_action', methods=['POST'])
def log_action():
    try:
        data = request.json
        # user_idを追加
        data['user_id'] = getattr(g, 'user_id', 'unknown')
        app.logger.info(f"ACTION_LOG: {json.dumps(data, ensure_ascii=False)}")
        return jsonify({'status': 'success'})
    except Exception as e:
        app.logger.error(f"Error logging action: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/')
def index():
    """トップページを表示する"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """検索処理を行い、結果を表示する"""
    random.seed(os.urandom(16))
    search_query = request.form['query']
    search_mode = request.form.get('search_mode', 'or')
    
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('results.html', recipes=[], query=search_query, error="データベースに接続できませんでした．")

        cursor = conn.cursor(dictionary=True)

        # Random Start ID (1 to 1,500,000)
        rand_id = random.randint(1, 1500000)
        
        # Search 1: From rand_id
        recipes_list_1 = search_recipes(cursor, search_query, start_id=rand_id, limit=10)
        
        recipes_list = recipes_list_1
        
        # Wrap-around if needed
        if len(recipes_list) < 10:
            needed = 10 - len(recipes_list)
            recipes_list_2 = search_recipes(cursor, search_query, start_id=1, limit=needed)
            recipes_list.extend(recipes_list_2)
        
        # Total count is unknown in this method without a separate COUNT query, 
        # but displaying "Many" or just list is sufficient for streaming.
        # We pass the list to template.
        
        return render_template('results.html', recipes=recipes_list, query=search_query)

    except Exception as e:
        app.logger.error(f"Search Error: {e}")
        return render_template('results.html', recipes=[], query=search_query, error=f"エラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    """レシピ詳細を表示する"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        recipe = get_recipe_details(cursor, recipe_id)
        
        if not recipe:
            return "Recipe not found", 404
            
        return render_template('recipe_detail.html', recipe=recipe)
    except Exception as e:
        app.logger.error(f"Detail Error: {e}")
        return f"Error: {e}", 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/search_supplement', methods=['GET'])
def search_supplement():
    return render_template('results.html', error="現在、不足分の栄養検索機能は停止しています。")


@app.route('/standard_search_home')
def standard_search_home():
    """基礎レシピの検索ページを表示する"""
    return render_template('standard_search_home.html')


@app.route('/standard_search', methods=['POST'])
def standard_search():
    """基礎レシピを検索し、結果を表示する"""
    search_query = request.form['query']
    search_mode = request.form.get('search_mode', 'recipe')

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
             return render_template('standard_recipes.html', query=search_query, error="データベースに接続できませんでした．", search_mode=search_mode, basic_recipes=[], cooking_time_map={})

        cursor = conn.cursor(dictionary=True)
        
        basic_recipes = search_standard_recipes(cursor, search_query, search_mode)
        
        return render_template('standard_recipes.html', query=search_query, basic_recipes=basic_recipes, cooking_time_map=COOKING_TIME_MAP, search_mode=search_mode)

    except Exception as e:
        app.logger.error(f"Error in standard_search: {e}")
        return render_template('standard_recipes.html', query=search_query, error="検索に失敗しました", basic_recipes=[], cooking_time_map={})
    finally:
         if conn and conn.is_connected():
            conn.close()


# --- 主食（固定値）の設定 ---
STAPLE_FOODS = [
    {
        'id': 'staple_1',
        'name': '白米茶碗1杯',
        'unit': '杯',
        'energy': 234,
        'protein': 3.75,
        'fat': 0.45,
        'carbs': 54.15
    },
    {
        'id': 'staple_2',
        'name': '食パン6枚切り1枚',
        'unit': '枚',
        'energy': 148.8,
        'protein': 5.34,
        'fat': 2.46,
        'carbs': 26.46
    },
    {
        'id': 'staple_3',
        'name': '味噌汁茶碗1杯',
        'unit': '杯',
        'energy': 59,
        'protein': 5.2,
        'fat': 3.1,
        'carbs': 3.6
    },
    {
        'id': 'staple_4',
        'name': 'コーンスープ1杯',
        'unit': '杯',
        'energy': 81,
        'protein': 1.54,
        'fat': 2.6,
        'carbs': 12.81
    }
]

@app.route('/nutrition_calculation')
def nutrition_calculation():
    """栄養計算ページを表示する"""
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'nutrition_pre_ex.csv')
    ingredients = []
    
    def safe_float(val):
        if not val or val == '-' or val == '\\N':
            return 0.0
        try:
            return float(val)
        except ValueError:
            return 0.0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers_jp = next(reader)
            headers_en = next(reader)
            
            for row in reader:
                if len(row) < 7: continue 
                ingredients.append({
                    'id': row[1],
                    'name': row[2],
                    'energy': safe_float(row[3]),
                    'protein': safe_float(row[4]),
                    'fat': safe_float(row[5]),
                    'carbs': safe_float(row[6]),
                })
                
    except Exception as e:
        app.logger.error(f"Error reading csv: {e}")
        return render_template('nutrition_calculation.html', error="データの読み込みに失敗しました。", ingredients=[], staple_foods=STAPLE_FOODS)

    return render_template('nutrition_calculation.html', ingredients=ingredients, staple_foods=STAPLE_FOODS)

if __name__ == '__main__':
    # ローカルでの動作確認用
    app.run(debug=True, host='0.0.0.0', port=5000)