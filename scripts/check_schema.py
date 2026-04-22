import sqlite3
import os

db_path = "data/conversations.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table[0]});")
        print(f"Schema for {table[0]}: {cursor.fetchall()}")
    conn.close()
else:
    print("DB not found")
