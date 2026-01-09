from apps.web.core.database import get_db_connection
from apps.web.services.search import search_recipes, search_standard_recipes

def test_search():
    print("Testing DB Connection...")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect.")
        return

    cursor = conn.cursor(dictionary=True)
    
    # Test 1: FULLTEXT + Ingredient Search
    query = "玉ねぎ"
    print(f"\nSearching for '{query}'...")
    results, count = search_recipes(cursor, query)
    print(f"Found {count} recipes.")
    if results:
        print(f"Top result: {results[0]['title']}")
    
    # Test 2: Standard Search
    query_std = "カレー"
    print(f"\nSearching Standard Recipes for '{query_std}'...")
    std_results = search_standard_recipes(cursor, query_std, search_mode='recipe')
    print(f"Found {len(std_results)} recipes.")
    if std_results:
        print(f"Top result: {std_results[0]['category_medium']}")

    conn.close()

if __name__ == "__main__":
    test_search()
