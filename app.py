import sys
import mysql.connector
from flask import Flask, render_template, request

# Flaskアプリケーションの初期化
app = Flask(__name__)

# --- データベース接続情報 ---
DB_CONFIG = {
    'user': 'root',
    'password': 'Gdtkjnuaa1024',
    'host': '127.0.0.1',
    'database': 'foodapp'
}

# --- カテゴリ分類マップ ---
CATEGORY_MAP = {
    '01': '穀類', '02': 'いも及びでん粉類', '03': '砂糖及び甘味類',
    '04': '豆類', '05': '種実類', '06': '野菜類',
    '07': '果実類', '08': 'きのこ類', '09': '藻類',
    '10': '魚介類', '11': '肉類', '12': '卵類',
    '13': '乳類', '14': '油脂類', '15': '菓子類',
    '16': 'し好飲料類', '17': '調味料及び香辛料類', '18': '調理済み流通食品類'
}

# --- ▼▼▼ 栄養素計算用のカラムリストを追加 ▼▼▼ ---
VITAMIN_COLUMNS_MG = ['TOCPHA', 'THIA', 'RIBF', 'NIA', 'VITB6A', 'PANTAC', 'VITC']
VITAMIN_COLUMNS_UG = ['VITA_RAE', 'VITD', 'VITK', 'VITB12', 'FOL', 'BIOT']
MINERAL_COLUMNS_MG = ['NA', 'K', 'CA', 'MG', 'P', 'FE', 'ZN', 'CU', 'MN']
MINERAL_COLUMNS_UG = ['IOD', 'SE', 'CR', 'MO']
# --- ▲▲▲ ここまで追加 ▲▲▲ ---


def get_db_connection():
    # ... (変更なし) ...
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"データベース接続エラー: {err}", file=sys.stderr)
        return None

@app.route('/')
def index():
    # ... (変更なし) ...
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form['query']
    search_mode = request.form.get('search_mode', 'ingredient')
    
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            search_pattern = f"%{search_query}%"

            if search_mode == 'basic':
                # (材料の頻度集計クエリは変更なし)
                sql_freq = """
                    SELECT norm.normalized_name, n.group AS category_group, COUNT(norm.normalized_name) AS frequency
                    FROM recipes AS r
                    JOIN ingredients AS i ON r.id = i.recipe_id
                    JOIN ingredients_structured_ver05_normalized AS norm ON i.id = norm.ingredients_id
                    LEFT JOIN nutritions AS n ON norm.normalized_name = n.name COLLATE utf8mb4_general_ci
                    WHERE r.title LIKE %s AND norm.normalized_name IS NOT NULL
                    GROUP BY norm.normalized_name, n.group ORDER BY frequency DESC;
                """
                cursor.execute(sql_freq, (search_pattern,))
                all_ingredients = cursor.fetchall()
                
                # (カテゴリ分類ロジックは変更なし)
                grouped_ingredients = {}
                for ing in all_ingredients:
                    category_name = 'その他'
                    category_group = ing.get('category_group')
                    if category_group:
                        category_code = str(category_group).zfill(2)
                        category_name = CATEGORY_MAP.get(category_code, 'その他')
                    if category_name not in grouped_ingredients:
                        grouped_ingredients[category_name] = []
                    grouped_ingredients[category_name].append({'name': ing['normalized_name'], 'frequency': ing['frequency']})
                
                # --- ▼▼▼ 栄養計算ロジックを追加 ▼▼▼ ---
                nutrition_totals = None
                top_ingredients_list = []
                if grouped_ingredients:
                    # 各カテゴリのトップ1材料を抽出
                    for category, ingredients in grouped_ingredients.items():
                        if ingredients:
                            top_ingredients_list.append(ingredients[0]) # 頻度順なので先頭がトップ

                    top_ingredient_names = [ing['name'] for ing in top_ingredients_list]

                    if top_ingredient_names:
                        # 栄養素計算に必要なカラムを全て結合
                        all_nutrient_columns = ['PROT', 'FAT', 'CHOAVLDF', 'FIB'] + VITAMIN_COLUMNS_MG + VITAMIN_COLUMNS_UG + MINERAL_COLUMNS_MG + MINERAL_COLUMNS_UG
                        
                        placeholders = ', '.join(['%s'] * len(top_ingredient_names))
                        sql_nutrition = f"SELECT {', '.join(all_nutrient_columns)} FROM nutritions WHERE name IN ({placeholders})"
                        cursor.execute(sql_nutrition, top_ingredient_names)
                        nutrition_data = cursor.fetchall()

                        # 栄養素を合計
                        nutrition_totals = {'protein': 0, 'fat': 0, 'carbs': 0, 'vitamin': 0, 'mineral': 0}
                        for row in nutrition_data:
                            nutrition_totals['protein'] += row.get('PROT', 0) or 0
                            nutrition_totals['fat'] += row.get('FAT', 0) or 0
                            nutrition_totals['carbs'] += (row.get('CHOAVLDF', 0) or 0) + (row.get('FIB', 0) or 0)
                            # ビタミン合計 (μgはmgに変換)
                            for col in VITAMIN_COLUMNS_MG: nutrition_totals['vitamin'] += row.get(col, 0) or 0
                            for col in VITAMIN_COLUMNS_UG: nutrition_totals['vitamin'] += (row.get(col, 0) or 0) / 1000.0
                            # ミネラル合計 (μgはmgに変換)
                            for col in MINERAL_COLUMNS_MG: nutrition_totals['mineral'] += row.get(col, 0) or 0
                            for col in MINERAL_COLUMNS_UG: nutrition_totals['mineral'] += (row.get(col, 0) or 0) / 1000.0
                # --- ▲▲▲ ここまで栄養計算ロジック ▲▲▲ ---
                
                cursor.close()
                conn.close()
                return render_template('basic_recipe_results.html', 
                                       grouped_ingredients=grouped_ingredients, 
                                       query=search_query,
                                       top_ingredients=top_ingredients_list,
                                       nutrition_totals=nutrition_totals)
            
            # (既存のレシピ名・材料名検索の処理は変更なし)
            # ...
            recipes_dict = {}
            if search_mode == 'ingredient':
                sql_get_ids = "SELECT DISTINCT recipe_id FROM ingredients WHERE name LIKE %s LIMIT 10"
                cursor.execute(sql_get_ids, (search_pattern,))
                recipe_ids = [row['recipe_id'] for row in cursor.fetchall()]
            elif search_mode == 'title':
                sql_get_ids = "SELECT id FROM recipes WHERE title LIKE %s LIMIT 10"
                cursor.execute(sql_get_ids, (search_pattern,))
                recipe_ids = [row['id'] for row in cursor.fetchall()]
            else:
                recipe_ids = []

            if not recipe_ids:
                cursor.close()
                conn.close()
                return render_template('results.html', recipes=[], query=search_query, search_mode=search_mode)

            placeholders = ', '.join(['%s'] * len(recipe_ids))
            
            sql_get_details = f"""
                SELECT
                    r.id, r.title, r.description,
                    i.id AS ingredient_id, i.name AS original_ingredient_name, i.quantity,
                    s.position, s.memo AS step_memo,
                    norm.normalized_name,
                    n.group AS category_group
                FROM recipes AS r
                LEFT JOIN ingredients AS i ON r.id = i.recipe_id
                LEFT JOIN steps AS s ON r.id = s.recipe_id
                LEFT JOIN ingredients_structured_ver05_normalized AS norm ON i.id = norm.ingredients_id
                LEFT JOIN nutritions AS n ON norm.normalized_name = n.name COLLATE utf8mb4_general_ci
                WHERE r.id IN ({placeholders})
                ORDER BY r.id, i.id, s.position ASC;
            """
            cursor.execute(sql_get_details, recipe_ids)
            
            for row in cursor.fetchall():
                recipe_id = row['id']
                if recipe_id not in recipes_dict:
                    recipes_dict[recipe_id] = {'id': row['id'], 'title': row['title'], 'description': row['description'], 'ingredients': {}, 'steps': {}}
                
                ingredient_id = row['ingredient_id']
                if ingredient_id and ingredient_id not in recipes_dict[recipe_id]['ingredients']:
                    recipes_dict[recipe_id]['ingredients'][ingredient_id] = {'original_name': row['original_ingredient_name'], 'quantity': row['quantity'], 'normalized_name': row['normalized_name'], 'category_group': row.get('category_group')}
                
                if row['step_memo'] and row['position'] not in recipes_dict[recipe_id]['steps']:
                    recipes_dict[recipe_id]['steps'][row['position']] = { 'memo': row['step_memo'] }
            
            cursor.close()

            recipes_list = []
            for recipe_data in recipes_dict.values():
                grouped_ingredients = {}
                for ing in recipe_data['ingredients'].values():
                    category_name = 'その他'
                    category_group = ing.get('category_group')
                    if category_group:
                        category_code = str(category_group).zfill(2)
                        category_name = CATEGORY_MAP.get(category_code, 'その他')
                    if category_name not in grouped_ingredients:
                        grouped_ingredients[category_name] = []
                    grouped_ingredients[category_name].append(ing)

                final_recipe = {'id': recipe_data['id'], 'title': recipe_data['title'], 'description': recipe_data['description'], 'grouped_ingredients': grouped_ingredients, 'steps': [step[1] for step in sorted(recipe_data['steps'].items())]}
                recipes_list.append(final_recipe)

            return render_template('results.html', recipes=recipes_list, query=search_query, search_mode=search_mode)

    except mysql.connector.Error as err:
        print(f"検索処理中にエラーが発生しました: {err}", file=sys.stderr)
        if search_mode == 'basic':
            return render_template('basic_recipe_results.html', grouped_ingredients={}, query=search_query)
        else:
            return render_template('results.html', recipes=[], query=search_query, search_mode=search_mode)
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)

