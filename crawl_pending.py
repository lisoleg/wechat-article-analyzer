"""
抓取待抓取文章的内容并更新数据库
用法: python crawl_pending.py
"""
import sqlite3
import sys
import time
from pathlib import Path

def get_pending_articles(db_path: str) -> list:
    """获取所有待抓取的文章"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, url, title FROM articles WHERE crawl_status = 'pending' ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_article_content(db_path: str, article_id: int, content_html: str, content_text: str) -> None:
    """保存文章内容并更新状态为 complete"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE articles SET content_html = ?, content_text = ?, crawl_status = 'complete', crawl_time = datetime('now') WHERE id = ?",
        (content_html, content_text, article_id),
    )
    conn.commit()
    conn.close()
    print(f"  ✅ 文章 {article_id} 内容已保存，状态更新为 complete")


def crawl_with_playwright(url: str) -> tuple:
    """使用 Playwright 抓取微信文章内容"""
    try:
        from playwright.sync_api import sync_playwright
        import datetime

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            print(f"  🌐 正在访问: {url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # 提取标题
            title = page.locator("#activity-name").inner_text() or page.title()

            # 提取正文 HTML
            content_html = page.locator("#js_content").inner_html()

            # 提取正文纯文本
            content_text = page.locator("#js_content").inner_text()

            browser.close()
            return title.strip(), content_html, content_text.strip()
    except Exception as e:
        print(f"  ❌ Playwright 抓取失败: {e}")
        return None, None, None


def main():
    db_path = str(Path(__file__).parent / "data" / "articles.db")
    if not Path(db_path).exists():
        print(f"❌ 数据库不存在: {db_path}")
        sys.exit(1)

    articles = get_pending_articles(db_path)
    if not articles:
        print("✅ 没有待抓取的文章")
        return

    print(f"🔍 发现 {len(articles)} 篇待抓取文章:")
    for a in articles:
        print(f"  - [{a['id']}] {a['title'][:50]}")

    import sqlite3
    for article in articles:
        aid = article["id"]
        url = article["url"]
        print(f"\n📥 正在抓取文章 {aid}: {article['title'][:50]}...")
        title, content_html, content_text = crawl_with_playwright(url)
        if content_html and content_text:
            # 保存内容
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            now = __import__("datetime").datetime.now().isoformat()
            cur.execute(
                "UPDATE articles SET content_html = ?, content_text = ?, crawl_status = 'complete', crawl_time = ? WHERE id = ?",
                (content_html, content_text, now, aid),
            )
            conn.commit()
            conn.close()
            print(f"  ✅ 文章 {aid} 抓取完成，内容长度: {len(content_text)} 字符")
        else:
            print(f"  ❌ 文章 {aid} 抓取失败")
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "UPDATE articles SET crawl_status = 'failed' WHERE id = ?", (aid,)
            )
            conn.commit()
            conn.close()
        time.sleep(2)  # 避免请求过快

    print("\n✅ 所有待抓取文章处理完成！")


if __name__ == "__main__":
    main()
