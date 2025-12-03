
import os
import sys
import mysql.connector

# DB Config
config_path = os.path.join('/srv/foodapp/apps/web', 'db_connection.cofg')
config_vars = {}
with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), {}, config_vars)

DB_CONFIG = config_vars['DB_CONFIG']

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    print("--- standard_recipe_ingredients sample ---")
    cursor.execute("SELECT ingredient_name FROM standard_recipe_ingredients LIMIT 5")
    for row in cursor.fetchall():
        print(row['ingredient_name'])

    print("\n--- synonym_dictionary sample ---")
    cursor.execute("SELECT synonym, normalized_name FROM synonym_dictionary LIMIT 5")
    for row in cursor.fetchall():
        print(f"{row['synonym']} -> {row['normalized_name']}")

except Exception as e:
    print(e)
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
