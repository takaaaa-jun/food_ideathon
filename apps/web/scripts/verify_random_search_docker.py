import sys
import os
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db_connection
from services.search import search_recipes, get_recipe_details

def verify_random_search(query):
    print(f"Verifying Random Search for: '{query}'")
    conn = get_db_connection()
    if not conn:
        print("DB Connection Failed")
        return
        
    cursor = conn.cursor(dictionary=True)
    
    # 1. Random Start
    rand_id = random.randint(1, 1500000)
    print(f"Random ID: {rand_id}")
    
    # 2. Search
    print("Executing search...")
    recipes = search_recipes(cursor, query, start_id=rand_id, limit=10)
    
    print(f"Found {len(recipes)} recipes in first pass.")
    for r in recipes:
        print(f" - ID: {r['id']}, Title: {r['title']}, Date: {r['published_at']}")
        
    if len(recipes) < 10:
        needed = 10 - len(recipes)
        print(f"Need {needed} more. Wrapping around...")
        recipes_2 = search_recipes(cursor, query, start_id=1, limit=needed)
        print(f"Found {len(recipes_2)} recipes in second pass.")
        recipes.extend(recipes_2)
        
    print(f"Total Results: {len(recipes)}")
    
    if recipes:
        target_id = recipes[0]['id']
        print(f"\nFetching details for ID: {target_id}...")
        detail = get_recipe_details(cursor, target_id)
        if detail:
            print(f"Detail Fetch Success: {detail['title']}")
            print(f"Ingredients: {len(detail.get('ingredients', []))}")
        else:
            print("Detail Fetch Failed")

    conn.close()

if __name__ == "__main__":
    verify_random_search("玉ねぎ")
