"""最小化测试：用模拟的微信文章 HTML 测 HtmlCleaner。"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.chdir(os.path.dirname(__file__))

from src.utils.html_cleaner import HtmlCleaner

RESULT_FILE = "test_htmlcleaner_result.log"

def log(msg: str):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def main():
    # 模拟微信文章 HTML（含 #js_content）
    test_html = """<html>
<head><title>测试文章</title></head>
<body>
<div id="js_content" class="rich_media_content">
    <p>第一段内容。</p>
    <p>第二段内容，包含<strong>加粗</strong>文字。</p>
    <section>
        <h2>小标题</h2>
        <p>更多内容在这里。</p>
    </section>
    <div class="reward_area"><p>打赏</p></div>
    <script>var x = 1;</script>
</div>
</body>
</html>"""

    log("=== 测试 extract_text_from_selector ===")
    try:
        text = HtmlCleaner.extract_text_from_selector(test_html, "#js_content")
        log(f"成功！文本长度: {len(text)}, 前100字: {text[:100]}")
    except Exception as e:
        log(f"失败: {e}")
        import traceback
        log(traceback.format_exc())

    log("\n=== 测试 html_to_text ===")
    try:
        text2 = HtmlCleaner.html_to_text(test_html)
        log(f"成功！文本长度: {len(text2)}, 前100字: {text2[:100]}")
    except Exception as e:
        log(f"失败: {e}")
        import traceback
        log(traceback.format_exc())

    log("\n=== 测试 clean ===")
    try:
        cleaned = HtmlCleaner.clean(test_html)
        log(f"成功！清洗后长度: {len(cleaned)}, 前200字: {cleaned[:200]}")
    except Exception as e:
        log(f"失败: {e}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    main()
