
import sqlite3
import os

DB_FILE = "data/jobs.db"

def check_orphans():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("--- Checking for Orphaned Resume Versions ---")
    
    # Find versions whose draft_id is not in drafts table
    cursor.execute("""
        SELECT rv.id, rv.draft_id, rv.pdf_path, rv.version_number
        FROM resume_versions rv
        LEFT JOIN drafts d ON rv.draft_id = d.id
        WHERE d.id IS NULL
    """)
    orphans = cursor.fetchall()
    
    if orphans:
        print(f"Found {len(orphans)} orphaned resume versions:")
        for o in orphans:
            print(f"  - Version ID: {o[0]}, Draft ID (Missing): {o[1]}, Path: {o[2]}")
    else:
        print("No orphaned versions found.")
        
    print("\n--- Checking for Draft IDs associated with target job IDs ---")
    target_job_ids = [
        "7014725717177112913",
        "5107616587956981479",
        "5814125911930369848",
        "200687386713884251"
    ]
    
    for tid in target_job_ids:
        print(f"\nTarget Path Segment: /{tid}/")
        cursor.execute("SELECT draft_id, pdf_path FROM resume_versions WHERE pdf_path LIKE ?", (f"%/{tid}/%",))
        res = cursor.fetchall()
        for rv_draft_id, pdf_path in res:
            cursor.execute("SELECT id, status FROM drafts WHERE id = ?", (rv_draft_id,))
            draft = cursor.fetchone()
            if draft:
                print(f"  Version points to VALID draft: {draft[0]} (Status: {draft[1]})")
            else:
                print(f"  Version points to MISSING draft: {rv_draft_id}")
            print(f"  Path: {pdf_path}")
            
    conn.close()

if __name__ == "__main__":
    check_orphans()
