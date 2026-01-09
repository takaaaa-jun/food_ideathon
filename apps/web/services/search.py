import random
import unicodedata
from core.database import get_synonyms, unify_keywords
from core.utils import build_recipes_dict, process_recipe_rows, COOKING_TIME_MAP

def search_recipes(cursor, search_query, start_id=1, limit=10):
    """
    一般レシピの検索処理 (Ingredient Search with Cursor Pagination)
    Returns: list of dicts (id, title, description, published_at), total_hit_check (bool)
    """
    normalized_query = search_query.replace('　', ' ')
    keywords = normalized_query.split()

    if not keywords:
        return []

    # 1. Ingredient Search Setup
    raw_inclusions = [k for k in keywords if not k.startswith('-')]
    # exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1] # Exclusions might be complex with cursor, ignore for now or apply in WHERE

    # Unify inclusions
    unified_inclusions = unify_keywords(cursor, raw_inclusions)
    
    # Expand inclusions with synonyms
    inclusions = []
    for inc in unified_inclusions:
        syns = get_synonyms(cursor, inc)
        inclusions.append(syns)

    candidate_recipes = []
    
    if inclusions:
        # Build Query with Cursor (recipe_id >= start_id)
        
        # Deferred Join Optimization:
        # 1. Fetch recipe_ids from ingredients table (using covering index)
        # 2. Fetch recipe details for those IDs
        
        found_ids = []
        
        if len(inclusions) == 1:
            # Single Ingredient Group
            all_synonyms_flat = inclusions[0]
            
            # Scatter-Gather Optimization:
            # IN (...) prevents using index for sorting.
            # Run separate query for each synonym and merge.
            
            gathered_ids = []
            
            for syn in all_synonyms_flat:
                # Use covering index (name, recipe_id)
                # This is an instant Range Scan.
                sql = """
                    SELECT recipe_id
                    FROM ingredients
                    WHERE name = %s
                    AND recipe_id >= %s
                    ORDER BY recipe_id ASC
                    LIMIT %s
                """
                # Fetch limit*2 to be safe for deduplication later, though usually 10 is enough per synonym.
                cursor.execute(sql, (syn, start_id, limit))
                gathered_ids.extend([row['recipe_id'] for row in cursor.fetchall()])
            
            # Sort and Deduplicate
            gathered_ids.sort()
            found_ids = list(dict.fromkeys(gathered_ids))[:limit]
            
        else:
            # Unified Paged Strategy (Paged Driver + Vectorized Verification)
            
            # 1. Rarest First Selection
            sorted_inclusions = []
            for group in inclusions:
                total_est = 0
                for syn in group:
                    cursor.execute("SELECT count(*) as cnt FROM ingredients WHERE name = %s", (syn,))
                    total_est += cursor.fetchone()['cnt']
                sorted_inclusions.append({'group': group, 'count': total_est})
            
            sorted_inclusions.sort(key=lambda x: x['count'])
            
            driver_synonyms = sorted_inclusions[0]['group']
            other_groups = [item['group'] for item in sorted_inclusions[1:]]
            
            # Helper: Verify batch
            def verify_batch(candidate_ids, group_synonyms):
                if not candidate_ids:
                    return set()
                placeholders_ids = ', '.join(['%s'] * len(candidate_ids))
                placeholders_names = ', '.join(['%s'] * len(group_synonyms))
                sql = f"""
                    SELECT DISTINCT recipe_id 
                    FROM ingredients 
                    WHERE name IN ({placeholders_names}) 
                    AND recipe_id IN ({placeholders_ids})
                """
                params = group_synonyms + candidate_ids
                cursor.execute(sql, params)
                return {row['recipe_id'] for row in cursor.fetchall()}

            found_ids = []
            current_start_id = start_id
            max_scan_candidates = 10000 
            scanned_count = 0
            FETCH_BATCH_SIZE = 1000
            
            while len(found_ids) < limit and scanned_count < max_scan_candidates:
                candidates = []
                for syn in driver_synonyms:
                    sql = """
                        SELECT recipe_id
                        FROM ingredients
                        WHERE name = %s
                        AND recipe_id >= %s
                        ORDER BY recipe_id ASC
                        LIMIT %s
                    """
                    cursor.execute(sql, (syn, current_start_id, FETCH_BATCH_SIZE))
                    candidates.extend([row['recipe_id'] for row in cursor.fetchall()])
                
                if not candidates:
                    break
                    
                candidates = sorted(list(set(candidates)))
                candidates = candidates[:FETCH_BATCH_SIZE] # Ensure we adhere to batch size logic
                
                last_candidate_id = candidates[-1]
                scanned_count += len(candidates)
                
                current_matches = set(candidates)
                for grp in other_groups:
                    if not current_matches:
                        break
                    current_matches &= verify_batch(list(current_matches), grp)
                
                for mid in sorted(list(current_matches)):
                    if mid not in found_ids:
                        found_ids.append(mid)
                    if len(found_ids) >= limit:
                        break
                        
                current_start_id = last_candidate_id + 1
            
        if not found_ids:
            return []
            
        placeholders_ids = ', '.join(['%s'] * len(found_ids))
        sql_details = f"""
            SELECT id, title, description, published_at 
            FROM recipes 
            WHERE id IN ({placeholders_ids})
            ORDER BY FIELD(id, {placeholders_ids})
        """
        cursor.execute(sql_details, found_ids + found_ids) 
        candidate_recipes = cursor.fetchall()

    return candidate_recipes


def get_recipe_details(cursor, recipe_id):
    """
    特定レシピの詳細情報を取得する
    """
    sql_get_details = """
        SELECT
            r.id, r.title, r.description,
            r.cooking_time, r.serving_for, r.published_at, r.attribute,
            i.id AS ingredient_id,
            i.name AS ingredient_name, i.quantity,
            s.position, s.memo AS step_memo,
            
            ist.normalized_name,
            iu.normalized_quantity,
            n.enerc_kcal, n.prot, n.fat, n.choavldf, n.fib,

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
        WHERE r.id = %s
        ORDER BY i.id, s.position ASC;
    """
    
    cursor.execute(sql_get_details, (recipe_id,))
    rows = cursor.fetchall()
    
    if not rows:
        return None

    recipes_dict = build_recipes_dict(rows)
    recipes_list = process_recipe_rows(recipes_dict)
    
    if recipes_list:
        return recipes_list[0]
    return None



def search_standard_recipes(cursor, search_query, search_mode='recipe'):
    """
    基礎レシピの検索処理
    """
    normalized_query = search_query.replace('　', ' ')
    keywords = normalized_query.split()

    if not keywords:
        return []

    raw_inclusions = [k for k in keywords if not k.startswith('-')]
    exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1]
    
    if not raw_inclusions and not exclusions:
        return []

    recipe_ids = []

    if search_mode == 'ingredient':
        # --- Ingredient Search Code ---
        candidate_ids_sets = []
        if raw_inclusions:
            for keyword in raw_inclusions:
                # Use get_normalized_name imported from database? No, need to pass cursor.
                # Since get_normalized_name is in database.py, we imported it.
                from core.database import get_normalized_name
                
                normalized_name = get_normalized_name(cursor, keyword)
                if normalized_name:
                    cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                else:
                    cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                
                ids = {row['standard_recipe_id'] for row in cursor.fetchall()}
                candidate_ids_sets.append(ids)
            
            if candidate_ids_sets:
                common_ids = candidate_ids_sets[0]
                for other_ids in candidate_ids_sets[1:]:
                    common_ids &= other_ids
                recipe_ids = list(common_ids)
            else:
                recipe_ids = []
        else:
             cursor.execute("SELECT id FROM standard_recipes")
             recipe_ids = [row['id'] for row in cursor.fetchall()]

        # Exclusions
        if recipe_ids and exclusions:
            from core.database import get_normalized_name
            excluded_ids = set()
            for keyword in exclusions:
                normalized_name = get_normalized_name(cursor, keyword)
                if normalized_name:
                        cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                else:
                        cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                
                for row in cursor.fetchall():
                    excluded_ids.add(row['standard_recipe_id'])
            
            recipe_ids = [rid for rid in recipe_ids if rid not in excluded_ids]

    else: 
        # --- Recipe Name (Category Medium) Search ---
        # Note: standard_recipes does not have FULLTEXT index, so we use LIKE.
        
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
        
        if not conditions:
            return [] # Should have been caught, but safety

        sql = f"SELECT id FROM standard_recipes WHERE {' AND '.join(conditions)}"
        cursor.execute(sql, params)
        recipe_ids = [row['id'] for row in cursor.fetchall()]

    if not recipe_ids:
        return []

    # Fetch details
    placeholders = ', '.join(['%s'] * len(recipe_ids))
    sql_std = f"""
        SELECT * FROM standard_recipes WHERE id IN ({placeholders})
    """
    cursor.execute(sql_std, recipe_ids)
    # Return raw dicts for now as expected by template
    return cursor.fetchall()
