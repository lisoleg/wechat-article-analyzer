"""浏览器管理模块 — BrowserManager。

使用 Playwright sync API 管理 Chromium 浏览器生命周期。
支持 Cookie 持久化（save_cookies / load_cookies）。
默认非无头模式（用户需要扫码登录）。
使用持久化浏览器上下文（user_data_dir）保留登录态。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)


class BrowserManager:
    """Playwright 浏览器生命周期管理。

    使用持久化浏览器上下文保留登录态，避免重复扫码。
    Cookie 可导出 / 导入为 JSON 文件。

    Attributes:
        playwright: Playwright 实例。
        browser: 浏览器实例。
        context: 浏览器上下文。
        page: 当前页面。
    """

    def __init__(
        self,
        cookies_path: str = "./data/cookies.json",
        browser_data_dir: str = "./data/browser_data",
    ) -> None:
        """初始化浏览器管理器。

        Args:
            cookies_path: Cookie 持久化文件路径。
            browser_data_dir: 浏览器用户数据目录。
        """
        self.cookies_path: str = cookies_path
        self.browser_data_dir: str = browser_data_dir
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def launch(self, headless: bool = False) -> None:
        """启动浏览器，使用持久化上下文保留登录态。

        Args:
            headless: 是否无头模式，默认 False（用户需要扫码）。
        """
        # 确保用户数据目录存在
        Path(self.browser_data_dir).mkdir(parents=True, exist_ok=True)

        self.playwright = sync_playwright().start()

        # 使用 launch_persistent_context 保留登录态
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.browser_data_dir,
            headless=headless,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        # 尝试加载已有 cookies
        self.load_cookies(self.cookies_path)

        # 获取或创建页面
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        logger.info(f"浏览器已启动 (headless={headless})")

    def save_cookies(self, path: Optional[str] = None) -> None:
        """导出当前上下文 cookies 到 JSON 文件。

        Args:
            path: 保存路径，默认使用初始化时指定的路径。
        """
        save_path = path or self.cookies_path
        if self.context is None:
            logger.warning("浏览器上下文未初始化，无法保存 cookies")
            return

        cookies = self.context.cookies()
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        logger.info(f"Cookies 已保存到 {save_path} ({len(cookies)} 条)")

    def load_cookies(self, path: Optional[str] = None) -> bool:
        """从 JSON 文件加载 cookies。

        Args:
            path: 加载路径，默认使用初始化时指定的路径。

        Returns:
            是否成功加载（文件不存在或为空返回 False）。
        """
        load_path = path or self.cookies_path
        if not os.path.exists(load_path):
            logger.debug(f"Cookie 文件不存在: {load_path}")
            return False

        if self.context is None:
            logger.warning("浏览器上下文未初始化，无法加载 cookies")
            return False

        try:
            with open(load_path, "r", encoding="utf-8") as f:
                cookies: list[dict[str, Any]] = json.load(f)

            if not cookies:
                return False

            self.context.add_cookies(cookies)
            logger.info(f"已加载 {len(cookies)} 条 cookies")
            return True
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载 cookies 失败: {e}")
            return False

    def navigate(self, url: str) -> Page:
        """导航到指定 URL，返回 Page 对象。

        Args:
            url: 目标 URL。

        Returns:
            当前 Page 对象。

        Raises:
            RuntimeError: 浏览器未启动。
        """
        if self.page is None:
            raise RuntimeError("浏览器未启动，请先调用 launch()")
        logger.debug(f"导航到: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        return self.page

    def close(self) -> None:
        """关闭浏览器，释放资源。"""
        if self.context is not None:
            self.context.close()
            self.context = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None
        self.browser = None
        self.page = None
        logger.info("浏览器已关闭")
