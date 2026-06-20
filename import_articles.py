"""批量导入微信文章到数据库。

使用 WebFetch 获取的内容直接入库，不依赖 Playwright 爬虫。
"""
import sys
sys.path.insert(0, '.')

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "data/articles.db"

# 4篇新文章的基本信息（内容通过 WebFetch 获取）
articles = [
    {
        "url": "https://mp.weixin.qq.com/s/C1N70hDX-easnN0xqusKgA",
        "title": "κ-Gate 与 κ-Gate 剪枝：TOMAS 太一互搏体系中的硬锚否决门与语义压缩剪枝",
        "publish_time": "2026-06-20 17:59",
    },
    {
        "url": "https://mp.weixin.qq.com/s/tM8nmq6pkgz0ufS4El_CiA",
        "title": "ψ-锚（目的锚／ψ-Anchor）：太一互搏公理体系（TOMAS）中 AGI 不可删改的终极目的与硬锚否决权形式化",
        "publish_time": "2026-06-20 18:51",
    },
    {
        "url": "https://mp.weixin.qq.com/s/Z5m3lp-a3XaQYEuZqy7tVQ",
        "title": "待获取",
        "publish_time": "2026-06-20",
    },
    {
        "url": "https://mp.weixin.qq.com/s/fCE5HJwGmveMkNWj3yYNCA",
        "title": "待获取",
        "publish_time": "2026-06-20",
    },
]

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

for art in articles:
    # 检查是否已存在
    cursor.execute("SELECT id FROM articles WHERE url = ?", (art["url"],))
    existing = cursor.fetchone()

    if existing:
        print(f"已存在（跳过）: {art['title'][:40]}")
        continue

    # 插入新文章
        cursor.execute(
        """INSERT INTO articles (url, title, publish_time, crawl_status, created_at)
           VALUES (?, ?, ?, 'pending', ?)""",
        (art["url"], art["title"], art["publish_time"], datetime.now().isoformat())
    )
    article_id = cursor.lastrowid
    print(f"已导入 [ID={article_id}]: {art['title'][:50]}")

conn.commit()
cursor.execute("SELECT COUNT(*) as cnt FROM articles")
total = cursor.fetchone()["cnt"]
print(f"\n数据库总文章数: {total}")
conn.close()
