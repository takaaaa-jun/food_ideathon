import os
import mysql.connector

# Load config
config_path = os.path.join(os.path.dirname(__file__), '../db_connection.cofg')
config_vars = {}
with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), {}, config_vars)

DB_CONFIG = config_vars['DB_CONFIG']

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    RECIPE_ID = 4
    GROUP_PREFIX = '17' # 17調味料...

    print(f"--- Checking Ingredients for Recipe ID {RECIPE_ID} in Group {GROUP_PREFIX} ---")
    
    query = """
        SELECT ingredient_name, count, group_name
        FROM standard_recipe_ingredients 
        WHERE standard_recipe_id = %s AND group_name LIKE %s
    """
    cursor.execute(query, (RECIPE_ID, f'{GROUP_PREFIX}%'))
    rows = cursor.fetchall()
    
    print(f"Total rows fetched: {len(rows)}")
    
    total_count = 0
    name_counts = {}
    
    for row in rows:
        name = row['ingredient_name']
        count = row['count']
        total_count += count
        
        if name in name_counts:
            name_counts[name].append(count)
        else:
            name_counts[name] = [count]
            
    print(f"Calculated Total Sum: {total_count}")
    print(f"Unique Ingredient Names: {len(name_counts)}")
    
    print("\n--- Checking for Duplicates ---")
    duplicates = {k: v for k, v in name_counts.items() if len(v) > 1}
    if duplicates:
        print(f"Found {len(duplicates)} duplicate ingredient names!")
        for name, counts in list(duplicates.items())[:10]:
            print(f"  {name}: {counts}")
    else:
        print("No duplicates found.")

    print("\n--- Top 10 Ingredients (by latest value/logic) ---")
    # Simulate the overwrite logic
    final_items = {}
    for row in rows:
        final_items[row['ingredient_name']] = row['count']
    
    sorted_items = sorted(final_items.items(), key=lambda x: x[1], reverse=True)[:10]
    for name, val in sorted_items:
        print(f"  {name}: {val}")

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
