import sys
import random
import os
import json
import mysql.connector
from flask import Flask, render_template, request

# Flaskアプリケーションの初期化
app = Flask(__name__)

# --- データベース接続情報 ---
DB_CONFIG = {
    'user': 'root',
    'password': 'Gdtkjnuaa1024',
    'host': '127.0.0.1',
    'database': 'database_food_ideathon'
}

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
        
        if not recipe_ids_20:
            return render_template('results.html', recipes=[], query=search_query)

        random.shuffle(recipe_ids_20)
        recipe_ids = recipe_ids_20[:10]

        placeholders = ', '.join(['%s'] * len(recipe_ids))
        sql_get_details = f"""
            SELECT
                r.id, r.title, r.description,
                r.cooking_time, r.serving_for,
                i.name AS ingredient_name, i.quantity,
                s.position, s.memo AS step_memo
            FROM recipes AS r
            LEFT JOIN ingredients AS i ON r.id = i.recipe_id
            LEFT JOIN steps AS s ON r.id = s.recipe_id
            WHERE r.id IN ({placeholders})
            ORDER BY r.id, i.id, s.position ASC;
        """
        cursor.execute(sql_get_details, recipe_ids)
        all_rows = cursor.fetchall()
        
        recipes_dict = {}
        for row in all_rows:
            recipe_id = row['id']
            if recipe_id not in recipes_dict:
                cooking_time_id = row.get('cooking_time')
                recipes_dict[recipe_id] = {
                    'id': row['id'],
                    'title': row['title'],
                    'description': row['description'],
                    'cooking_time': COOKING_TIME_MAP.get(cooking_time_id),
                    'serving_for': row.get('serving_for'),
                    'ingredients': {}, 'steps': {}
                }
            
            ing_key = (row['ingredient_name'], row['quantity'])
            if row['ingredient_name'] and ing_key not in recipes_dict[recipe_id]['ingredients']:
                recipes_dict[recipe_id]['ingredients'][ing_key] = {
                    'name': row['ingredient_name'], 'quantity': row['quantity']
                }

            if row['step_memo'] and row['position'] not in recipes_dict[recipe_id]['steps']:
                recipes_dict[recipe_id]['steps'][row['position']] = {'memo': row['step_memo']}

        recipes_list = []
        for recipe_data in recipes_dict.values():
             final_recipe = {
                'id': recipe_data['id'],
                'title': recipe_data['title'],
                'description': recipe_data['description'],
                'cooking_time': recipe_data['cooking_time'],
                'serving_for': recipe_data['serving_for'],
                'ingredients': list(recipe_data['ingredients'].values()),
                'steps': [step[1] for step in sorted(recipe_data['steps'].items())]
            }
             recipes_list.append(final_recipe)

        return render_template('results.html', recipes=recipes_list, query=search_query)

    except mysql.connector.Error as err:
        print(f"検索処理中にエラーが発生しました: {err}", file=sys.stderr)
        return render_template('results.html', recipes=[], query=search_query, error="検索処理中にエラーが発生しました．")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# --- ▼▼▼ ここから基礎レシピ関連のルートを修正 ▼▼▼ ---

@app.route('/basic_search_home')
def basic_search_home():
    """基礎レシピの検索ページを表示する"""
    return render_template('basic_search_home.html')


@app.route('/basic_search', methods=['POST'])
def basic_search():
    """基礎レシピを検索し、結果を表示する"""
    search_query = request.form['query']
    
    try:
        with open('0_base_recipe.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_recipes = data.get('recipes', {})
        
        # 検索クエリがレシピ名（キー）に含まれるものをフィルタリング
        filtered_recipes = {
            recipe_name: details for recipe_name, details in all_recipes.items()
            if search_query in recipe_name
        }
        
        # 結果表示には basic_recipes.html を再利用する
        return render_template('basic_recipes.html',
                               query=search_query,
                               basic_recipes=filtered_recipes,
                               cooking_time_map=COOKING_TIME_MAP)
    except FileNotFoundError:
        return "基礎レシピファイル (0_base_recipe.json) が見つかりません．", 404
    except json.JSONDecodeError:
        return "基礎レシピファイル (0_base_recipe.json) の形式が正しくありません．", 500

# --- ▲▲▲ ここまで修正 ▲▲▲ ---


if __name__ == '__main__':
    app.run(debug=True)