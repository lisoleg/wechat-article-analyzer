"""进度显示模块 — ProgressDisplay。

基于 rich.Progress 封装，提供美观的终端进度条。
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)


class ProgressDisplay:
    """rich Progress 封装，支持多任务并行进度显示。

    使用方式::

        display = ProgressDisplay()
        task_id = display.create_task("采集进度", total=2000)
        for i in range(2000):
            display.update(task_id, advance=1)
        display.finish()
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        """初始化进度显示器。"""
        self.progress: Progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console or Console(),
        )

    def start(self) -> None:
        """启动进度显示。"""
        self.progress.start()

    def create_task(self, description: str, total: Optional[int] = None) -> TaskID:
        """创建一个进度任务。

        Args:
            description: 任务描述文本。
            total: 任务总量，None 表示不确定总量。

        Returns:
            任务 ID。
        """
        return self.progress.add_task(description, total=total)

    def update(
        self,
        task_id: TaskID,
        advance: float = 1.0,
        description: Optional[str] = None,
    ) -> None:
        """更新任务进度。

        Args:
            task_id: 任务 ID。
            advance: 前进的步数。
            description: 可选的新描述文本。
        """
        kwargs: dict = {"advance": advance}
        if description is not None:
            kwargs["description"] = description
        self.progress.update(task_id, **kwargs)

    def finish(self) -> None:
        """停止进度显示。"""
        self.progress.stop()

    def __enter__(self) -> "ProgressDisplay":
        """上下文管理器入口。"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口。"""
        self.finish()
