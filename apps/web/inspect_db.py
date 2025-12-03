import os
import mysql.connector

# Load config
config_path = os.path.join(os.path.dirname(__file__), 'db_connection.cofg')
config_vars = {}
with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), {}, config_vars)

DB_CONFIG = config_vars['DB_CONFIG']

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    # Check standard_recipe_ingredients
    cursor.execute("DESCRIBE standard_recipe_ingredients")
    print("\nColumns in standard_recipe_ingredients:")
    for col in cursor.fetchall():
        print(col)

    cursor.execute("SELECT ingredient_name FROM standard_recipe_ingredients LIMIT 10")
    print("\nSample ingredient_names in standard_recipe_ingredients:")
    for row in cursor.fetchall():
        print(row)

    # Check for multiple synonyms for a normalized_name
    print("\nChecking for multiple synonyms:")
    cursor.execute("SELECT normalized_name, COUNT(*) as c FROM synonym_dictionary GROUP BY normalized_name HAVING c > 1 LIMIT 5")
    for row in cursor.fetchall():
        print(f"Normalized: {row[0]}, Count: {row[1]}")
        cursor.execute(f"SELECT synonym FROM synonym_dictionary WHERE normalized_name = '{row[0]}'")
        print(f"  Synonyms: {[r[0] for r in cursor.fetchall()]}")

    # Check if normalized_name matches standard_recipe_ingredients
    print("\nChecking overlap between synonym_dictionary.normalized_name and standard_recipe_ingredients.ingredient_name:")
    cursor.execute("""
        SELECT s.ingredient_name 
        FROM standard_recipe_ingredients s
        JOIN synonym_dictionary sd ON s.ingredient_name = sd.normalized_name
        LIMIT 5
    """)
    print("Matches found:")
    for row in cursor.fetchall():
        print(row)


except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
