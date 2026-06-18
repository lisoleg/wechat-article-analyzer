"""打印所有 pending 文章的 crawl_error。"""
import sqlite3, os
os.chdir('./data')
conn = sqlite3.connect('articles.db')
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT id, title, crawl_status, crawl_error FROM articles WHERE crawl_status!='complete' ORDER BY id"
).fetchall()

print(f"非 complete 文章数: {len(rows)}")
for r in rows:
    status = r['crawl_status']
    err = (r['crawl_error'] or '')[:200]
    title = (r['title'] or '')[:30]
    print(f"  id={r['id']}, status={status}, title={title}, err={err}")

conn.close()
