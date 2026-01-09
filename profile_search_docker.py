import sys
import os
import time
import mysql.connector

# No sys.path append needed as /app is PYTHONPATH in Docker

from core.database import get_db_connection
from services.search import search_recipes

def profile_search(query):
    print(f"Profiling search for: '{query}'")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to DB")
        return

    cursor = conn.cursor(dictionary=True)
    
    start_time = time.time()
    try:
        recipes, count = search_recipes(cursor, query)
    except Exception as e:
        print(f"Error during search: {e}")
        return
    finally:
        cursor.close()
        conn.close()
        
    end_time = time.time()
    duration = end_time - start_time
    print(f"Search completed in {duration:.4f} seconds.")
    print(f"Total count: {count}")
    print(f"Results returned: {len(recipes)}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "玉ねぎ"
    profile_search(query)
