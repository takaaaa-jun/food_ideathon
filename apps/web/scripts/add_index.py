import time
import mysql.connector
from core.database import get_db_connection

def add_index():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Checking existing indexes...")
    cursor.execute("SHOW INDEX FROM ingredients WHERE Key_name = 'idx_ingredients_name_recipe_id'")
    if cursor.fetchone():
        print("Index 'idx_ingredients_name_recipe_id' already exists.")
    else:
        print("Adding index 'idx_ingredients_name_recipe_id' to ingredients table...")
        start_time = time.time()
        try:
            # Adding composite index on (name, recipe_id)
            # This helps: WHERE name='...' AND recipe_id >= X ORDER BY recipe_id
            cursor.execute("CREATE INDEX idx_ingredients_name_recipe_id ON ingredients (name, recipe_id)")
            conn.commit()
            print(f"Index added successfully in {time.time() - start_time:.2f} seconds.")
        except mysql.connector.Error as err:
            print(f"Error adding index: {err}")
    
    conn.close()

if __name__ == "__main__":
    add_index()
