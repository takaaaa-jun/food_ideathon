import sys
import random
import os
import json
import csv
import mysql.connector
from flask import Flask, render_template, request, g, jsonify, url_for
import logging
import time
import datetime
import psutil
import uuid
from werkzeug.middleware.proxy_fix import ProxyFix
# import socket # ローカル実行のためコメントアウト

# Flaskアプリケーションの初期化
app = Flask(__name__)
# プロキシ配下での動作に対応（X-Forwarded-Forなどを処理）
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# --- ロギング設定 ---
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# ログの時刻をJSTにするための設定
def jst_converter(*args):
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).timetuple()

logging.Formatter.converter = jst_converter

logging.basicConfig(
    filename=os.path.join(log_dir, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
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

# --- データベース接続情報 ---
config_path = os.path.join(os.path.dirname(__file__), 'db_connection.cofg')
config_vars = {}
with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), {}, config_vars)

DB_CONFIG = config_vars['DB_CONFIG']

# --- 調理時間のマッピング ---
COOKING_TIME_MAP = {
    1: '5分以内', 2: '約10分', 3: '約15分',
    4: '約30分', 5: '約1時間', 6: '1時間以上'
}

def get_db_connection():
    """データベースへの接続を確立する"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"データベース接続エラー: {err}", file=sys.stderr)
        return None


def get_synonyms(cursor, keyword):
    """
    指定されたキーワードの同義語を取得する
    """
    synonyms = {keyword}
    
    # 1. キーワードが normalized_name かどうか確認し、そうなら synonym を取得
    sql_get_synonyms = "SELECT synonym FROM synonym_dictionary WHERE normalized_name = %s"
    cursor.execute(sql_get_synonyms, (keyword,))
    for row in cursor.fetchall():
        synonyms.add(row['synonym'])

    # 2. キーワードが synonym かどうか確認し、そうなら normalized_name を取得
    #    さらに、その normalized_name に紐づく他の synonym も取得
    sql_get_normalized = "SELECT normalized_name FROM synonym_dictionary WHERE synonym = %s"
    cursor.execute(sql_get_normalized, (keyword,))
    normalized_names = [row['normalized_name'] for row in cursor.fetchall()]
    
    for norm_name in normalized_names:
        synonyms.add(norm_name)
        cursor.execute(sql_get_synonyms, (norm_name,))
        for row in cursor.fetchall():
            synonyms.add(row['synonym'])
            
    return list(synonyms)

def get_normalized_name(cursor, keyword):
    """
    指定されたキーワードに対応する normalized_name を取得する
    """
    # 1. キーワードが既に normalized_name として存在するか確認
    sql_check_norm = "SELECT normalized_name FROM synonym_dictionary WHERE normalized_name = %s LIMIT 1"
    cursor.execute(sql_check_norm, (keyword,))
    if cursor.fetchone():
        return keyword

    # 2. キーワードが synonym の場合、対応する normalized_name を取得
    sql_get_norm = "SELECT normalized_name FROM synonym_dictionary WHERE synonym = %s LIMIT 1"
    cursor.execute(sql_get_norm, (keyword,))
    row = cursor.fetchone()
    if row:
        return row['normalized_name']
        
    return None

def unify_keywords(cursor, keywords):
    """
    キーワードリスト内の同義語を統合する。
    同じ normalized_name を持つキーワードが複数ある場合、
    synonym_dictionary 全体の中から id が最も小さいものを代表として返す。
    (入力に含まれていない同義語でも、IDが最小ならそれが採用される)
    """
    if not keywords:
        return []

    # 1. 各入力キーワードの normalized_name を取得
    placeholders = ', '.join(['%s'] * len(keywords))
    sql = f"""
        SELECT synonym, normalized_name 
        FROM synonym_dictionary 
        WHERE synonym IN ({placeholders})
    """
    cursor.execute(sql, keywords)
    rows = cursor.fetchall()
    
    # keyword -> normalized_name
    kw_to_norm = {row['synonym']: row['normalized_name'] for row in rows}
    
    # 2. 必要な normalized_name を収集
    seen_norms = set()
    for kw in keywords:
        if kw in kw_to_norm:
            seen_norms.add(kw_to_norm[kw])
            
    # 3. 各 normalized_name について、IDが最小の synonym を取得
    norm_to_best = {}
    if seen_norms:
        placeholders_norm = ', '.join(['%s'] * len(seen_norms))
        # normalized_name ごとに ID 昇順で取得し、最初の一件（最小ID）を採用する
        # MySQLのバージョンによってはウィンドウ関数が使えるが、ここではシンプルに全取得してPythonで処理するか、
        # あるいは相関サブクエリを使う。
        # シンプルに normalized_name IN (...) で取得して、Python側で最小を選ぶのが確実で速い（データ量が少なければ）。
        
        sql_best = f"""
            SELECT normalized_name, synonym, id
            FROM synonym_dictionary 
            WHERE normalized_name IN ({placeholders_norm})
            ORDER BY id ASC
        """
        cursor.execute(sql_best, list(seen_norms))
        best_rows = cursor.fetchall()
        
        for row in best_rows:
            norm = row['normalized_name']
            if norm not in norm_to_best:
                norm_to_best[norm] = row['synonym']
    
    # 4. 結果の構築 (入力順序を維持しつつ置換)
    unified_keywords = []
    processed_norms = set()
    
    for kw in keywords:
        if kw in kw_to_norm:
            norm = kw_to_norm[kw]
            if norm not in processed_norms:
                if norm in norm_to_best:
                    unified_keywords.append(norm_to_best[norm])
                processed_norms.add(norm)
        else:
            # DBにないキーワードはそのまま
            unified_keywords.append(kw)
            
    return unified_keywords

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

        normalized_query = search_query.replace('　', ' ')
        keywords = normalized_query.split()

        if not keywords:
            return render_template('results.html', recipes=[], query=search_query)

        # Separate inclusions and exclusions
        raw_inclusions = [k for k in keywords if not k.startswith('-')]
        exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1]

        # Unify inclusions (resolve synonyms to the one with smallest ID)
        unified_inclusions = unify_keywords(cursor, raw_inclusions)

        # Expand inclusions with synonyms
        inclusions = []
        for inc in unified_inclusions:
            syns = get_synonyms(cursor, inc)
            inclusions.append(syns) # List of lists: [['玉ねぎ', 'たまねぎ'], ['人参', 'にんじん']]


        attributes = ['cookpad', 'rakuten']
        selected_attribute = random.choice(attributes)

        sql_get_ids = ""
        params = []

        # Base query: Filter by attribute
        # We need to handle cases:
        # 1. Only Inclusions
        # 2. Only Exclusions (should probably show all recipes minus exclusions? or error? Let's assume error or empty for now if no inclusions, but user might want "not onion" from all. Let's support "not onion" from all.)
        # 3. Mixed

        # Strategy:
        # Find recipes that have ALL inclusions.
        # AND do NOT have ANY exclusions.

        if not inclusions and not exclusions:
             return render_template('results.html', recipes=[], query=search_query)

        # Start building the query
        # We will select recipe_ids that match criteria
        
        # Part 1: Inclusions (AND logic)
        # Part 1: Inclusions (AND logic)
        if inclusions:
            # We need to find recipes that match AT LEAST ONE synonym for EACH inclusion group.
            # Example: (name IN ('玉ねぎ', 'たまねぎ')) AND (name IN ('人参', 'にんじん'))
            
            # Since MySQL doesn't have a simple "contains all from list of lists" for a single column in a group by,
            # we can use the HAVING clause with conditional counts.
            
            conditions = []
            all_params = []
            
            for syn_group in inclusions:
                placeholders = ', '.join(['%s'] * len(syn_group))
                conditions.append(f"SUM(CASE WHEN i.name IN ({placeholders}) THEN 1 ELSE 0 END) > 0")
                all_params.extend(syn_group)
            
            having_clause = " AND ".join(conditions)
            
            # To optimize, we should also filter in WHERE clause to only include relevant ingredients
            # Flatten all synonyms for WHERE IN clause
            all_synonyms_flat = [item for sublist in inclusions for item in sublist]
            placeholders_all = ', '.join(['%s'] * len(all_synonyms_flat))
            
            sql_inclusions = f"""
                SELECT i.recipe_id, r.attribute
                FROM ingredients AS i
                JOIN recipes AS r ON i.recipe_id = r.id
                WHERE i.name IN ({placeholders_all})
                GROUP BY i.recipe_id
                HAVING {having_clause}
            """
            params_inc = all_synonyms_flat + all_params

        else:
            # If no inclusions, we start with ALL recipes (limited to 100 for performance across all attributes)
            sql_inclusions = f"""
                SELECT r.id as recipe_id, r.attribute
                FROM recipes AS r
                LIMIT 100
            """
            params_inc = []
        
        # Execute Part 1 to get candidate IDs
        cursor.execute(sql_inclusions, params_inc)
        candidates = cursor.fetchall() # List of dicts: [{'recipe_id': 1, 'attribute': 'cookpad'}, ...]
        candidate_ids = [row['recipe_id'] for row in candidates]

        if not candidate_ids:
             return render_template('results.html', recipes=[], query=search_query)

        # Part 2: Exclusions (NOT logic)
        final_candidates = candidates
        if exclusions:
            if not candidate_ids:
                final_candidates = []
            else:
                placeholders_exc = ', '.join(['%s'] * len(exclusions))
                placeholders_cand = ', '.join(['%s'] * len(candidate_ids))
                
                # Find which of the candidate_ids contain any of the exclusions
                sql_exclusions = f"""
                    SELECT DISTINCT i.recipe_id
                    FROM ingredients AS i
                    WHERE i.recipe_id IN ({placeholders_cand})
                    AND i.name IN ({placeholders_exc})
                """
                params_exc = candidate_ids + exclusions
                
                cursor.execute(sql_exclusions, params_exc)
                excluded_ids = set([row['recipe_id'] for row in cursor.fetchall()])
                
                final_candidates = [row for row in candidates if row['recipe_id'] not in excluded_ids]

        # Calculate total count (matches across ALL attributes)
        total_count = len(final_candidates)

        # Normalize attributes in candidates (convert full-width to half-width)
        import unicodedata
        for row in final_candidates:
            if row['attribute']:
                row['attribute'] = unicodedata.normalize('NFKC', row['attribute'])

        # Check which attributes have results
        available_attributes = set(row['attribute'] for row in final_candidates)
        
        # Strict filtering: Only allow 'cookpad' or 'rakuten'
        valid_attributes = {'cookpad', 'rakuten'}
        
        # Filter available attributes to only valid ones
        available_valid_attributes = available_attributes.intersection(valid_attributes)
        
        if available_valid_attributes:
            if selected_attribute not in available_valid_attributes:
                # If selected attribute is not available, pick another valid one
                selected_attribute = list(available_valid_attributes)[0]
        else:
            # If neither cookpad nor rakuten are available, but we have results (e.g. cookpad_niigataken),
            # we should probably return empty or handle it.
            # User request: "cookpadまたはrakutenに完全一致したattributeにしてほしい"
            # So if neither is available, we return empty list for display?
            # Or do we just stick to selected_attribute and return empty?
            # Let's assume we strictly filter.
            pass

        # Filter by selected attribute for display
        final_ids = [row['recipe_id'] for row in final_candidates if row['attribute'] == selected_attribute]

        recipe_ids_20 = final_ids[:20]


        # ▼▼▼ 追加：normalized_name = 'null' を含むレシピを除外 ▼▼▼
        if recipe_ids_20:
            placeholders = ', '.join(['%s'] * len(recipe_ids_20))
            sql_filter = f"""
                SELECT r.id AS recipe_id
                FROM recipes AS r
                WHERE r.id IN ({placeholders})
                AND NOT EXISTS (
                    SELECT 1
                    FROM ingredients AS i
                    JOIN ingredient_structured AS is1
                    ON is1.ingredient_id = i.id
                    WHERE i.recipe_id = r.id
                    AND is1.normalized_name = 'null'
                );
            """
            cursor.execute(sql_filter, recipe_ids_20)
            recipe_ids_20 = [row['recipe_id'] for row in cursor.fetchall()]
        # ▲▲▲ 追加ここまで ▲▲▲

        if not recipe_ids_20:
            return render_template('results.html', recipes=[], query=search_query, search_mode=search_mode, total_count=total_count)

        random.shuffle(recipe_ids_20)
        recipe_ids = recipe_ids_20[:10]

        placeholders = ', '.join(['%s'] * len(recipe_ids))
        
        # ▼▼▼ このSQLクエリを修正 ▼▼▼
        sql_get_details = f"""
            SELECT
                r.id, r.title, r.description,
                r.cooking_time, r.serving_for,
                i.id AS ingredient_id,
                i.name AS ingredient_name, i.quantity,
                s.position, s.memo AS step_memo,
                
                ist.normalized_name,
                iu.normalized_quantity,
                n.enerc_kcal,
                n.prot,
                n.fat,
                n.choavldf,
                n.fib,

                rni.serving_size,
                rni.calories AS total_calories,
                rni.protein AS total_protein,
                rni.fat AS total_fat,
                rni.carbohydrates AS total_carbohydrates
            FROM recipes AS r
            LEFT JOIN ingredients AS i ON r.id = i.recipe_id
            LEFT JOIN steps AS s ON r.id = s.recipe_id
            LEFT JOIN ingredient_structured AS ist ON i.id = ist.ingredient_id
            LEFT JOIN ingredient_units AS iu ON i.id = iu.ingredient_id
            LEFT JOIN nutritions AS n ON ist.normalized_name = n.name COLLATE utf8mb4_general_ci
            LEFT JOIN recipe_nutrition_info AS rni ON r.id = rni.recipe_id
            WHERE r.id IN ({placeholders})
            ORDER BY r.id, i.id, s.position ASC;
        """
        # ▲▲▲ ここまで修正 ▲▲▲
        
        cursor.execute(sql_get_details, recipe_ids)
        all_rows = cursor.fetchall()
        
        recipes_dict = {}
        for row in all_rows:
            recipe_id = row['id']
            if recipe_id not in recipes_dict:
                cooking_time_id = row.get('cooking_time')
                
                # recipe_nutrition_infoテーブルからの値を使用
                # serving_sizeが0やNoneの場合は1として扱う（0除算防止）
                serving_size = row.get('serving_size') or 1
                if serving_size == 0: serving_size = 1

                recipes_dict[recipe_id] = {
                    'id': row['id'],
                    'title': row['title'],
                    'description': row['description'],
                    'cooking_time': COOKING_TIME_MAP.get(cooking_time_id),
                    'serving_for': row.get('serving_for'), # 表示用には元のテキストも保持
                    'serving_size': serving_size, # 計算用の数値
                    'ingredients': {}, 
                    'steps': {},
                    'nutrition_totals': {
                        'energy': row.get('total_calories') or 0,
                        'protein': row.get('total_protein') or 0,
                        'fat': row.get('total_fat') or 0,
                        'carbs': row.get('total_carbohydrates') or 0
                    },
                    'calculated_nutrition': { # 材料からの積算値も一応保持（デバッグ用や比較用）
                        'energy': 0, 'protein': 0, 'fat': 0, 'carbs': 0
                    }
                }
            
            ingredient_id = row.get('ingredient_id')
            if ingredient_id and ingredient_id not in recipes_dict[recipe_id]['ingredients']:
                
                quantity_g = row.get('normalized_quantity') or 0
                
                n_energy_100g = row.get('enerc_kcal') or 0
                n_protein_100g = row.get('prot') or 0
                n_fat_100g = row.get('fat') or 0
                n_carbs_100g = (row.get('choavldf') or 0) + (row.get('fib') or 0)
                
                ing_nutrition = {
                    'energy': (n_energy_100g / 100.0) * quantity_g,
                    'protein': (n_protein_100g / 100.0) * quantity_g,
                    'fat': (n_fat_100g / 100.0) * quantity_g,
                    'carbs': (n_carbs_100g / 100.0) * quantity_g,
                    'normalized_name': row.get('normalized_name'),
                    'normalized_quantity_g': quantity_g
                }

                recipes_dict[recipe_id]['ingredients'][ingredient_id] = {
                    'name': row['ingredient_name'], 
                    'quantity': row['quantity'],
                    'nutrition': ing_nutrition
                }
                
                if quantity_g > 0:
                    recipes_dict[recipe_id]['calculated_nutrition']['energy'] += ing_nutrition['energy']
                    recipes_dict[recipe_id]['calculated_nutrition']['protein'] += ing_nutrition['protein']
                    recipes_dict[recipe_id]['calculated_nutrition']['fat'] += ing_nutrition['fat']
                    recipes_dict[recipe_id]['calculated_nutrition']['carbs'] += ing_nutrition['carbs']

            if row['step_memo'] and row['position'] not in recipes_dict[recipe_id]['steps']:
                recipes_dict[recipe_id]['steps'][row['position']] = {'memo': row['step_memo']}

        # 基準値
        STANDARDS = {
            'energy': 734,
            'protein': 31,
            'fat': 21,
            'carbs': 106
        }

        # ▼▼▼ 共通処理として切り出し ▼▼▼
        recipes_list = process_recipe_rows(recipes_dict)
        # ▲▲▲ ここまで修正 ▲▲▲

        # Reconstruct query for display (to show unified tags)
        display_query_parts = unified_inclusions + ['-' + exc for exc in exclusions]
        display_query = ' '.join(display_query_parts)

        return render_template('results.html', recipes=recipes_list, query=display_query, search_mode=search_mode, total_count=total_count)

    except Exception as e:
        app.logger.error(f"Error in search: {e}")
        return render_template('results.html', error="検索中にエラーが発生しました。")

# ▼▼▼ 新規ルート追加 ▼▼▼
@app.route('/search_supplement', methods=['GET'])
def search_supplement():
    return render_template('results.html', error="現在、不足分の栄養検索機能は停止しています。")

# ▼▼▼ ヘルパー関数 ▼▼▼
def build_recipes_dict(all_rows):
    recipes_dict = {}
    for row in all_rows:
        recipe_id = row['id']
        if recipe_id not in recipes_dict:
            cooking_time_id = row.get('cooking_time')
            
            serving_size = row.get('serving_size') or 1
            if serving_size == 0: serving_size = 1

            recipes_dict[recipe_id] = {
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'cooking_time': COOKING_TIME_MAP.get(cooking_time_id),
                'serving_for': row.get('serving_for'),
                'serving_size': serving_size,
                'ingredients': {}, 
                'steps': {},
                'nutrition_totals': {
                    'energy': row.get('total_calories') or 0,
                    'protein': row.get('total_protein') or 0,
                    'fat': row.get('total_fat') or 0,
                    'carbs': row.get('total_carbohydrates') or 0
                },
                'calculated_nutrition': {
                    'energy': 0, 'protein': 0, 'fat': 0, 'carbs': 0
                }
            }
        
        ingredient_id = row.get('ingredient_id')
        if ingredient_id and ingredient_id not in recipes_dict[recipe_id]['ingredients']:
            
            quantity_g = row.get('normalized_quantity') or 0
            
            n_energy_100g = row.get('enerc_kcal') or 0
            n_protein_100g = row.get('prot') or 0
            n_fat_100g = row.get('fat') or 0
            n_carbs_100g = (row.get('choavldf') or 0) + (row.get('fib') or 0)
            
            ing_nutrition = {
                'energy': (n_energy_100g / 100.0) * quantity_g,
                'protein': (n_protein_100g / 100.0) * quantity_g,
                'fat': (n_fat_100g / 100.0) * quantity_g,
                'carbs': (n_carbs_100g / 100.0) * quantity_g,
                'normalized_name': row.get('normalized_name'),
                'normalized_quantity_g': quantity_g
            }

            recipes_dict[recipe_id]['ingredients'][ingredient_id] = {
                'name': row['ingredient_name'], 
                'quantity': row['quantity'],
                'nutrition': ing_nutrition
            }
            
            if quantity_g > 0:
                recipes_dict[recipe_id]['calculated_nutrition']['energy'] += ing_nutrition['energy']
                recipes_dict[recipe_id]['calculated_nutrition']['protein'] += ing_nutrition['protein']
                recipes_dict[recipe_id]['calculated_nutrition']['fat'] += ing_nutrition['fat']
                recipes_dict[recipe_id]['calculated_nutrition']['carbs'] += ing_nutrition['carbs']

        if row['step_memo'] and row['position'] not in recipes_dict[recipe_id]['steps']:
            recipes_dict[recipe_id]['steps'][row['position']] = {'memo': row['step_memo']}
    return recipes_dict

def process_recipe_rows(recipes_dict):
    # 基準値
    STANDARDS = {
        'energy': 734,
        'protein': 31,
        'fat': 21,
        'carbs': 106
    }

    recipes_list = []
    for recipe_data in recipes_dict.values():
            # serving_sizeを使って計算
            serving_count = recipe_data['serving_size']
            
            per_serving = {
                'energy': recipe_data['nutrition_totals']['energy'] / serving_count,
                'protein': recipe_data['nutrition_totals']['protein'] / serving_count,
                'fat': recipe_data['nutrition_totals']['fat'] / serving_count,
                'carbs': recipe_data['nutrition_totals']['carbs'] / serving_count
            }
            
            nutrition_per_serving = per_serving
            
            nutrition_ratios = {
                'energy': (per_serving['energy'] / STANDARDS['energy']) * 100,
                'protein': (per_serving['protein'] / STANDARDS['protein']) * 100,
                'fat': (per_serving['fat'] / STANDARDS['fat']) * 100,
                'carbs': (per_serving['carbs'] / STANDARDS['carbs']) * 100
            }
            
            final_recipe = {
            'id': recipe_data['id'],
            'title': recipe_data['title'],
            'description': recipe_data['description'],
            'cooking_time': recipe_data['cooking_time'],
            'serving_for': recipe_data['serving_for'], # 表示用テキスト
            'serving_size': recipe_data['serving_size'], # 数値
            'ingredients': list(recipe_data['ingredients'].values()),
            'steps': [step[1] for step in sorted(recipe_data['steps'].items())],
            'nutrition_totals': recipe_data['nutrition_totals'],
            'nutrition_per_serving': nutrition_per_serving,
            'nutrition_ratios': nutrition_ratios,
            'standards': STANDARDS
        }
            recipes_list.append(final_recipe)
    return recipes_list
# ▲▲▲ ここまで修正 ▲▲▲


# --- 基礎レシピ関連のルート ---
# (変更なし)
# --- 基礎レシピ関連のルート ---

@app.route('/standard_search_home')
def standard_search_home():
    """基礎レシピの検索ページを表示する"""
    return render_template('standard_search_home.html')


@app.route('/standard_search', methods=['POST'])
def standard_search():
    """基礎レシピを検索し、結果を表示する"""
    search_query = request.form['query']
    search_mode = request.form.get('search_mode', 'recipe')

    # クエリをキーワードに分割（全角スペースも考慮）
    normalized_query = search_query.replace('　', ' ')
    keywords = normalized_query.split()

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
             return render_template('standard_recipes.html', query=search_query, error="データベースに接続できませんでした．", search_mode=search_mode, basic_recipes=[], cooking_time_map={})

        cursor = conn.cursor(dictionary=True)
        
        recipes_data = {} # recipe_id -> {details}
        recipe_ids = []

        if not keywords:
             # キーワードがない場合は空の結果を返す
             return render_template('standard_recipes.html', query=search_query, basic_recipes=[], cooking_time_map=COOKING_TIME_MAP, search_mode=search_mode)

        # Separate inclusions and exclusions
        raw_inclusions = [k for k in keywords if not k.startswith('-')]
        exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1]

        if not raw_inclusions and not exclusions:
             return render_template('standard_recipes.html', query=search_query, basic_recipes=[], cooking_time_map=COOKING_TIME_MAP, search_mode=search_mode)

        if search_mode == 'ingredient':
            # 材料名で検索 (AND検索 + NOT検索)
            # 1. Inclusions: 各キーワードを normalized_name に変換し、それを含むレシピIDの積集合をとる
            
            candidate_ids_sets = []
            
            # Inclusions処理
            if raw_inclusions:
                for keyword in raw_inclusions:
                    # Try to get normalized name
                    normalized_name = get_normalized_name(cursor, keyword)
                    
                    if normalized_name:
                        # normalized_name がある場合は完全一致で検索
                        cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                    else:
                        # ない場合は部分一致で検索
                        cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                    
                    ids = {row['standard_recipe_id'] for row in cursor.fetchall()}
                    candidate_ids_sets.append(ids)
                
                if candidate_ids_sets:
                    # 積集合をとる (AND)
                    common_ids = candidate_ids_sets[0]
                    for other_ids in candidate_ids_sets[1:]:
                        common_ids &= other_ids
                    recipe_ids = list(common_ids)
                else:
                    # inclusionsがあるのにヒットなしなら結果0
                    recipe_ids = []
            else:
                # inclusionsがない場合（exclusionsのみ）、全レシピを対象とするか？
                # ここでは全レシピIDを取得する（件数が多い場合はLIMITが必要かもしれないが、standard_recipesはそこまで多くないと想定）
                cursor.execute("SELECT id FROM standard_recipes")
                recipe_ids = [row['id'] for row in cursor.fetchall()]

            # 2. Exclusions処理 (NOT)
            if recipe_ids and exclusions:
                excluded_ids = set()
                for keyword in exclusions:
                    normalized_name = get_normalized_name(cursor, keyword)
                    if normalized_name:
                         cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                    else:
                         cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                    
                    for row in cursor.fetchall():
                        excluded_ids.add(row['standard_recipe_id'])
                
                # 除外
                recipe_ids = [rid for rid in recipe_ids if rid not in excluded_ids]

            if not recipe_ids:
                 return render_template('standard_recipes.html', query=search_query, basic_recipes=[], cooking_time_map=COOKING_TIME_MAP, search_mode=search_mode)

        else: # recipe name search
            # レシピ名（category_medium）で検索 (AND検索 + NOT検索)
            
            # Inclusions (AND)
            conditions = []
            params = []
            
            if raw_inclusions:
                for keyword in raw_inclusions:
                    conditions.append("category_medium LIKE %s")
                    params.append(f"%{keyword}%")
            
            # Exclusions (AND NOT)
            if exclusions:
                for keyword in exclusions:
                    conditions.append("category_medium NOT LIKE %s")
                    params.append(f"%{keyword}%")

            if not conditions:
                 # 条件なし
                 return render_template('standard_recipes.html', query=search_query, basic_recipes=[], cooking_time_map=COOKING_TIME_MAP, search_mode=search_mode)

            where_clause = " AND ".join(conditions)
            
            sql_search_recipes = f"""
                SELECT id
                FROM standard_recipes
                WHERE {where_clause}
            """
            cursor.execute(sql_search_recipes, tuple(params))
            recipe_ids = [row['id'] for row in cursor.fetchall()]

            if not recipe_ids:
                 return render_template('standard_recipes.html', query=search_query, basic_recipes=[], cooking_time_map=COOKING_TIME_MAP, search_mode=search_mode)

        # レシピ詳細情報の取得
        # 取得したIDに基づいて standard_recipes 情報を取得
        placeholders = ','.join(['%s'] * len(recipe_ids))
        sql_get_recipes = f"""
            SELECT * FROM standard_recipes WHERE id IN ({placeholders})
        """
        cursor.execute(sql_get_recipes, recipe_ids)
        recipes_rows = cursor.fetchall()

        for row in recipes_rows:
            recipes_data[row['id']] = {
                'name': row['category_medium'],
                'recipe_count': row['recipe_count'],
                'cooking_time': [row['cooking_time']], # リストにする
                'steps': {'average_steps': row['average_steps']},
                'ingredient': {}
            }

        # 材料情報の取得
        sql_get_ingredients = f"""
            SELECT * FROM standard_recipe_ingredients WHERE standard_recipe_id IN ({placeholders})
        """
        cursor.execute(sql_get_ingredients, recipe_ids)
        ingredients_rows = cursor.fetchall()

        for row in ingredients_rows:
            r_id = row['standard_recipe_id']
            if r_id in recipes_data:
                group = row['group_name']
                name = row['ingredient_name']
                count = row['count']
                
                if group not in recipes_data[r_id]['ingredient']:
                    recipes_data[r_id]['ingredient'][group] = {'all': [0]} # allの初期化
                
                recipes_data[r_id]['ingredient'][group][name] = [count]
                recipes_data[r_id]['ingredient'][group]['all'][0] += count

        # 手順情報の取得 (追加)
        sql_get_steps = f"""
            SELECT * FROM standard_recipe_steps WHERE standard_recipe_id IN ({placeholders})
            ORDER BY count DESC
        """
        cursor.execute(sql_get_steps, recipe_ids)
        steps_rows = cursor.fetchall()

        for row in steps_rows:
            r_id = row['standard_recipe_id']
            if r_id in recipes_data:
                if 'standard_steps' not in recipes_data[r_id]:
                    recipes_data[r_id]['standard_steps'] = []
                
                recipes_data[r_id]['standard_steps'].append({
                    'food_name': row['food_name'],
                    'action': row['action'],
                    'count': row['count']
                })

        # テンプレートに渡す形式に変換 (リストのタプル: [(name, details), ...])
        # ソート順: 
        #  - レシピ検索: recipe_count 降順 (元のロジック準拠)
        #  - 材料検索: ヒットした材料のカウント合計が多い順 (元のロジック準拠)
        
        final_recipes_list = []
        
        if search_mode == 'ingredient':
            # ヒット件数計算
            # 検索クエリ（inclusions）にマッチする材料のカウント合計を計算
            recipes_with_score = []
            for r_id, details in recipes_data.items():
                hit_count = 0
                for group_data in details['ingredient'].values():
                    for name, count_list in group_data.items():
                        if name != 'all':
                            # 各キーワードについてマッチするか確認
                            for kw in raw_inclusions:
                                if kw in name:
                                    hit_count += count_list[0]
                                    break # 1つの材料につき1回カウント（重複カウント防止）
                recipes_with_score.append((details['name'], details, hit_count))
            
            # スコア順にソート
            sorted_recipes_tuple = sorted(recipes_with_score, key=lambda x: x[2], reverse=True)
            final_recipes_list = [(item[0], item[1]) for item in sorted_recipes_tuple]

        else:
            # レシピ数順にソート
            sorted_items = sorted(recipes_data.values(), key=lambda x: x['recipe_count'], reverse=True)
            final_recipes_list = [(item['name'], item) for item in sorted_items]

        total_count = len(final_recipes_list)
        final_recipes_list = final_recipes_list[:5]

        return render_template('standard_recipes.html',
                               query=search_query,
                               basic_recipes=final_recipes_list,
                               total_count=total_count,
                               cooking_time_map=COOKING_TIME_MAP,
                               search_mode=search_mode)

    except mysql.connector.Error as err:
         return render_template('standard_recipes.html', query=search_query, error=f"データベースエラー: {err}", search_mode=search_mode, basic_recipes=[], cooking_time_map={})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- ローカル実行用の起動設定 ---
# ▲▲▲ ヘルパー関数ここまで ▲▲▲

# --- 主食（固定値）の設定 ---
# ユーザー様へ: 以下の栄養素の数値を修正してください
# 入力欄をコード内で作成しました
STAPLE_FOODS = [
    {
        'id': 'staple_1',
        'name': '白米茶碗1杯', # こめ　［水稲めし］　精白米　うるち米
        'unit': '杯',
        'energy': 234,
        'protein': 3.75,
        'fat': 0.45,
        'carbs': 54.15
    },
    {
        'id': 'staple_2',
        'name': '食パン6枚切り1枚', # こむぎ　［パン類］　角形食パン　食パン
        'unit': '枚',
        'energy': 148.8,
        'protein': 5.34,
        'fat': 2.46,
        'carbs': 26.46
    },
    {
        'id': 'staple_3',
        'name': '味噌汁茶碗1杯', # https://foodservice.ajinomoto.co.jp/recipepro/recipe/25984/
        'unit': '杯',
        'energy': 59,
        'protein': 5.2,
        'fat': 3.1,
        'carbs': 3.6
    },
    {
        'id': 'staple_4',
        'name': 'コーンスープ1杯', # https://calorie.slism.jp/118004/
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
    app.run(host='0.0.0.0', port=5000, debug=True)