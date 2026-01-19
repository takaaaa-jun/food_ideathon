
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_connection

def inspect():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("--- nutritions columns ---")
    cursor.execute("DESCRIBE nutritions")
    for row in cursor.fetchall():
        print(f"{row['Field']} ({row['Type']})")

    print("\n--- recipe_nutrition_info columns ---")
    cursor.execute("DESCRIBE recipe_nutrition_info")
    for row in cursor.fetchall():
        print(f"{row['Field']} ({row['Type']})")

    conn.close()

if __name__ == "__main__":
    inspect()
