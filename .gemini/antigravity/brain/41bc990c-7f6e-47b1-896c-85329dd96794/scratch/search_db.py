import sqlite3
import os

db_path = "c:/Users/nemes/Desktop/Ultron/data/memory_v2/memory.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"Searching in table: {table_name}")
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            for row in rows:
                if "Ali Tuna" in str(row):
                    print(f"FOUND in {table_name}: {row}")
        except Exception as e:
            print(f"Error reading {table_name}: {e}")
    conn.close()
else:
    print("DB not found")
