"""文章正文采集模块 — ArticleContentCrawler。

逐篇导航到文章真实 URL（由 article_list.py 通过 appmsgpublish API 获取），
提取正文 HTML（通常在 #js_content 容器中），
用 HtmlCleaner 转换为纯文本，提取封面图 URL。
每篇间隔 2-3 秒随机延迟防风控。
失败记录 crawl_error，状态置 failed，继续下一篇。
"""

from __future__ import annotations

import random
import time
from typing import Optional

from loguru import logger
from playwright.sync_api import Page

from src.crawler.browser import BrowserManager
from src.database import ArticleRepository
from src.models import Article
from src.utils.html_cleaner import HtmlCleaner


class ArticleContentCrawler:
    """文章正文逐篇采集器。

    属性:
        browser_mgr: 浏览器管理器。
        repo: 文章仓库。
        interval_min: 随机延迟下限（秒）。
        interval_max: 随机延迟上限（秒）。
    """

    # 正文内容选择器列表（按优先级尝试）
    CONTENT_SELECTORS: list[str] = [
        "#js_content",
        ".rich_media_content",
        "#page-content",
        ".rich_media_area_primary_inner",
        "article",
    ]

    # 封面图选择器列表
    COVER_SELECTORS: list[str] = [
        'meta[property="og:image"]',
        ".rich_media_meta img",
        ".reward_area img",
        'img[data-src]:first-of-type',
    ]

    def __init__(
        self,
        browser_mgr: BrowserManager,
        repo: ArticleRepository,
        interval_min: int = 2,
        interval_max: int = 3,
    ) -> None:
        """初始化正文采集器。

        Args:
            browser_mgr: 浏览器管理器实例。
            repo: 文章仓库实例。
            interval_min: 随机延迟下限（秒）。
            interval_max: 随机延迟上限（秒）。
        """
        self.browser_mgr: BrowserManager = browser_mgr
        self.repo: ArticleRepository = repo
        self.interval_min: int = interval_min
        self.interval_max: int = interval_max

    def fetch_all_content(
        self,
        resume: bool = False,
        limit: Optional[int] = None,
    ) -> None:
        """批量抓取所有待采集文章的正文内容。

        Args:
            resume: 断点续抓模式，True 时跳过已完成的文章。
            limit: 限制采集数量。
        """
        # 获取待采集文章
        if resume:
            pending_articles = self.repo.get_articles_by_crawl_status("pending")
            failed_articles = self.repo.get_articles_by_crawl_status("failed")
            articles = pending_articles + failed_articles
        else:
            articles = self.repo.get_articles_by_crawl_status("pending")

        if limit:
            articles = articles[:limit]

        if not articles:
            logger.info("没有待采集的文章")
            # debug: 打印所有文章状态
            all_arts = self.repo.get_all_articles()
            statuses = {}
            for a in all_arts:
                statuses[a.crawl_status] = statuses.get(a.crawl_status, 0) + 1
            logger.debug(f"DB 中所有文章状态: {statuses}")
            return

        logger.info(f"开始采集正文内容，共 {len(articles)} 篇")

        success_count = 0
        fail_count = 0

        for idx, article in enumerate(articles, start=1):
            logger.info(
                f"[{idx}/{len(articles)}] 正在抓取: {article.title[:50]}..."
            )

            try:
                # 更新状态为进行中
                self.repo.update_crawl_status(article.id, "in_progress")

                # 抓取单篇
                result = self.fetch_content(article)

                if result and result.content_text:
                    self.repo.update_content(
                        article.id,
                        result.content_html or "",
                        result.content_text,
                        result.cover_image_url,
                    )
                    self.repo.update_crawl_status(article.id, "complete")
                    success_count += 1
                    logger.info(
                        f"[{idx}/{len(articles)}] 采集成功: {article.title[:50]}"
                    )
                else:
                    self.repo.update_crawl_status(
                        article.id, "failed", "未提取到正文内容"
                    )
                    fail_count += 1
                    logger.warning(
                        f"[{idx}/{len(articles)}] 未提取到正文: {article.title[:50]}"
                    )

            except Exception as e:
                error_msg = str(e)[:500]
                self.repo.update_crawl_status(article.id, "failed", error_msg)
                fail_count += 1
                logger.error(
                    f"[{idx}/{len(articles)}] 采集失败: {article.title[:50]} - {e}"
                )
                logger.error("详细错误：", exc_info=True)

            # 随机延迟防风控（最后一篇不需要）
            if idx < len(articles):
                delay = random.uniform(self.interval_min, self.interval_max)
                logger.debug(f"等待 {delay:.1f} 秒...")
                time.sleep(delay)

        logger.info(
            f"正文采集完成: 成功 {success_count} 篇, 失败 {fail_count} 篇"
        )

    def fetch_content(self, article: Article) -> Optional[Article]:
        """抓取单篇文章的正文内容。

        Args:
            article: 待抓取的文章对象（article.url 为真实 content_url）。

        Returns:
            更新后的 Article 对象（含 content_html / content_text / cover_image_url），
            失败返回 None。
        """
        if self.browser_mgr.page is None:
            raise RuntimeError("浏览器未启动")

        page = self.browser_mgr.page

        # 导航到文章真实 URL
        logger.debug(f"导航到文章页面: {article.url[:80]}")
        page.goto(article.url, wait_until="domcontentloaded", timeout=30000)

        # 等待正文容器加载
        time.sleep(2)

        # 提取正文 HTML
        content_html = self.extract_html(page)
        logger.debug(f"content_html 长度: {len(content_html) if content_html else 0}")

        # 提取封面图
        cover_url = self.extract_cover_image(page)
        logger.debug(f"cover_url: {cover_url}")

        # 转换为纯文本（逐步 try/except 定位错误）
        content_text = ""
        if content_html:
            # 方法1：从正文选择器提取
            for selector in self.CONTENT_SELECTORS:
                try:
                    text = HtmlCleaner.extract_text_from_selector(
                        page.content(), selector
                    )
                    if text and len(text.strip()) > 50:
                        content_text = text.strip()
                        logger.debug(f"选择器 {selector} 提取成功，文本长度: {len(content_text)}")
                        break
                except Exception as e2:
                    logger.warning(f"选择器 {selector} 提取失败: {e2}")
                    continue

            # 方法2：整个页面 HTML 清洗
            if not content_text:
                try:
                    content_text = HtmlCleaner.html_to_text(content_html)
                    logger.debug(f"html_to_text 提取成功，文本长度: {len(content_text)}")
                except Exception as e2:
                    logger.warning(f"html_to_text 失败: {e2}")
                    content_text = ""

        article.content_html = content_html
        article.content_text = content_text
        article.cover_image_url = cover_url

        return article

    def extract_html(self, page: Page) -> str:
        """从页面提取正文 HTML。

        尝试多个选择器，返回第一个匹配到的元素 HTML。
        如果所有选择器都未匹配，返回整个页面 HTML。

        Args:
            page: Playwright Page 对象。

        Returns:
            正文 HTML 字符串。
        """
        for selector in self.CONTENT_SELECTORS:
            try:
                element = page.query_selector(selector)
                if element:
                    html = element.inner_html()
                    if html and len(html.strip()) > 100:
                        logger.debug(f"正文选择器匹配: {selector}")
                        return html
            except Exception:
                continue

        # 回退：返回整个页面 HTML
        logger.warning("所有正文选择器均未匹配，使用整个页面 HTML")
        return page.content()

    def extract_cover_image(self, page: Page) -> Optional[str]:
        """提取文章封面图 URL。

        尝试多个选择器，返回第一个匹配到的图片 URL。

        Args:
            page: Playwright Page 对象。

        Returns:
            封面图 URL，未找到返回 None。
        """
        for selector in self.COVER_SELECTORS:
            try:
                if selector.startswith("meta"):
                    element = page.query_selector(selector)
                    if element:
                        content = element.get_attribute("content")
                        if content and content.startswith("http"):
                            return content
                else:
                    element = page.query_selector(selector)
                    if element:
                        src = (
                            element.get_attribute("data-src")
                            or element.get_attribute("src")
                        )
                        if src and src.startswith("http"):
                            return src
            except Exception:
                continue

        return None
