import time
import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_connection
from services.search import search_recipes

def profile_slow_case():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # User Case: "じゃがいも 大根 砂糖 醤油" (Potato, Daikon, Sugar, Soy Sauce)
    # These are all very common ingredients.
    # If "じゃがいも" (Potato) is the driver, it has huge row count.
    # Verification against "Sugar" (also huge) might be fast existence check,
    # but we still scan thousands of "Potato" rows to find a recipe that has ALL 4.
    
    query = "じゃがいも 大根 砂糖 醤油"
    start_id = random.randint(1, 1500000)
    print(f"Profiling slow search for '{query}' starting at ID {start_id}...")
    
    start_time = time.time()
    try:
        recipes = search_recipes(cursor, query, start_id=start_id, limit=10)
        end_time = time.time()
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        print(f"Found {len(recipes)} recipes")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

    conn.close()

if __name__ == "__main__":
    profile_slow_case()
