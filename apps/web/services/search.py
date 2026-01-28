import random
import unicodedata
from core.database import get_synonyms, unify_keywords
from core.utils import build_recipes_dict, process_recipe_rows, COOKING_TIME_MAP

def _parse_query(cursor, search_query):
    normalized_query = search_query.replace('　', ' ')
    keywords = normalized_query.split()

    if not keywords:
        return []

    # 1. Ingredient Search Setup
    raw_inclusions = [k for k in keywords if not k.startswith('-')]
    # exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1] 

    # Unify inclusions
    unified_inclusions = unify_keywords(cursor, raw_inclusions)
    
    # Expand inclusions with synonyms
    inclusions = []
    for inc in unified_inclusions:
        syns = get_synonyms(cursor, inc)
        inclusions.append(syns)
    
    return inclusions

def search_recipes(cursor, search_query, start_id=1, limit=10):
    """
    一般レシピの検索処理 (Ingredient Search with Cursor Pagination)
    Returns: list of dicts (id, title, description, published_at), total_hit_check (bool)
    """
    # Use helper
    inclusions = _parse_query(cursor, search_query)
    
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
                    row = cursor.fetchone()
                    if row:
                        total_est += row['cnt']
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
            n.enerc_kcal, n.prot, n.fat, n.choavldf, n.fib, n.nacl_eq,

            rni.serving_size,
            rni.calories AS total_calories,
            rni.protein AS total_protein,
            rni.fat AS total_fat,
            rni.carbohydrates AS total_carbohydrates,
            rni.fiber AS total_fiber,
            rni.salt AS total_salt
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
    基礎レシピの検索処理 (Optimized)
    """
    normalized_query = search_query.replace('　', ' ')
    keywords = normalized_query.split()

    if not keywords:
        return []

    raw_inclusions = [k for k in keywords if not k.startswith('-')]
    exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1]
    
    if not raw_inclusions and not exclusions:
        return []

    target_ids = []

    if search_mode == 'ingredient':
        # --- Optimized Ingredient Search ---
        # Strategy: 
        # 1. Get (id, count) for each keyword.
        # 2. Intersect IDs (AND search).
        # 3. Sum counts for score.
        # 4. Sort and take top 5 IDs.
        
        from core.database import get_normalized_name
        
        # List of {recipe_id: count} dicts for each keyword
        keyword_matches = []
        
        if raw_inclusions:
            for keyword in raw_inclusions:
                normalized_name = get_normalized_name(cursor, keyword)
                if normalized_name:
                    cursor.execute("SELECT standard_recipe_id, count FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                else:
                    cursor.execute("SELECT standard_recipe_id, count FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                
                # Store as map: {id: count}
                matches = {row['standard_recipe_id']: row['count'] for row in cursor.fetchall()}
                keyword_matches.append(matches)
            
            if not keyword_matches:
                return []
                
            # Intersect IDs (AND logic)
            common_ids = set(keyword_matches[0].keys())
            for other_match in keyword_matches[1:]:
                common_ids &= set(other_match.keys())
            
            if not common_ids:
                return []

            # Calculate Score: Sum of counts for the matched keywords
            # (Higher count means the ingredient is more prominent in that recipe)
            scored_recipes = [] 
            for r_id in common_ids:
                score = 0
                for match_map in keyword_matches:
                    score += match_map.get(r_id, 0)
                scored_recipes.append({'id': r_id, 'score': score})
            
            # Sort by Score DESC
            scored_recipes.sort(key=lambda x: x['score'], reverse=True)
            
            # Exclusion Logic
            if exclusions:
                excluded_ids = set()
                for keyword in exclusions:
                    normalized_name = get_normalized_name(cursor, keyword)
                    if normalized_name:
                            cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name = %s", (normalized_name,))
                    else:
                            cursor.execute("SELECT DISTINCT standard_recipe_id FROM standard_recipe_ingredients WHERE ingredient_name LIKE %s", (f"%{keyword}%",))
                    for row in cursor.fetchall():
                        excluded_ids.add(row['standard_recipe_id'])
                
                scored_recipes = [r for r in scored_recipes if r['id'] not in excluded_ids]

            # Slice Top 5
            target_ids = [r['id'] for r in scored_recipes[:5]]
            
        else:
            # No inclusions provided in ingredient mode? Just return empty or all?
            # Original logic returned all IDs. But effectively we need inclusions for ingredient search.
             return []

    else: 
        # --- Optimized Recipe Name Search ---
        # Use LIKE and ORDER BY recipe_count DESC LIMIT 5 directly in SQL
        
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
            return []

        # Optimize: Sort by popularity (recipe_count) and LIMIT 5
        sql = f"SELECT id FROM standard_recipes WHERE {' AND '.join(conditions)} ORDER BY recipe_count DESC LIMIT 5"
        cursor.execute(sql, params)
        target_ids = [row['id'] for row in cursor.fetchall()]

    if not target_ids:
        return []

    # --- Fetch Details ONLY for Target IDs ---
    placeholders = ', '.join(['%s'] * len(target_ids))
    
    # 1. Basic Info
    sql_std = f"SELECT * FROM standard_recipes WHERE id IN ({placeholders})"
    cursor.execute(sql_std, target_ids)
    recipes_rows = cursor.fetchall()
    
    recipes_data = {}
    for row in recipes_rows:
        recipes_data[row['id']] = {
            'id': row['id'],
            'name': row['category_medium'],
            'recipe_count': row['recipe_count'],
            'cooking_time': [row['cooking_time']],
            'steps': {'average_steps': row['average_steps']},
            'standard_steps': [],
            'ingredient': {}
        }
        
    # 2. Ingredients
    sql_get_ingredients = f"SELECT * FROM standard_recipe_ingredients WHERE standard_recipe_id IN ({placeholders})"
    cursor.execute(sql_get_ingredients, target_ids)
    ingredients_rows = cursor.fetchall()

    for row in ingredients_rows:
        r_id = row['standard_recipe_id']
        if r_id in recipes_data:
            group = row['group_name'] or 'その他'
            name = row['ingredient_name']
            count = row['count']
            
            if name == 'all':
                continue

            if group not in recipes_data[r_id]['ingredient']:
                recipes_data[r_id]['ingredient'][group] = {'all': [0]}
            
            if name not in recipes_data[r_id]['ingredient'][group]:
                 recipes_data[r_id]['ingredient'][group][name] = [0]

            recipes_data[r_id]['ingredient'][group][name][0] = count
            recipes_data[r_id]['ingredient'][group][name][0] = count
            recipes_data[r_id]['ingredient'][group]['all'][0] += count

    # Sort categories by total count descending for each recipe
    for r_id in recipes_data:
        sorted_ingredients = dict(sorted(recipes_data[r_id]['ingredient'].items(), key=lambda item: item[1]['all'][0], reverse=True))
        recipes_data[r_id]['ingredient'] = sorted_ingredients
    # 3. Steps
    sql_get_steps = f"SELECT * FROM standard_recipe_steps WHERE standard_recipe_id IN ({placeholders}) ORDER BY count DESC"
    cursor.execute(sql_get_steps, target_ids)
    steps_rows = cursor.fetchall()

    for row in steps_rows:
        r_id = row['standard_recipe_id']
        if r_id in recipes_data:
            recipes_data[r_id]['standard_steps'].append({
                'food_name': row['food_name'],
                'action': row['action'],
                'count': row['count']
            })

    # Preserve Order of target_ids
    final_recipes_list = []
    for tid in target_ids:
        if tid in recipes_data:
            final_recipes_list.append((recipes_data[tid]['name'], recipes_data[tid]))
            
    return final_recipes_list

def get_standard_recipe_details(cursor, recipe_id):
    """
    基準レシピの詳細情報を取得する
    """
    # 1. Recipe Basic Info
    cursor.execute("SELECT * FROM standard_recipes WHERE id = %s", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        return None
        
    # Standardize structure to match search_standard_recipes for template compatibility
    recipe['steps'] = {'average_steps': recipe['average_steps']}
    recipe['cooking_time'] = [recipe['cooking_time']] # Expect list in template
    
    # 2. Ingredients
    cursor.execute("""
        SELECT group_name, ingredient_name, count 
        FROM standard_recipe_ingredients 
        WHERE standard_recipe_id = %s
        ORDER BY count DESC
    """, (recipe_id,))
    ingredients_rows = cursor.fetchall()
    
    # Structure ingredients by group (Same format as search_standard_recipes for template reuse)
    # Structure: { 'CategoryName': {'all': [total], 'onion': [10], ...} }
    ingredients_data = {}
    for row in ingredients_rows:
        grp = row['group_name'] or 'その他'
        name = row['ingredient_name']
        count = row['count']
        
        if name == 'all':
            continue
            
        if grp not in ingredients_data:
            ingredients_data[grp] = {'all': [0]}
            
        if name not in ingredients_data[grp]:
            ingredients_data[grp][name] = [0]
            
        ingredients_data[grp][name][0] = count
        ingredients_data[grp]['all'][0] += count        
    
    # Sort categories by total count descending
    sorted_ingredients_data = dict(sorted(ingredients_data.items(), key=lambda item: item[1]['all'][0], reverse=True))
    recipe['ingredient'] = sorted_ingredients_data # Use 'ingredient' key to match search results template

    # 3. Steps
    cursor.execute("""
        SELECT food_name, action, count
        FROM standard_recipe_steps
        WHERE standard_recipe_id = %s
        ORDER BY count DESC
    """, (recipe_id,))
    
    # Use 'standard_steps' key to match search results template
    recipe['standard_steps'] = [] 
    steps_rows = cursor.fetchall()
    for row in steps_rows:
        recipe['standard_steps'].append({
            'food_name': row['food_name'],
            'action': row['action'],
            'count': row['count']
        })
    
    return recipe
