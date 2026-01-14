from flask import Blueprint, render_template, request, current_app
from core.database import get_db_connection
from core.utils import COOKING_TIME_MAP
from services.search import search_standard_recipes, get_standard_recipe_details

standard_bp = Blueprint('standard', __name__)

@standard_bp.route('/standard_search_home')
def standard_search_home():
    """基礎レシピの検索ページを表示する"""
    return render_template('standard_search_home.html')


@standard_bp.route('/standard_search', methods=['POST'])
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
        current_app.logger.error(f"Error in standard_search: {e}")
        return render_template('standard_recipes.html', query=search_query, error="検索に失敗しました", basic_recipes=[], cooking_time_map={})
    finally:
         if conn and conn.is_connected():
            conn.close()


@standard_bp.route('/standard_recipe/<int:recipe_id>')
def standard_recipe_detail(recipe_id):
    """基準レシピ詳細を表示する"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        recipe = get_standard_recipe_details(cursor, recipe_id)
        
        if not recipe:
            return "Recipe not found", 404
            
        return render_template('standard_recipe_detail.html', recipe=recipe, cooking_time_map=COOKING_TIME_MAP)
    except Exception as e:
        current_app.logger.error(f"Standard Detail Error: {e}")
        return f"Error: {e}", 500
    finally:
        if conn and conn.is_connected():
            conn.close()
