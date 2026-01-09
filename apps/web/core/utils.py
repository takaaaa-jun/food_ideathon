import logging
import datetime
import os

# --- ログ設定ヘルパー ---
def jst_converter(*args):
    """ログの時刻をJSTにする"""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).timetuple()

# --- 定数 ---
COOKING_TIME_MAP = {
    1: '5分以内', 2: '約10分', 3: '約15分',
    4: '約30分', 5: '約1時間', 6: '1時間以上'
}

STANDARDS = {
    'energy': 734,
    'protein': 31,
    'fat': 21,
    'carbs': 106
}

def process_recipe_rows(recipes_dict):
    """
    DBから取得したレシピ情報の辞書を、表示用のリスト形式に変換・計算する
    """
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

def build_recipes_dict(all_rows):
    """
    DBの検索結果行（JOINされた情報）から、レシピIDをキーとする辞書を構築する
    """
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
        
        # 軽量版（検索時）では結合情報がない場合があるためチェック
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

        if row.get('step_memo') and row.get('position') is not None and row['position'] not in recipes_dict[recipe_id]['steps']:
            recipes_dict[recipe_id]['steps'][row['position']] = {'memo': row['step_memo']}
    return recipes_dict
