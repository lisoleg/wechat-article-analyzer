"""日志配置模块 — LoggerSetup。

使用 loguru 实现日志，同时输出到控制台和文件。
文件输出每天轮转，保留 7 天。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger as _logger

if TYPE_CHECKING:
    from loguru import Logger as _LoguruLoggerType


class LoggerSetup:
    """loguru 日志初始化工具。

    使用方式::

        LoggerSetup.setup(level="INFO", log_file="./logs/app.log")
        from loguru import logger
        logger.info("Hello")
    """

    _initialized: bool = False

    @classmethod
    def setup(
        cls,
        level: str = "INFO",
        log_file: str = "./logs/app.log",
    ) -> None:
        """初始化日志配置：控制台 + 文件双输出。

        Args:
            level: 日志级别 — DEBUG / INFO / WARNING / ERROR。
            log_file: 日志文件路径。
        """
        # 避免重复初始化
        _logger.remove()

        # 控制台输出：彩色格式
        _logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

        # 文件输出：每天轮转，保留 7 天
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        _logger.add(
            str(log_path),
            level=level,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} - {message}"
            ),
            rotation="1 day",
            retention="7 days",
            encoding="utf-8",
        )

        cls._initialized = True

    @classmethod
    def get_logger(cls) -> "_LoguruLoggerType":
        """获取 loguru logger 实例。

        Returns:
            loguru.logger 对象。
        """
        if not cls._initialized:
            cls.setup()
        return _logger
