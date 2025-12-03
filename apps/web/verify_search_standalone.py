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

# --- Helper Functions (Copied from app.py) ---
def get_synonyms(cursor, keyword):
    synonyms = {keyword}
    sql_get_synonyms = "SELECT synonym FROM synonym_dictionary WHERE normalized_name = %s"
    cursor.execute(sql_get_synonyms, (keyword,))
    for row in cursor.fetchall():
        synonyms.add(row['synonym'])

    sql_get_normalized = "SELECT normalized_name FROM synonym_dictionary WHERE synonym = %s"
    cursor.execute(sql_get_normalized, (keyword,))
    normalized_names = [row['normalized_name'] for row in cursor.fetchall()]
    
    for norm_name in normalized_names:
        synonyms.add(norm_name)
        cursor.execute(sql_get_synonyms, (norm_name,))
        for row in cursor.fetchall():
            synonyms.add(row['synonym'])
            
    return list(synonyms)

def unify_keywords(cursor, keywords):
    if not keywords:
        return []

    placeholders = ', '.join(['%s'] * len(keywords))
    sql = f"""
        SELECT synonym, normalized_name 
        FROM synonym_dictionary 
        WHERE synonym IN ({placeholders})
    """
    cursor.execute(sql, keywords)
    rows = cursor.fetchall()
    
    kw_to_norm = {row['synonym']: row['normalized_name'] for row in rows}
    
    seen_norms = set()
    for kw in keywords:
        if kw in kw_to_norm:
            seen_norms.add(kw_to_norm[kw])
            
    norm_to_best = {}
    if seen_norms:
        placeholders_norm = ', '.join(['%s'] * len(seen_norms))
        sql_best = f"""
            SELECT normalized_name, synonym, id
            FROM synonym_dictionary 
            WHERE normalized_name IN ({placeholders_norm})
            ORDER BY id ASC
        """
        cursor.execute(sql_best, list(seen_norms))
        best_rows = cursor.fetchall()
        
        for row in best_rows:
            norm = row['normalized_name']
            if norm not in norm_to_best:
                norm_to_best[norm] = row['synonym']
    
    unified_keywords = []
    processed_norms = set()
    
    for kw in keywords:
        if kw in kw_to_norm:
            norm = kw_to_norm[kw]
            if norm not in processed_norms:
                if norm in norm_to_best:
                    unified_keywords.append(norm_to_best[norm])
                processed_norms.add(norm)
        else:
            unified_keywords.append(kw)
            
    return unified_keywords

import random

# ... (Previous imports and config) ...

# ... (Helper functions: get_db_connection, get_synonyms, unify_keywords) ...

# --- Verification Logic ---
def verify_search(search_query):
    print(f"\n=== Verifying Search for: '{search_query}' ===")
    
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor(dictionary=True)

    normalized_query = search_query.replace('　', ' ')
    keywords = normalized_query.split()
    
    print(f"Original Keywords: {keywords}")

    # 1. Unify
    raw_inclusions = [k for k in keywords if not k.startswith('-')]
    exclusions = [k[1:] for k in keywords if k.startswith('-') and len(k) > 1]
    
    unified_inclusions = unify_keywords(cursor, raw_inclusions)
    print(f"Unified Keywords (Tags): {unified_inclusions}")
    
    # Simulate display query reconstruction
    display_query_parts = unified_inclusions + ['-' + exc for exc in exclusions]
    display_query = ' '.join(display_query_parts)
    print(f"Display Query (for UI): '{display_query}'")

    # 2. Expand
    inclusions = []
    for inc in unified_inclusions:
        syns = get_synonyms(cursor, inc)
        inclusions.append(syns)
        print(f"Expanded Synonyms for '{inc}': {syns}")

    # 3. Search Query Construction (Simulation)
    if inclusions:
        conditions = []
        all_params = []
        
        for syn_group in inclusions:
            placeholders = ', '.join(['%s'] * len(syn_group))
            conditions.append(f"SUM(CASE WHEN i.name IN ({placeholders}) THEN 1 ELSE 0 END) > 0")
            all_params.extend(syn_group)
        
        having_clause = " AND ".join(conditions)
        
        all_synonyms_flat = [item for sublist in inclusions for item in sublist]
        placeholders_all = ', '.join(['%s'] * len(all_synonyms_flat))
        
        # Get all matching recipes first (with attribute)
        sql_inclusions = f"""
            SELECT i.recipe_id, r.title, r.attribute
            FROM ingredients AS i
            JOIN recipes AS r ON i.recipe_id = r.id
            WHERE i.name IN ({placeholders_all})
            GROUP BY i.recipe_id
            HAVING {having_clause}
            LIMIT 100
        """
        params_inc = all_synonyms_flat + all_params
        
        print("\nExecuting SQL...")
        cursor.execute(sql_inclusions, params_inc)
        candidates = cursor.fetchall()
        print(f"Total Candidates Found (Limit 100): {len(candidates)}")
        
        if not candidates:
            print("No recipes found.")
            cursor.close()
            conn.close()
            return

        # Debug: Print available attributes
        available_attributes_raw = set(row['attribute'] for row in candidates)
        print(f"Available Attributes in DB (Raw): {available_attributes_raw}")

        # Normalize attributes in candidates (convert full-width to half-width)
        import unicodedata
        for row in candidates:
            if row['attribute']:
                row['attribute'] = unicodedata.normalize('NFKC', row['attribute'])

        # 4. Random Attribute Selection

        attributes = ['cookpad', 'rakuten']
        selected_attribute = random.choice(attributes)
        print(f"Selected Attribute: {selected_attribute}")
        
        # Filter by attribute
        # Check if selected attribute has results
        available_attributes = set(row['attribute'] for row in candidates)
        print(f"Available Attributes (Normalized): {available_attributes}")

        
        # Strict filtering logic verification
        valid_attributes = {'cookpad', 'rakuten'}
        available_valid_attributes = available_attributes.intersection(valid_attributes)
        
        if available_valid_attributes:
            if selected_attribute not in available_valid_attributes:
                selected_attribute = list(available_valid_attributes)[0]
                print(f"Switched Attribute to: {selected_attribute} (original choice not available)")
        else:
             print("No valid attributes (cookpad/rakuten) found in candidates.")
             # In app.py, this results in empty list
             selected_attribute = "NONE"

        final_candidates = [row for row in candidates if row['attribute'] == selected_attribute]
        print(f"Candidates after attribute filter: {len(final_candidates)}")
        
        # 5. Limit to 20, Shuffle, Limit to 10
        recipe_ids_20 = final_candidates[:20]
        random.shuffle(recipe_ids_20)
        final_results = recipe_ids_20[:10]
        
        print(f"Final Display (Random 10 from top 20):")
        for row in final_results:
            print(f" - ID: {row['recipe_id']}, Title: {row['title']}, Attribute: {row['attribute']}")
            
    else:
        print("No inclusions to search.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    # Test cases
    verify_search("玉葱")
    verify_search("たまねぎ")
    verify_search("玉ねぎ")
    verify_search("玉葱 たまねぎ") # Should unify to one tag
