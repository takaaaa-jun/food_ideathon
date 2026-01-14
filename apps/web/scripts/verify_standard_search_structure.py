import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_connection
from services.search import search_standard_recipes

def verify():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Search for something that exists, or empty
    results = search_standard_recipes(cursor, "カレー") # "Curry" is likely to exist
    
    print(f"Type of results: {type(results)}")
    if isinstance(results, list):
        print(f"Length: {len(results)}")
        if results:
            print(f"First item type: {type(results[0])}")
            print(f"First item keys: {results[0].keys()}")
    elif isinstance(results, dict):
        print(f"Keys: {list(results.keys())}")
        first_val = next(iter(results.values()))
        print(f"First value type: {type(first_val)}")
        if isinstance(first_val, dict):
             print(f"First value keys: {first_val.keys()}")

    conn.close()

if __name__ == "__main__":
    verify()
