
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_connection
from services.search import search_standard_recipes

def test_search():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "玉ねぎ"
    print(f"Searching for '{query}' (Ingredient Mode)...")
    
    start_time = time.time()
    results = search_standard_recipes(cursor, query, search_mode='ingredient')
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Results Count: {len(results)}")
    
    for name, details in results:
        print(f"- {name} (ID: {details['id']}, Count: {details['recipe_count']})")

    print("\n" + "="*20 + "\n")
    
    query = "ハンバーグ"
    print(f"Searching for '{query}' (Recipe Mode)...")
    
    start_time = time.time()
    results = search_standard_recipes(cursor, query, search_mode='recipe')
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Results Count: {len(results)}")
    
    for name, details in results:
        print(f"- {name} (ID: {details['id']}, Count: {details['recipe_count']})")

    conn.close()

if __name__ == "__main__":
    test_search()
