
import os
import sys
import csv
import mysql.connector
from datetime import datetime

# Add parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from core.database import get_db_connection
except ImportError:
    # Fallback if running directly without app context
    print("Could not import get_db_connection, using simplified connection")
    def get_db_connection():
        return mysql.connector.connect(
            host=os.environ.get('MYSQL_HOST', 'db'),
            user=os.environ.get('MYSQL_USER', 'deliciousdx'),
            password=os.environ.get('MYSQL_PASSWORD', 'deliciousdx'),
            database=os.environ.get('MYSQL_DATABASE', 'database_food_ideathon')
        )

def restore_standard_recipes():
    print("Starting restoration of standard_recipes...")
    
    csv_path = os.path.join(os.path.dirname(__file__), '../standard_recipes.csv')
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return

    cursor = conn.cursor()

    # 1. Create Table
    print("Creating table if not exists...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS standard_recipes (
        id INT PRIMARY KEY,
        category_medium VARCHAR(255),
        recipe_count INT,
        cooking_time INT,
        average_steps INT,
        created_at DATETIME
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    cursor.execute(create_table_sql)

    # 2. Read CSV and Insert
    print(f"Reading CSV from {csv_path}...")
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            print(f"CSV Headers: {reader.fieldnames}")
            
            # Prepare INSERT statement
            insert_sql = """
            INSERT INTO standard_recipes (id, category_medium, recipe_count, cooking_time, average_steps, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                category_medium = VALUES(category_medium),
                recipe_count = VALUES(recipe_count),
                cooking_time = VALUES(cooking_time),
                average_steps = VALUES(average_steps),
                created_at = VALUES(created_at)
            """
            
            rows_to_insert = []
            for row in reader:
                # Handle cooking_time potentially being empty or invalid
                cooking_time = row['cooking_time']
                if not cooking_time or not cooking_time.isdigit():
                    cooking_time = 0
                
                rows_to_insert.append((
                    row['id'],
                    row['category_medium'],
                    row['recipe_count'],
                    int(cooking_time),
                    row['average_steps'],
                    row['created_at']
                ))
            
            if rows_to_insert:
                print(f"Inserting {len(rows_to_insert)} records...")
                cursor.executemany(insert_sql, rows_to_insert)
                conn.commit()
                print("Data insertion complete.")
            else:
                print("No data found in CSV.")

    except Exception as e:
        print(f"Error during restoration: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    restore_standard_recipes()
