import os
import csv
import logging

# --- 主食（固定値）の設定 ---
STAPLE_FOODS = [
    {
        'id': 'staple_1',
        'name': '白米茶碗1杯',
        'unit': '杯',
        'energy': 234,
        'protein': 3.75,
        'fat': 0.45,
        'carbs': 54.15,
        'fiber': 2.25,
        'salt': 0.0
    },
    {
        'id': 'staple_2',
        'name': '食パン6枚切り1枚',
        'unit': '枚',
        'energy': 148.8,
        'protein': 5.34,
        'fat': 2.46,
        'carbs': 26.46,
        'fiber': 2.52,
        'salt': 0.72
    },
    {
        'id': 'staple_3',
        'name': '味噌汁お碗1杯',
        'unit': '杯',
        'energy': 59,
        'protein': 5.2,
        'fat': 3.1,
        'carbs': 3.6,
        'fiber': 1.0,
        'salt': 1.5
    },
    {
        'id': 'staple_4',
        'name': 'コーンスープ1杯',
        'unit': '杯',
        'energy': 81,
        'protein': 1.54,
        'fat': 2.6,
        'carbs': 12.81,
        'fiber': 1.0, 
        'salt': 1.0
    }
]

def load_nutrition_data(data_dir):
    csv_path = os.path.join(data_dir, 'nutrition_ex.csv')
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
                if len(row) < 10: continue 
                ingredients.append({
                    'id': row[1],
                    'name': row[3],
                    'energy': safe_float(row[4]),
                    'protein': safe_float(row[5]),
                    'fat': safe_float(row[6]),
                    'carbs': safe_float(row[7]),
                    'fiber': safe_float(row[8]),
                    'salt': safe_float(row[9])
                })
        return ingredients
    except Exception as e:
        logging.error(f"Error reading csv: {e}")
        return []
