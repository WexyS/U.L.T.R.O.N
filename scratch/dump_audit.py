import sqlite3
import json

def dump_audit():
    try:
        conn = sqlite3.connect("data/react_audit.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM react_audit ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
        
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps(results, indent=2, ensure_ascii=False))
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_audit()
