import sqlite3
import os

# Database is in the data folder in this same root
DB_FILE = os.path.join("data", "jobs.db")

if not os.path.exists(DB_FILE):
    print(f"DB file {DB_FILE} not found. Current CWD: {os.getcwd()}")
    print(f"Files in current dir: {os.listdir('.')}")
else:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT url, status, error_message, timestamp FROM jobs ORDER BY timestamp DESC LIMIT 20;")
    rows = cursor.fetchall()
    print(f"{'URL':<50} | {'Status':<20} | {'Error':<20}")
    print("-" * 100)
    for row in rows:
        print(f"{str(row[0])[:50]:<50} | {str(row[1]):<20} | {str(row[2])[:20]:<20}")
    conn.close()
