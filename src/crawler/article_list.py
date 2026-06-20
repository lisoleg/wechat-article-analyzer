"""文章列表采集模块 — ArticleListCrawler。

导航到微信公众号后台，通过已发表文章列表 API 获取全部文章，
解析每篇文章的标题、真实URL、发布时间，并 upsert 到数据库。

正确 API（含真实 content_url）：
https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin={begin}&count={count}&query=&type=101_1_102_103&token={token}&lang=zh_CN&f=json&ajax=1

响应结构（三层嵌套 JSON）：
  第1层: {"base_resp":{...}, "publish_page":"{\"total_count\":1897,\"publish_count\":...\"publish_list\":[...]}"}"
  第2层: json.loads(data["publish_page"]) -> {"total_count":1897, "publish_list":[{...}]}"
  第3层: 每条 publish_list 项的 publish_info 字段也是 JSON 字符串，需再次解析
        json.loads(item["publish_info"]) -> {"appmsg_info":[{"content_url":"https://...","title":"...",...}]}"
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from loguru import logger
from playwright.sync_api import Page

from src.crawler.browser import BrowserManager
from src.database import ArticleRepository
from src.models import Article


class ArticleListCrawler:
    """文章列表批量采集器（使用 appmsgpublish API）。

    属性:
        browser_mgr: 浏览器管理器。
        repo: 文章仓库。
        _token: 当前会话 token。
    """

    # 已发表文章列表 API（含真实 content_url）
    # type=101_1_102_103 表示已发表文章（非草稿）
    PUBLISH_API_TEMPLATE: str = (
        "https://mp.weixin.qq.com/cgi-bin/appmsgpublish?"
        "sub=list&begin={begin}&count={count}&query=&"
        "type=101_1_102_103&token={token}&lang=zh_CN&f=json&ajax=1"
    )

    # 素材管理页面入口（用于导航获取 token）
    MATERIAL_PAGE_URL: str = (
        "https://mp.weixin.qq.com/cgi-bin/appmsg?"
        "sub=list&t=media/appmsg_list&token={token}&lang=zh_CN"
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
        self._token: Optional[str] = None

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------
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

        # 导航到素材管理页面，确保浏览器在正确域名下并获取 token
        self._navigate_to_material_page()

        if not self._token:
            raise RuntimeError("未能获取 token，请确认登录状态")

        logger.info(f"开始获取文章列表 (token={self._token})")

        all_articles: list[Article] = []
        begin = 0
        count = 5  # 微信后台每页5条
        collected_count = 0
        total_count: Optional[int] = None

        while True:
            api_url = self.PUBLISH_API_TEMPLATE.format(
                begin=begin, count=count, token=self._token
            )
            logger.debug(f"请求文章列表 API: begin={begin}, count={count}")

            try:
                response_text = self._fetch_api_json(api_url)
                data = json.loads(response_text)

                # ---- 第1层解析：检查 base_resp ----
                base_resp = data.get("base_resp", {})
                err_code = base_resp.get("err_code", 0)
                if err_code != 0:
                    logger.error(
                        f"API 返回错误: err_code={err_code}, "
                        f"err_msg={base_resp.get('err_msg', '')}"
                    )
                    break

                # ---- 第1层解析：publish_page 是 JSON 字符串 ----
                publish_page_raw = data.get("publish_page", "")
                if not publish_page_raw:
                    logger.warning("publish_page 为空，采集完成")
                    break

                publish_data = json.loads(publish_page_raw)

                # 获取文章总数
                if total_count is None:
                    total_count = publish_data.get("total_count", 0)
                    logger.info(f"公众号共有 {total_count} 篇已发表文章")

                # ---- 第2层解析：publish_list ----
                publish_list = publish_data.get("publish_list", [])
                if not publish_list:
                    logger.info("publish_list 为空，采集完成")
                    break

                # ---- 第3层解析：每条 publish_info 也是 JSON 字符串 ----
                batch_new_count = 0  # 本批新增文章数
                for item in publish_list:
                    articles = self._parse_publish_item(item)
                    for article in articles:
                        if not article:
                            continue

                        # 断点续抓：跳过已入库且已完成的
                        if resume:
                            # 先按 URL 查
                            existing = self.repo.get_article_by_url(article.url)
                            # URL 未匹配时按 title + publish_time 查（tempkey 刷新场景）
                            if not existing:
                                existing = self.repo.get_article_by_title_and_time(
                                    article.title, article.publish_time
                                )

                            if existing and existing.crawl_status == "complete" and existing.content_text:
                                # 文章内容已完整，仅刷新 URL（如有变化）
                                if existing.url != article.url:
                                    self.repo.update_url(existing.id, article.url)
                                    logger.debug(f"已刷新 URL: {article.title[:30]}")
                                # 跳过：本批已有文章数不增加
                                continue

                        article_id = self.repo.upsert_article(article)
                        article.id = article_id
                        all_articles.append(article)
                        collected_count += 1
                        batch_new_count += 1

                        if limit and collected_count >= limit:
                            logger.info(f"已达到限制数量 {limit}")
                            return all_articles

                # 优化：如果本批没有新增文章（说明已追上 DB 进度），停止扫描
                if resume and batch_new_count == 0:
                    logger.info("本批无新增文章，已追上最新进度，停止扫描")
                    break

                begin += count

                # 检查是否已获取全部文章
                if total_count is not None and begin >= total_count:
                    logger.info(f"已获取全部 {total_count} 篇文章")
                    break

                # 间隔延迟防风控
                time.sleep(1)

            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败 (begin={begin}): {e}")
                logger.debug(f"响应内容（前500字符）: {response_text[:500] if 'response_text' in dir() else 'N/A'}")
                break
            except Exception as e:
                logger.error(f"API 请求失败 (begin={begin}): {e}")
                logger.exception("详细错误")
                break

        logger.info(f"文章列表获取完成，共 {len(all_articles)} 篇")
        return all_articles

    # ----------------------------------------------------------
    # 导航与 token 获取
    # ----------------------------------------------------------
    def _navigate_to_material_page(self) -> None:
        """导航到素材管理页面，确保浏览器在正确域名下并提取 token。

        登录后浏览器已在 mp.weixin.qq.com 域名下（带 token），
        直接从当前 URL 提取 token 并导航到素材管理页面。
        """
        page = self.browser_mgr.page
        assert page is not None

        # 先从当前 URL 提取 token
        self._token = self._extract_token_from_url(page.url)

        if self._token:
            # 直接导航到素材管理页面（带 token）
            material_url = self.MATERIAL_PAGE_URL.format(token=self._token)
            try:
                page.goto(material_url, wait_until="networkidle", timeout=30000)
                time.sleep(2)
                # 导航后重新提取 token（URL 可能变化）
                self._token = self._extract_token_from_url(page.url)
                logger.info(f"已导航到素材管理页面 (token={self._token})")
            except Exception as e:
                logger.warning(f"导航到素材管理页面时出现异常: {e}")
                # 尝试 domcontentloaded 作为后备
                try:
                    page.goto(material_url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)
                    self._token = self._extract_token_from_url(page.url)
                except Exception as e2:
                    logger.warning(f"后备导航也失败: {e2}")
        else:
            # 没有 token，尝试先导航到首页获取 token
            logger.warning("当前 URL 无 token，尝试导航到后台首页")
            try:
                page.goto("https://mp.weixin.qq.com/", wait_until="domcontentloaded")
                time.sleep(2)
                self._token = self._extract_token_from_url(page.url)
                if self._token:
                    material_url = self.MATERIAL_PAGE_URL.format(token=self._token)
                    page.goto(material_url, wait_until="domcontentloaded")
                    time.sleep(2)
                    self._token = self._extract_token_from_url(page.url)
                else:
                    logger.error("无法获取 token，请确认已登录")
            except Exception as e:
                logger.warning(f"导航过程中出现异常: {e}")

    @staticmethod
    def _extract_token_from_url(url: str) -> Optional[str]:
        """从 URL 中提取 token 参数。

        Args:
            url: 页面 URL。

        Returns:
            token 字符串，提取失败返回 None。
        """
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        token_list = params.get("token", [])
        return token_list[0] if token_list else None

    # ----------------------------------------------------------
    # API 请求辅助
    # ----------------------------------------------------------
    def _fetch_api_json(self, api_url: str) -> str:
        """通过 page.evaluate 发起 fetch 请求，返回响应文本。

        Args:
            api_url: 目标 API URL。

        Returns:
            响应文本（JSON 字符串）。

        Raises:
            RuntimeError: 浏览器页面未初始化。
        """
        page = self.browser_mgr.page
        assert page is not None

        response_text: str = page.evaluate(
            """
            async (url) => {
                const resp = await fetch(url, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Accept': 'application/json',
                    }
                });
                return await resp.text();
            }
            """,
            api_url,
        )
        return str(response_text)

    # ----------------------------------------------------------
    # 响应解析
    # ----------------------------------------------------------
    def _parse_publish_item(self, item: dict[str, Any]) -> list[Optional[Article]]:
        """解析单条 publish_list 项为 Article 对象列表。

        每条 publish_list 项对应一次群发（可能包含多篇文章），
        publish_info 字段是 JSON 字符串，需二次解析。

        Args:
            item: publish_list 中的单个项。

        Returns:
            Article 对象列表（一次群发可能包含多篇文章）。
        """
        articles: list[Optional[Article]] = []

        try:
            publish_info_raw = item.get("publish_info", "")
            if not publish_info_raw:
                return articles

            # 第3层解析：publish_info 是 JSON 字符串
            # 注意：有时已经是 dict，需要先判断
            if isinstance(publish_info_raw, str):
                publish_info = json.loads(publish_info_raw)
            else:
                publish_info = publish_info_raw

            # appmsg_info 是文章列表（一次群发可能有多篇）
            appmsg_info_list = publish_info.get("appmsg_info", [])
            if not appmsg_info_list:
                return articles

            for msg_info in appmsg_info_list:
                article = self._parse_appmsg_info(msg_info)
                articles.append(article)

        except json.JSONDecodeError as e:
            logger.warning(f"解析 publish_info JSON 失败: {e}")
            logger.debug(f"publish_info 内容（前200字符）: {str(item.get('publish_info', ''))[:200]}")
        except Exception as e:
            logger.warning(f"解析 publish_item 失败: {e}")

        return articles

    def _parse_appmsg_info(self, info: dict[str, Any]) -> Optional[Article]:
        """解析单篇文章信息（appmsg_info 列表中的单项）。

        Args:
            info: 文章信息字典。

        Returns:
            Article 对象，解析失败返回 None。
        """
        try:
            # 标题
            title = (
                info.get("title", "")
                or info.get("Title", "")
                or info.get("appMsgTitle", "")
            )
            title = title.strip() if title else ""

            # 真实文章 URL（content_url 是完整可访问的 URL）
            url = (
                info.get("content_url", "")
                or info.get("url", "")
                or info.get("link", "")
            )
            url = url.strip() if url else ""

            if not title:
                logger.debug(f"解析文章失败（无标题），可用键: {list(info.keys())}")
                return None

            if not url:
                logger.debug(f"解析文章失败（无URL），标题: {title[:30]}")
                return None

            # 调试：打印 API 返回的所有字段（用于确认 publish_time 字段名）
            logger.debug(f"_parse_appmsg_info 可用键: {list(info.keys())}")
            # 第一次调用时打印完整第一篇文章内容（用于找时间字段）
            if not hasattr(self, "_debug_logged"):
                import json as _json
                logger.info(f"[DEBUG] 第一篇文章完整内容:\n{_json.dumps(info, ensure_ascii=False, indent=2)[:500]}")
                self._debug_logged = True

            # 发布时间（时间戳转 ISO 格式）
            create_time = (
                info.get("create_time", 0)
                or info.get("CreateTime", 0)
                or info.get("update_time", 0)
                or info.get("published_time", 0)
                or info.get("publish_time", 0)
                or info.get("pub_time", 0)
            )
            if create_time:
                publish_time = time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(int(create_time))
                )
            else:
                publish_time = None

            # 封面图
            cover_url = (
                info.get("cover_img", "")
                or info.get("cover", "")
                or info.get("CoverImg", "")
                or info.get("thumb_url", "")
                or info.get("cover_img_url", "")
            )
            cover_url = cover_url.strip() if cover_url else ""

            return Article(
                title=title,
                url=url,
                publish_time=publish_time,
                cover_image_url=cover_url if cover_url else None,
                crawl_status="pending",
            )

        except Exception as e:
            logger.warning(f"解析文章信息失败: {e}")
            return None
