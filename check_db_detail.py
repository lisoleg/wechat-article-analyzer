"""Check pending/failed articles detail."""
import sqlite3
import os

os.chdir('./data')
conn = sqlite3.connect('articles.db')
conn.row_factory = sqlite3.Row

# Check all articles with status
for status in ['pending', 'failed', 'complete']:
    rows = conn.execute(
        'SELECT id, title, crawl_status, crawl_error FROM articles WHERE crawl_status=? ORDER BY id',
        (status,)
    ).fetchall()
    if rows:
        print(f"\n=== {status} ({len(rows)}) ===")
        for r in rows:
            title = r['title'][:40] if r['title'] else '(no title)'
            err = r['crawl_error'][:100] if r['crawl_error'] else '(none)'
            print(f"  id={r['id']}, title={title}")
            if err != '(none)':
                print(f"    error: {err}")

conn.close()
