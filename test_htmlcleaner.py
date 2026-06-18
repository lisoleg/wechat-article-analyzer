"""测试 HtmlCleaner：用一篇真实文章 HTML 触发错误，写结果到文件。"""
import sys
import os

# 确保 src 在路径里
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.chdir(os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from src.utils.html_cleaner import HtmlCleaner

RESULT_FILE = "test_htmlcleaner.log"

def log(msg: str):
    """写日志到文件（utf-8），同时 print。"""
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 用列表 API 拿到的一篇真实文章 URL
        # 从 DB 里取第一篇 pending/failed 的文章
        import sqlite3
        conn = sqlite3.connect("data/articles.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT url FROM articles WHERE crawl_status='failed' LIMIT 1"
        ).fetchone()
        if not row:
            log("DB 里没有 failed 文章，先跑 crawl 插入一篇")
            return
        url = row["url"]
        log(f"测试 URL: {url[:80]}")

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        html = page.content()
        log(f"页面 HTML 长度: {len(html)}")

        # 测试 extract_html 等效逻辑
        for selector in ["#js_content", ".rich_media_content", "article"]:
            elem = page.query_selector(selector)
            if elem:
                inner = elem.inner_html()
                log(f"选择器 {selector} 匹配，inner_html 长度: {len(inner)}")
                # 直接用 BeautifulSoup 解析这段 HTML
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(inner, "lxml")
                    log(f"BeautifulSoup 解析成功（lxml）")
                except Exception as e:
                    log(f"lxml 解析失败: {e}，尝试 html.parser")
                    try:
                        soup = BeautifulSoup(inner, "html.parser")
                        log("html.parser 解析成功")
                    except Exception as e2:
                        log(f"html.parser 也失败: {e2}")
                        continue
                # 尝试 get_text
                try:
                    text = soup.get_text(separator="", strip=False)
                    log(f"get_text 成功，文本长度: {len(text)}")
                    break
                except Exception as e:
                    log(f"get_text 失败: {e}")
                    import traceback
                    log(traceback.format_exc())

        browser.close()

if __name__ == "__main__":
    main()
