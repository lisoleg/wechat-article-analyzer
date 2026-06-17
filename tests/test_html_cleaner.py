"""HTML 清洗测试。

测试 HtmlCleaner 的 clean / html_to_text / extract_text_from_selector 方法。
验证能正确去除 script / style / 广告，并转换为纯文本。
"""

import pytest

from src.utils.html_cleaner import HtmlCleaner


class TestHtmlCleanerClean:
    """clean() 方法测试。"""

    def test_removes_script_tags(self):
        """测试移除 script 标签。"""
        html = """
        <html>
        <body>
            <script>alert('xss');</script>
            <p>正文内容</p>
        </body>
        </html>
        """
        cleaned = HtmlCleaner.clean(html)
        assert "alert" not in cleaned
        assert "正文内容" in cleaned
        assert "<script" not in cleaned

    def test_removes_style_tags(self):
        """测试移除 style 标签。"""
        html = """
        <html>
        <head><style>body { color: red; }</style></head>
        <body><p>内容</p></body>
        </html>
        """
        cleaned = HtmlCleaner.clean(html)
        assert "color: red" not in cleaned
        assert "内容" in cleaned

    def test_removes_ad_elements(self):
        """测试移除广告元素。"""
        html = """
        <html>
        <body>
            <div class="advertisement">广告内容</div>
            <div id="banner-promo">横幅广告</div>
            <p>正文</p>
        </body>
        </html>
        """
        cleaned = HtmlCleaner.clean(html)
        assert "广告内容" not in cleaned
        assert "横幅广告" not in cleaned
        assert "正文" in cleaned

    def test_removes_comments(self):
        """测试移除 HTML 注释。"""
        html = """
        <html>
        <body>
            <!-- 这是注释 -->
            <p>正文</p>
        </body>
        </html>
        """
        cleaned = HtmlCleaner.clean(html)
        assert "这是注释" not in cleaned
        assert "正文" in cleaned


class TestHtmlToText:
    """html_to_text() 方法测试。"""

    def test_basic_conversion(self):
        """测试基本 HTML 转纯文本。"""
        html = "<html><body><p>Hello</p><p>World</p></body></html>"
        text = HtmlCleaner.html_to_text(html)
        assert "Hello" in text
        assert "World" in text

    def test_preserves_paragraph_breaks(self):
        """测试段落换行保留。"""
        html = """
        <html><body>
            <p>第一段</p>
            <p>第二段</p>
        </body></html>
        """
        text = HtmlCleaner.html_to_text(html)
        lines = text.split("\n")
        assert "第一段" in lines
        assert "第二段" in lines

    def test_strips_script_and_style(self):
        """测试转换时移除 script 和 style。"""
        html = """
        <html>
        <head><style>.x { color: red; }</style></head>
        <body>
            <script>console.log('test');</script>
            <p>纯文本内容</p>
        </body>
        </html>
        """
        text = HtmlCleaner.html_to_text(html)
        assert "color" not in text
        assert "console.log" not in text
        assert "纯文本内容" in text

    def test_empty_html(self):
        """测试空 HTML 输入。"""
        text = HtmlCleaner.html_to_text("")
        assert text == ""

    def test_nested_tags(self):
        """测试嵌套标签。"""
        html = """
        <html><body>
            <div>
                <p>外层<span>内层</span>文本</p>
            </div>
        </body></html>
        """
        text = HtmlCleaner.html_to_text(html)
        assert "外层" in text
        assert "内层" in text
        assert "文本" in text

    def test_head_removed(self):
        """测试 head 标签内容被移除。"""
        html = """
        <html>
        <head><title>页面标题</title><meta charset="utf-8"></head>
        <body><p>正文</p></body>
        </html>
        """
        text = HtmlCleaner.html_to_text(html)
        assert "页面标题" not in text
        assert "正文" in text


class TestExtractTextFromSelector:
    """extract_text_from_selector() 方法测试。"""

    def test_extract_by_id(self):
        """测试通过 ID 选择器提取文本。"""
        html = """
        <html><body>
            <div id="header">头部</div>
            <div id="js_content">
                <p>这是正文内容</p>
                <p>第二段正文</p>
            </div>
        </body></html>
        """
        text = HtmlCleaner.extract_text_from_selector(html, "#js_content")
        assert "这是正文内容" in text
        assert "第二段正文" in text
        assert "头部" not in text

    def test_extract_not_found(self):
        """测试选择器未匹配时返回空字符串。"""
        html = "<html><body><p>内容</p></body></html>"
        text = HtmlCleaner.extract_text_from_selector(html, "#not_exist")
        assert text == ""

    def test_extract_with_script_removed(self):
        """测试选择器提取时也移除 script。"""
        html = """
        <html><body>
            <div id="js_content">
                <script>alert('xss');</script>
                <p>正文</p>
            </div>
        </body></html>
        """
        text = HtmlCleaner.extract_text_from_selector(html, "#js_content")
        assert "alert" not in text
        assert "正文" in text

    def test_extract_class_selector(self):
        """测试 class 选择器。"""
        html = """
        <html><body>
            <div class="rich_media_content">
                <p>微信正文</p>
            </div>
        </body></html>
        """
        text = HtmlCleaner.extract_text_from_selector(
            html, ".rich_media_content"
        )
        assert "微信正文" in text
