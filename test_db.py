import mysql.connector
import sys

config = {
    'user': 'deliciousdx',
    'password': 'deliciousdx',
    'host': '172.17.0.1',
    'database': 'database_food_ideathon'
}

try:
    print(f"Connecting to {config['host']}...")
    conn = mysql.connector.connect(**config)
    print("Success!")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
