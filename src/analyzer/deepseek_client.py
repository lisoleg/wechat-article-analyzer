"""DeepSeek API 客户端模块 — DeepSeekClient。

使用 openai SDK 兼容模式（base_url 设为 https://api.deepseek.com/v1）。
支持 chat（文本响应）和 chat_json（JSON 格式响应）。
指数退避重试（1s → 2s → 4s），最多 3 次。
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional, TypeVar

from loguru import logger
from openai import OpenAI

T = TypeVar("T")


class DeepSeekClient:
    """DeepSeek API 客户端，兼容 OpenAI 格式。

    Attributes:
        api_key: API 密钥。
        model: 模型名称（默认 deepseek-chat）。
        base_url: API 基础 URL。
        max_retries: 最大重试次数。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        max_retries: int = 3,
    ) -> None:
        """初始化 DeepSeek 客户端。

        Args:
            api_key: API 密钥。
            model: 模型名称，默认 deepseek-chat。
            base_url: API 基础 URL。
            max_retries: 最大重试次数，默认 3。
        """
        self.api_key: str = api_key
        self.model: str = model
        self.base_url: str = base_url
        self.max_retries: int = max_retries
        self._client: OpenAI = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> str:
        """发送对话请求，返回文本响应。

        Args:
            messages: 消息列表，格式同 OpenAI Chat API。
            temperature: 温度参数，控制响应随机性。

        Returns:
            模型响应的文本内容。

        Raises:
            RuntimeError: 所有重试均失败后抛出。
        """
        def _do_chat() -> str:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            content = response.choices[0].message.content
            return content or ""

        return self._retry(_do_chat)

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """发送对话请求，要求 JSON 格式响应，返回解析后的 dict。

        在 messages 中追加 system 指令要求返回 JSON 格式。
        如果响应中包含 ```json 代码块，自动提取。
        解析失败时抛出 ValueError。

        Args:
            messages: 消息列表。
            temperature: 温度参数。

        Returns:
            解析后的 JSON 字典。

        Raises:
            ValueError: JSON 解析失败。
            RuntimeError: 所有重试均失败。
        """
        def _do_chat_json() -> dict[str, Any]:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or ""

            # 尝试直接解析
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

            # 尝试提取 ```json ... ``` 代码块
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                json_str = content[start:end].strip()
                return json.loads(json_str)

            # 尝试提取 { ... } 部分
            if "{" in content and "}" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                json_str = content[start:end]
                return json.loads(json_str)

            raise ValueError(f"无法解析 JSON 响应: {content[:200]}")

        return self._retry(_do_chat_json)

    def _retry(self, func: Callable[[], T]) -> T:
        """指数退避重试封装。

        重试间隔：1s → 2s → 4s，最多 max_retries 次。

        Args:
            func: 要重试的函数。

        Returns:
            函数返回值。

        Raises:
            RuntimeError: 所有重试均失败。
        """
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = 2 ** (attempt - 1)  # 1, 2, 4 秒
                    logger.warning(
                        f"API 调用失败（第 {attempt} 次），"
                        f"{wait_time} 秒后重试: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"API 调用失败，已达最大重试次数 {self.max_retries}: {e}")

        raise RuntimeError(
            f"API 调用失败，已达最大重试次数 {self.max_retries}"
        ) from last_exception
