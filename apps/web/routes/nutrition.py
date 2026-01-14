from flask import Blueprint, render_template, current_app
import os
from services.nutrition import STAPLE_FOODS, load_nutrition_data

nutrition_bp = Blueprint('nutrition', __name__)

@nutrition_bp.route('/nutrition_calculation')
def nutrition_calculation():
    """栄養計算ページを表示する"""
    # Assuming app.py is in apps/web, root_path is apps/web.
    data_dir = os.path.join(current_app.root_path, 'data')
    
    ingredients = load_nutrition_data(data_dir)
    
    if not ingredients:
         return render_template('nutrition_calculation.html', error="データの読み込みに失敗しました。", ingredients=[], staple_foods=STAPLE_FOODS)

    return render_template('nutrition_calculation.html', ingredients=ingredients, staple_foods=STAPLE_FOODS)
