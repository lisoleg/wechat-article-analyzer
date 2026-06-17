"""HTML 清洗模块 — HtmlCleaner。

使用 BeautifulSoup4 + lxml 解析 HTML，
去除 script / style / 广告等无关内容，提取纯文本。
"""

from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup, Tag


def _get_parser() -> str:
    """获取可用的 HTML 解析器，优先使用 lxml，不可用时回退到 html.parser。

    Returns:
        解析器名称字符串。
    """
    try:
        # 测试 lxml 是否可用
        BeautifulSoup("<p>test</p>", "lxml")
        return "lxml"
    except Exception:
        return "html.parser"


class HtmlCleaner:
    """HTML 清洗工具，提供静态方法。

    使用方式::

        text = HtmlCleaner.html_to_text(html_string)
        cleaned_html = HtmlCleaner.clean(html_string)
    """

    # 需要完全移除的标签
    _REMOVE_TAGS: list[str] = [
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "form",
        "input",
        "button",
        "nav",
        "footer",
    ]

    # 常见广告 class / id 关键词
    _AD_KEYWORDS: list[str] = [
        "ad",
        "advertisement",
        "banner",
        "promo",
        "sponsor",
        "qr_code",
        "qr-code",
        "recommend",
        "reward",
        "js_pc_qr_code",
        "share",
        "tips_app",
        "tips_pc",
    ]

    @classmethod
    def clean(cls, html: str) -> str:
        """清洗 HTML：移除 script/style/广告等标签，返回清洗后的 HTML 字符串。

        Args:
            html: 原始 HTML 字符串。

        Returns:
            清洗后的 HTML 字符串。
        """
        soup = BeautifulSoup(html, _get_parser())

        # 移除指定标签
        for tag_name in cls._REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 移除含广告关键词的元素
        for element in soup.find_all(True):
            classes = element.get("class", [])
            if isinstance(classes, str):
                classes = classes.split()
            elem_id = element.get("id", "")
            combined = " ".join(classes) + " " + elem_id
            for keyword in cls._AD_KEYWORDS:
                if keyword in combined.lower():
                    element.decompose()
                    break

        # 移除注释
        from bs4 import Comment
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        return str(soup)

    @classmethod
    def html_to_text(cls, html: str) -> str:
        """将 HTML 转换为纯文本。

        先执行 clean() 清洗，再提取文本内容，保留段落换行。

        Args:
            html: 原始 HTML 字符串。

        Returns:
            清洗后的纯文本。
        """
        cleaned_html = cls.clean(html)
        soup = BeautifulSoup(cleaned_html, _get_parser())

        # 移除 head 标签内容
        head = soup.find("head")
        if head:
            head.decompose()

        # 在块级元素前添加换行
        block_tags = [
            "p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "tr", "blockquote", "section", "article",
        ]

        for tag_name in block_tags:
            for tag in soup.find_all(tag_name):
                tag.append("\n")

        # 获取文本并规范化空白
        text = soup.get_text(separator="")
        # 合并连续空行，去除每行首尾空格
        lines = [line.strip() for line in text.splitlines()]
        # 移除空行，但保留段落间换行
        result_lines: list[str] = []
        prev_empty = False
        for line in lines:
            if line:
                result_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                result_lines.append("")
                prev_empty = True
        return "\n".join(result_lines).strip()

    @classmethod
    def extract_text_from_selector(cls, html: str, selector: str) -> str:
        """从指定 CSS 选择器提取纯文本。

        Args:
            html: 原始 HTML 字符串。
            selector: CSS 选择器（如 "#js_content"）。

        Returns:
            选择器匹配元素的纯文本，无匹配时返回空字符串。
        """
        soup = BeautifulSoup(html, _get_parser())
        element: Optional[Tag] = soup.select_one(selector)
        if element is None:
            return ""
        # 对匹配元素再执行清洗
        return cls.html_to_text(str(element))
