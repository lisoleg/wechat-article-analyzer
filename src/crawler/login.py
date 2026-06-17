"""登录处理模块 — LoginHandler。

负责微信公众号后台扫码登录、登录态检测、Cookie 持久化。
打开 mp.weixin.qq.com，等待用户扫码，轮询检测登录状态。
"""

from __future__ import annotations

import time
from typing import Optional

from loguru import logger

from src.crawler.browser import BrowserManager


class LoginTimeoutError(Exception):
    """登录超时异常。"""

    pass


class LoginHandler:
    """微信公众号后台扫码登录处理器。

    Attributes:
        browser_mgr: 浏览器管理器实例。
        login_url: 微信公众号后台登录 URL。
    """

    # 微信公众号后台 URL
    LOGIN_URL: str = "https://mp.weixin.qq.com/"
    # 登录成功后 URL 包含的标识（cgi-bin/home 表示已进入后台首页）
    LOGGED_IN_INDICATOR: str = "/cgi-bin/home"

    def __init__(
        self,
        browser_mgr: BrowserManager,
        login_timeout: int = 300,
        cookies_path: str = "./data/cookies.json",
    ) -> None:
        """初始化登录处理器。

        Args:
            browser_mgr: 浏览器管理器实例。
            login_timeout: 登录超时时间（秒），默认 300。
            cookies_path: Cookie 持久化路径。
        """
        self.browser_mgr: BrowserManager = browser_mgr
        self.login_timeout: int = login_timeout
        self.cookies_path: str = cookies_path
        self.login_url: str = self.LOGIN_URL

    def login(self, timeout: Optional[int] = None) -> bool:
        """执行登录流程：打开登录页 → 等待扫码 → 保存 cookies。

        Args:
            timeout: 超时时间（秒），None 则使用初始化时的默认值。

        Returns:
            登录是否成功。

        Raises:
            LoginTimeoutError: 登录超时。
        """
        actual_timeout = timeout or self.login_timeout

        # 启动浏览器
        self.browser_mgr.launch(headless=False)

        # 导航到登录页
        self.browser_mgr.navigate(self.login_url)

        # 检查是否已登录（cookie 有效）
        if self.check_login_status():
            logger.info("Cookie 有效，已自动登录")
            return True

        logger.info(f"等待用户扫码登录，超时时间 {actual_timeout} 秒...")

        # 等待登录完成
        if self.wait_for_login(actual_timeout):
            # 登录成功，保存 cookies
            self.browser_mgr.save_cookies(self.cookies_path)
            logger.info("登录成功，cookies 已保存")
            return True

        raise LoginTimeoutError(f"登录超时（{actual_timeout} 秒），请重新运行 login 命令")

    def check_login_status(self) -> bool:
        """检测当前是否已登录。

        通过检测当前 URL 是否从登录页跳转到后台首页来判断。

        Returns:
            是否已登录。
        """
        if self.browser_mgr.page is None:
            return False

        current_url = self.browser_mgr.page.url
        # 如果 URL 包含 cgi-bin/home 等后台路径，说明已登录
        if self.LOGGED_IN_INDICATOR in current_url:
            return True

        # 尝试检测页面是否有已登录的标识元素
        try:
            # 微信后台首页通常有特定元素
            element = self.browser_mgr.page.query_selector(".weui-desktop-account__nickname")
            if element:
                return True
        except Exception:
            pass

        return False

    def wait_for_login(self, timeout: int) -> bool:
        """轮询等待用户扫码登录。

        每隔 2 秒检测一次登录状态，直到超时。

        Args:
            timeout: 超时时间（秒）。

        Returns:
            是否在超时前登录成功。
        """
        start_time = time.time()
        poll_interval = 2  # 每 2 秒检测一次

        while time.time() - start_time < timeout:
            if self.check_login_status():
                return True
            time.sleep(poll_interval)

        return False
