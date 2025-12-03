import sys
import random
import os
import json
import mysql.connector
from flask import Flask, render_template, request
# import socket # ローカル実行のためコメントアウト

# Flaskアプリケーションの初期化
app = Flask(__name__)

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

        attributes = ['cookpad', 'rakuten']
        selected_attribute = random.choice(attributes)

        sql_get_ids = ""
        params = []

        if search_mode == 'and':
            placeholders = ', '.join(['%s'] * len(keywords))
            sql_get_ids = f"""
                SELECT i.recipe_id FROM ingredients AS i
                JOIN recipes AS r ON i.recipe_id = r.id
                WHERE r.attribute = %s AND i.name IN ({placeholders})
                GROUP BY i.recipe_id
                HAVING COUNT(DISTINCT i.name) = %s
                LIMIT 20;
            """
            params = [selected_attribute] + keywords + [len(keywords)]

        elif search_mode == 'not':
            if len(keywords) < 2:
                error_msg = "NOT検索には、含む材料と除外する材料の2つをスペース区切りで入力してください．"
                return render_template('results.html', recipes=[], query=search_query, error=error_msg)
            include_ingredient = keywords[0]
            exclude_ingredient = keywords[1]
            sql_get_ids = """
                SELECT DISTINCT i.recipe_id FROM ingredients AS i
                JOIN recipes AS r ON i.recipe_id = r.id
                WHERE r.attribute = %s AND i.name = %s AND i.recipe_id NOT IN (
                    SELECT DISTINCT recipe_id FROM ingredients WHERE name = %s
                )
                LIMIT 20;
            """
            params = [selected_attribute, include_ingredient, exclude_ingredient]

        else: # or
            placeholders = ', '.join(['%s'] * len(keywords))
            sql_get_ids = f"""
                SELECT DISTINCT i.recipe_id FROM ingredients AS i
                JOIN recipes AS r ON i.recipe_id = r.id
                WHERE r.attribute = %s AND i.name IN ({placeholders})
                LIMIT 20;
            """
            params = [selected_attribute] + keywords

        cursor.execute(sql_get_ids, params)
        recipe_ids_20 = [row['recipe_id'] for row in cursor.fetchall()]
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
            return render_template('results.html', recipes=[], query=search_query)

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

        return render_template('results.html', recipes=recipes_list, query=search_query)

    except Exception as e:
        app.logger.error(f"Error in search: {e}")
        return render_template('results.html', error="検索中にエラーが発生しました。")

# ▼▼▼ 新規ルート追加 ▼▼▼
@app.route('/search_supplement', methods=['GET'])
def search_supplement():
    try:
        missing_calories = float(request.args.get('missing_calories', 0))
        
        if missing_calories <= 0:
             return render_template('results.html', error="不足カロリーが正しく指定されていません。")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 全レシピを取得し、不足カロリーに近い順にソートするクエリ
        # normalized_name = 'null' の除外も適用
        # パフォーマンス向上のため、必要なカラムのみ取得してPython側で計算・ソートするか、
        # あるいはSQLで計算するか。ここではSQLで計算してソートする。
        # ただし、詳細情報（材料など）も表示する必要があるため、2段階で取得する。
        
        # 1. 対象レシピIDを取得
        # GROUP BYエラーを回避するため、JOINではなくサブクエリを使用
        sql_find_ids = """
            SELECT 
                rni.recipe_id,
                ABS((rni.calories / rni.serving_size) - %s) AS diff
            FROM recipe_nutrition_info AS rni
            WHERE rni.serving_size > 0
            AND rni.recipe_id IN (
                SELECT DISTINCT i.recipe_id 
                FROM ingredients AS i
                JOIN ingredient_structured AS ist ON i.id = ist.ingredient_id
                WHERE ist.normalized_name != 'null'
            )
            ORDER BY diff ASC
            LIMIT 20
        """
        
        cursor.execute(sql_find_ids, (missing_calories,))
        target_recipes = cursor.fetchall()
        
        if not target_recipes:
             cursor.close()
             conn.close()
             return render_template('results.html', recipes=[], query=f"不足 {missing_calories:.1f} kcal を補うレシピ")

        recipe_ids = [row['recipe_id'] for row in target_recipes]
        placeholders = ','.join(['%s'] * len(recipe_ids))
        
        # 2. 詳細情報を取得（search関数と同じクエリを使用）
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
            ORDER BY FIELD(r.id, {placeholders}), i.id, s.position ASC;
        """
        
        # ORDER BY FIELD を使って、diff順（recipe_idsの順序）を維持する
        params = recipe_ids + recipe_ids # IN句用 + FIELD関数用
        cursor.execute(sql_get_details, params)
        all_rows = cursor.fetchall()
        
        cursor.close()
        conn.close()

        # データ構築処理（共通化したいが、まずはここに記述し、後でリファクタリングも検討）
        recipes_dict = build_recipes_dict(all_rows)
        recipes_list = process_recipe_rows(recipes_dict)

        return render_template('results.html', recipes=recipes_list, query=f"不足 {missing_calories:.1f} kcal を補うレシピ")

    except Exception as e:
        app.logger.error(f"Error in search_supplement: {e}")
        return render_template('results.html', error="検索中にエラーが発生しました。")

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

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
             return render_template('standard_recipes.html', query=search_query, error="データベースに接続できませんでした．", search_mode=search_mode, basic_recipes=[], cooking_time_map={})

        cursor = conn.cursor(dictionary=True)
        
        recipes_data = {} # recipe_id -> {details}
        recipe_ids = []

        if search_mode == 'ingredient':
            # 材料名で検索
            # standard_recipe_ingredients から検索
            sql_search_ingredients = """
                SELECT DISTINCT standard_recipe_id
                FROM standard_recipe_ingredients
                WHERE ingredient_name LIKE %s
            """
            cursor.execute(sql_search_ingredients, (f"%{search_query}%",))
            recipe_ids = [row['standard_recipe_id'] for row in cursor.fetchall()]
            
            # 該当するレシピがなければ終了
            if not recipe_ids:
                 return render_template('standard_recipes.html', query=search_query, basic_recipes=[], cooking_time_map=COOKING_TIME_MAP, search_mode=search_mode)

        else: # recipe name search
            # レシピ名（category_medium）で検索
            sql_search_recipes = """
                SELECT id
                FROM standard_recipes
                WHERE category_medium LIKE %s
            """
            cursor.execute(sql_search_recipes, (f"%{search_query}%",))
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
            # 検索クエリにマッチする材料のカウント合計を計算
            recipes_with_score = []
            for r_id, details in recipes_data.items():
                hit_count = 0
                for group_data in details['ingredient'].values():
                    for name, count_list in group_data.items():
                        if name != 'all' and search_query in name: # 部分一致で簡易判定
                             hit_count += count_list[0]
                recipes_with_score.append((details['name'], details, hit_count))
            
            # スコア順にソート
            sorted_recipes_tuple = sorted(recipes_with_score, key=lambda x: x[2], reverse=True)
            final_recipes_list = [(item[0], item[1]) for item in sorted_recipes_tuple]

        else:
            # レシピ数順にソート
            sorted_items = sorted(recipes_data.values(), key=lambda x: x['recipe_count'], reverse=True)
            final_recipes_list = [(item['name'], item) for item in sorted_items]

        return render_template('standard_recipes.html',
                               query=search_query,
                               basic_recipes=final_recipes_list,
                               cooking_time_map=COOKING_TIME_MAP,
                               search_mode=search_mode)

    except mysql.connector.Error as err:
         return render_template('standard_recipes.html', query=search_query, error=f"データベースエラー: {err}", search_mode=search_mode, basic_recipes=[], cooking_time_map={})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- ローカル実行用の起動設定 ---
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)