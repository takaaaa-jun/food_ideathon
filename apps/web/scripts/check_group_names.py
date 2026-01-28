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
    cursor = conn.cursor()
    
    print("--- Check group_name in standard_recipe_ingredients ---")
    cursor.execute("SELECT DISTINCT group_name FROM standard_recipe_ingredients LIMIT 20")
    for row in cursor.fetchall():
        print(row)

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
