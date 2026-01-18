import sqlite3
import os

DB_FILE = "data/jobs.db"
if not os.path.exists(DB_FILE):
    print(f"DB file {DB_FILE} not found")
else:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT url, status, error_message FROM jobs LIMIT 20;")
    rows = cursor.fetchall()
    for row in rows:
        print(f"URL: {row[0]}")
        print(f"Status: {row[1]}")
        print(f"Error: {row[2]}")
        print("-" * 20)
    conn.close()
