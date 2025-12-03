import os
import sys
import mysql.connector

# --- Database Connection ---
config_path = os.path.join(os.path.dirname(__file__), 'db_connection.cofg')
config_vars = {}
with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), {}, config_vars)

DB_CONFIG = config_vars['DB_CONFIG']

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}", file=sys.stderr)
        return None

def get_normalized_name(cursor, keyword):
    # 1. Check if keyword is already a normalized_name
    sql_check_norm = "SELECT normalized_name FROM synonym_dictionary WHERE normalized_name = %s LIMIT 1"
    cursor.execute(sql_check_norm, (keyword,))
    if cursor.fetchone():
        return keyword

    # 2. Check if keyword is a synonym
    sql_get_norm = "SELECT normalized_name FROM synonym_dictionary WHERE synonym = %s LIMIT 1"
    cursor.execute(sql_get_norm, (keyword,))
    row = cursor.fetchone()
    if row:
        return row['normalized_name']
        
    return None

def verify_standard_search(search_query, search_mode='ingredient'):
    print(f"\n=== Verifying Standard Search ({search_mode}) for: '{search_query}' ===")
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor(dictionary=True)

    normalized_query = search_query.replace('　', ' ')
    keywords = normalized_query.split()
    
    print(f"Keywords: {keywords}")

    # Separate inclusions and exclusions
    raw_inclusions = [k for k in keywords if not k.startswith('-')]
    exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1]
    
    print(f"Inclusions: {raw_inclusions}")
    print(f"Exclusions: {exclusions}")

    recipe_ids = []

    if search_mode == 'ingredient':
        candidate_ids_sets = []
        
        # Inclusions
        if raw_inclusions:
            for keyword in raw_inclusions:
                normalized_name = get_normalized_name(cursor, keyword)
                print(f"  Keyword '{keyword}' -> Normalized: '{normalized_name}'")
                
                if normalized_name:
                    cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                else:
                    cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                
                ids = {row['standard_recipe_id'] for row in cursor.fetchall()}
                print(f"    Found {len(ids)} recipes")
                candidate_ids_sets.append(ids)
            
            if candidate_ids_sets:
                common_ids = candidate_ids_sets[0]
                for other_ids in candidate_ids_sets[1:]:
                    common_ids &= other_ids
                recipe_ids = list(common_ids)
            else:
                recipe_ids = []
        else:
            # No inclusions, get all IDs (limit for safety in verification)
            cursor.execute("SELECT id FROM standard_recipes LIMIT 100")
            recipe_ids = [row['id'] for row in cursor.fetchall()]

        print(f"  IDs after inclusions: {len(recipe_ids)}")

        # Exclusions
        if recipe_ids and exclusions:
            excluded_ids = set()
            for keyword in exclusions:
                normalized_name = get_normalized_name(cursor, keyword)
                print(f"  Exclusion '{keyword}' -> Normalized: '{normalized_name}'")
                
                if normalized_name:
                        cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                else:
                        cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                
                for row in cursor.fetchall():
                    excluded_ids.add(row['standard_recipe_id'])
            
            print(f"    Found {len(excluded_ids)} excluded recipes")
            recipe_ids = [rid for rid in recipe_ids if rid not in excluded_ids]

    else: # recipe search
        conditions = []
        params = []
        
        if raw_inclusions:
            for keyword in raw_inclusions:
                conditions.append("category_medium LIKE %s")
                params.append(f"%{keyword}%")
        
        if exclusions:
            for keyword in exclusions:
                conditions.append("category_medium NOT LIKE %s")
                params.append(f"%{keyword}%")

        if conditions:
            where_clause = " AND ".join(conditions)
            sql = f"SELECT id FROM standard_recipes WHERE {where_clause}"
            cursor.execute(sql, tuple(params))
            recipe_ids = [row['id'] for row in cursor.fetchall()]
        else:
            recipe_ids = []

    print(f"Final Result Count: {len(recipe_ids)}")
    
    if recipe_ids:
        # Get names for first 5
        placeholders = ','.join(['%s'] * len(recipe_ids[:5]))
        cursor.execute(f"SELECT id, category_medium FROM standard_recipes WHERE id IN ({placeholders})", recipe_ids[:5])
        for row in cursor.fetchall():
            print(f" - [{row['id']}] {row['category_medium']}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    # Test 1: Ingredient Search (Synonym)
    verify_standard_search("玉ねぎ", 'ingredient')
    verify_standard_search("たまねぎ", 'ingredient') # Should match same as above
    
    # Test 2: Ingredient Search (AND)
    verify_standard_search("玉ねぎ 人参", 'ingredient')
    
    # Test 3: Ingredient Search (NOT)
    verify_standard_search("玉ねぎ -人参", 'ingredient')
    
    # Test 4: Recipe Search
    verify_standard_search("カレー", 'recipe')
    verify_standard_search("カレー -ドライ", 'recipe')
