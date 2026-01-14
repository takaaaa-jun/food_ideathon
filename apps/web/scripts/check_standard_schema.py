
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

print("Checking Standard Recipes Tables...")

# Sizes
cursor.execute("SELECT COUNT(*) as c FROM standard_recipes")
print(f"standard_recipes count: {cursor.fetchone()['c']}")

cursor.execute("SELECT COUNT(*) as c FROM standard_recipe_ingredients")
print(f"standard_recipe_ingredients count: {cursor.fetchone()['c']}")

# Schema inspection (simulated DESCRIBE)
print("\n--- standard_recipes columns ---")
cursor.execute("DESCRIBE standard_recipes")
for row in cursor.fetchall():
    print(f"{row['Field']}: {row['Type']}")

print("\n--- standard_recipe_ingredients columns ---")
cursor.execute("DESCRIBE standard_recipe_ingredients")
for row in cursor.fetchall():
    print(f"{row['Field']}: {row['Type']}")
    
conn.close()
