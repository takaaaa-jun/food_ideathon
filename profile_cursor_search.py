import time
import random
from core.database import get_db_connection
from services.search import search_recipes

def profile_cursor():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "玉ねぎ"
    start_id = random.randint(1, 1500000)
    print(f"Profiling cursor search for '{query}' starting at ID {start_id}...")
    
    start_time = time.time()
    # Mocking the call structure from app.py
    recipes = search_recipes(cursor, query, start_id=start_id, limit=10)
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Found {len(recipes)} recipes")
    
    # Also profile multi-keyword
    query_multi = "玉ねぎ 人参"
    print(f"\nProfiling cursor search for '{query_multi}' starting at ID {start_id}...")
    start_time = time.time()
    recipes = search_recipes(cursor, query_multi, start_id=start_id, limit=10)
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Found {len(recipes)} recipes")

    conn.close()

if __name__ == "__main__":
    profile_cursor()
