from flask import Blueprint, render_template, request, current_app
import random
import os
from core.database import get_db_connection
from services.search import search_recipes, get_recipe_details

personal_bp = Blueprint('personal', __name__)

@personal_bp.route('/')
def index():
    """トップページを表示する"""
    return render_template('index.html')


@personal_bp.route('/search', methods=['POST'])
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
        
        return render_template('results.html', recipes=recipes_list, query=search_query)

    except Exception as e:
        current_app.logger.error(f"Search Error: {e}")
        return render_template('results.html', recipes=[], query=search_query, error=f"エラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

@personal_bp.route('/recipe/<int:recipe_id>')
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
        current_app.logger.error(f"Detail Error: {e}")
        return f"Error: {e}", 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@personal_bp.route('/search_supplement', methods=['GET'])
def search_supplement():
    return render_template('results.html', error="現在、不足分の栄養検索機能は停止しています。")
