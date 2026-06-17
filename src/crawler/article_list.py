"""文章列表采集模块 — ArticleListCrawler。

导航到微信公众号后台素材管理页面，滚动加载所有文章列表项，
解析每篇文章的标题、URL、发布时间，并 upsert 到数据库。

微信公众号后台文章列表通常通过 API 接口获取：
https://mp.weixin.qq.com/cgi-bin/appmsg?sub=list&action=list_ex&token=XXX&lang=zh_CN&f=json&ajax=1
返回的 JSON 中 articles 在 app_msg_info 列表里。
如果 API 方式不稳定，也支持通过页面 DOM 解析。
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from loguru import logger
from playwright.sync_api import Page, Response

from src.crawler.browser import BrowserManager
from src.database import ArticleRepository
from src.models import Article


class ArticleListCrawler:
    """文章列表批量采集器。

    支持两种采集方式：
    1. API 拦截：监听网络请求，直接解析 JSON 响应。
    2. DOM 解析：滚动加载页面，从 DOM 元素提取文章信息。

    Attributes:
        browser_mgr: 浏览器管理器。
        repo: 文章仓库。
    """

    # 素材管理页面 URL（需 token 参数，运行时从当前页面获取）
    MATERIAL_URL_TEMPLATE: str = (
        "https://mp.weixin.qq.com/cgi-bin/appmsg?"
        "sub=list&action=list_ex&begin={begin}&count={count}&"
        "token={token}&lang=zh_CN&f=json&ajax=1"
    )

    # 素材管理页面入口
    MATERIAL_PAGE_URL: str = (
        "https://mp.weixin.qq.com/cgi-bin/appmsg?sub=list&t=media/appmsg_list"
    )

    def __init__(
        self,
        browser_mgr: BrowserManager,
        repo: ArticleRepository,
    ) -> None:
        """初始化文章列表采集器。

        Args:
            browser_mgr: 浏览器管理器实例。
            repo: 文章仓库实例。
        """
        self.browser_mgr: BrowserManager = browser_mgr
        self.repo: ArticleRepository = repo
        self._collected_articles: list[dict[str, Any]] = []
        self._token: Optional[str] = None

    def fetch_article_list(
        self,
        resume: bool = False,
        limit: Optional[int] = None,
    ) -> list[Article]:
        """获取文章列表并存入数据库。

        Args:
            resume: 断点续抓模式，如果 True 则仅获取尚未入库的文章。
            limit: 限制获取数量，None 表示不限制。

        Returns:
            新获取的文章列表。
        """
        if self.browser_mgr.page is None:
            raise RuntimeError("浏览器未启动，请先调用 launch()")

        # 先导航到素材管理页面获取 token
        self._navigate_to_material_page()

        # 获取 token
        self._token = self._extract_token()
        if not self._token:
            logger.warning("未能从页面 URL 中提取 token，尝试使用 DOM 方式采集")

        logger.info(f"开始获取文章列表 (token={self._token})")

        all_articles: list[Article] = []

        # 方式1：尝试通过 API 批量获取
        if self._token:
            all_articles = self._fetch_via_api(resume, limit)

        # 方式2：如果 API 方式失败，使用 DOM 解析
        if not all_articles:
            logger.info("API 方式未获取到文章，尝试 DOM 方式")
            all_articles = self._fetch_via_dom(resume, limit)

        logger.info(f"文章列表获取完成，共 {len(all_articles)} 篇")
        return all_articles

    def _navigate_to_material_page(self) -> None:
        """导航到素材管理页面。"""
        page = self.browser_mgr.page
        assert page is not None

        # 先导航到后台首页
        page.goto("https://mp.weixin.qq.com/", wait_until="domcontentloaded")
        time.sleep(2)

        # 尝试点击进入素材管理
        try:
            # 点击"内容与互动" → "图文消息"
            page.goto(
                "https://mp.weixin.qq.com/cgi-bin/appmsg?sub=list&t=media/appmsg_list",
                wait_until="domcontentloaded",
            )
            time.sleep(3)
        except Exception as e:
            logger.warning(f"导航到素材管理页面时出现异常: {e}")

    def _extract_token(self) -> Optional[str]:
        """从当前页面 URL 中提取 token 参数。

        Returns:
            token 字符串，提取失败返回 None。
        """
        if self.browser_mgr.page is None:
            return None

        current_url = self.browser_mgr.page.url
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        token_list = params.get("token", [])
        return token_list[0] if token_list else None

    def _fetch_via_api(
        self,
        resume: bool,
        limit: Optional[int],
    ) -> list[Article]:
        """通过 API 接口批量获取文章列表。

        Args:
            resume: 断点续抓模式。
            limit: 数量限制。

        Returns:
            获取到的文章列表。
        """
        assert self._token is not None
        page = self.browser_mgr.page
        assert page is not None

        all_articles: list[Article] = []
        begin = 0
        count = 20  # 每页 20 条
        collected_count = 0

        while True:
            api_url = self.MATERIAL_URL_TEMPLATE.format(
                begin=begin, count=count, token=self._token
            )

            logger.debug(f"请求文章列表 API: begin={begin}, count={count}")

            try:
                # 使用 page.evaluate 发起 fetch 请求
                response_text = page.evaluate(
                    """
                    async (url) => {
                        const resp = await fetch(url);
                        return await resp.text();
                    }
                    """,
                    api_url,
                )

                data = json.loads(response_text)
                article_infos: list[dict[str, Any]] = data.get("app_msg_info", [])

                if not article_infos:
                    logger.info("API 返回空列表，采集完成")
                    break

                for info in article_infos:
                    article = self._parse_api_article(info)
                    if article:
                        # 断点续抓：跳过已入库且已完成的
                        if resume:
                            existing = self.repo.get_article_by_url(article.url)
                            if existing and existing.crawl_status == "complete":
                                continue

                        article_id = self.repo.upsert_article(article)
                        article.id = article_id
                        all_articles.append(article)
                        collected_count += 1

                        if limit and collected_count >= limit:
                            logger.info(f"已达到限制数量 {limit}")
                            return all_articles

                begin += count

                # 如果返回数量小于请求数量，说明已到末尾
                if len(article_infos) < count:
                    logger.info("已到列表末尾")
                    break

                # 间隔延迟防风控
                time.sleep(1)

            except Exception as e:
                logger.error(f"API 请求失败 (begin={begin}): {e}")
                break

        return all_articles

    def _fetch_via_dom(
        self,
        resume: bool,
        limit: Optional[int],
    ) -> list[Article]:
        """通过 DOM 解析方式获取文章列表。

        Args:
            resume: 断点续抓模式。
            limit: 数量限制。

        Returns:
            获取到的文章列表。
        """
        page = self.browser_mgr.page
        assert page is not None

        all_articles: list[Article] = []
        collected_count = 0
        scroll_count = 0
        max_scrolls = 200  # 最大滚动次数保护

        while scroll_count < max_scrolls:
            # 滚动加载
            self.scroll_to_load_all()
            scroll_count += 1

            # 解析当前页面的文章项
            items = self.parse_article_items()

            new_found = False
            for item in items:
                if resume:
                    existing = self.repo.get_article_by_url(item.url)
                    if existing and existing.crawl_status == "complete":
                        continue

                # 检查是否已收集过
                if not any(a.url == item.url for a in all_articles):
                    article_id = self.repo.upsert_article(item)
                    item.id = article_id
                    all_articles.append(item)
                    collected_count += 1
                    new_found = True

                    if limit and collected_count >= limit:
                        logger.info(f"已达到限制数量 {limit}")
                        return all_articles

            if not new_found and scroll_count > 3:
                # 连续多次滚动无新内容，认为已加载完毕
                logger.info("滚动加载无新内容，采集完成")
                break

            time.sleep(1)

        return all_articles

    def scroll_to_load_all(self) -> None:
        """滚动页面到底部，触发懒加载。"""
        page = self.browser_mgr.page
        assert page is not None

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    def parse_article_items(self) -> list[Article]:
        """从页面 DOM 解析文章列表项。

        Returns:
            文章列表。
        """
        page = self.browser_mgr.page
        assert page is not None

        articles: list[Article] = []

        # 微信后台素材列表的常见选择器
        selectors = [
            ".weui-desktop-card__bd .weui-desktop-table__row",
            ".appmsg_list .appmsg_item",
            ".table_wrp .tbody_row",
            "tr[data-id]",
        ]

        for selector in selectors:
            rows = page.query_selector_all(selector)
            if not rows:
                continue

            for row in rows:
                article = self._parse_dom_row(row)
                if article:
                    articles.append(article)
            break

        return articles

    def _parse_api_article(self, info: dict[str, Any]) -> Optional[Article]:
        """解析 API 返回的单篇文章信息。

        Args:
            info: API 返回的文章信息字典。

        Returns:
            Article 对象，解析失败返回 None。
        """
        try:
            title = info.get("title", "")
            url = info.get("link", "") or info.get("url", "")

            if not title or not url:
                return None

            # 发布时间（时间戳转 ISO 格式）
            create_time = info.get("create_time", 0)
            if create_time:
                publish_time = time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(int(create_time))
                )
            else:
                publish_time = None

            cover_url = info.get("cover_img", "") or info.get("cover", "")

            return Article(
                title=title,
                url=url,
                publish_time=publish_time,
                cover_image_url=cover_url if cover_url else None,
                crawl_status="pending",
            )
        except Exception as e:
            logger.warning(f"解析 API 文章信息失败: {e}")
            return None

    def _parse_dom_row(self, element: Any) -> Optional[Article]:
        """解析 DOM 行元素为 Article 对象。

        Args:
            element: Playwright ElementHandle。

        Returns:
            Article 对象，解析失败返回 None。
        """
        try:
            # 提取标题
            title_element = element.query_selector(
                ".weui-desktop-table__cell a, .appmsg_title a, .title a, a[class*='title']"
            )
            title = title_element.inner_text().strip() if title_element else ""

            # 提取链接
            url = ""
            if title_element:
                url = title_element.get_attribute("href") or ""

            if not url:
                link_element = element.query_selector("a[href]")
                if link_element:
                    url = link_element.get_attribute("href") or ""

            if not title or not url:
                return None

            # 提取发布时间
            time_element = element.query_selector(
                ".weui-desktop-table__cell .time, .update_time, .create_time, span[class*='time']"
            )
            publish_time = None
            if time_element:
                time_text = time_element.inner_text().strip()
                # 尝试解析常见格式
                publish_time = self._parse_time_str(time_text)

            # 提取封面图
            img_element = element.query_selector("img")
            cover_url = None
            if img_element:
                cover_url = (
                    img_element.get_attribute("data-src")
                    or img_element.get_attribute("src")
                )

            return Article(
                title=title,
                url=url,
                publish_time=publish_time,
                cover_image_url=cover_url,
                crawl_status="pending",
            )
        except Exception as e:
            logger.warning(f"解析 DOM 行元素失败: {e}")
            return None

    @staticmethod
    def _parse_time_str(time_str: str) -> Optional[str]:
        """解析时间字符串为 ISO 8601 格式。

        Args:
            time_str: 时间字符串（如 "2024-01-15" 或 "2024/01/15 12:30"）。

        Returns:
            ISO 8601 格式时间字符串，解析失败返回 None。
        """
        from datetime import datetime

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
            "%Y年%m月%d日",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(time_str.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue

        return None
