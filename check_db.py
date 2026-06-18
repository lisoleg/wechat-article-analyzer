"""Check articles DB state."""
import sqlite3
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

conn = sqlite3.connect('./data/articles.db')
conn.row_factory = sqlite3.Row

# Status counts
stats = conn.execute(
    'SELECT crawl_status, COUNT(*) as c FROM articles GROUP BY crawl_status'
).fetchall()
print("=== Status counts ===")
for r in stats:
    print(f"  {r[0]}: {r[1]}")

# Last 5 articles
rows = conn.execute(
    'SELECT id, crawl_status FROM articles ORDER BY id DESC LIMIT 5'
).fetchall()
print("\n=== Last 5 articles ===")
for r in rows:
    print(f"  id={r['id']}, status={r['crawl_status']}")

conn.close()
