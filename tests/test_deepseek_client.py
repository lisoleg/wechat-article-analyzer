"""DeepSeek 客户端测试（mock 测试）。

使用 mock 模拟 DeepSeek API 调用，测试重试逻辑和 JSON 解析。
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.deepseek_client import DeepSeekClient


class TestDeepSeekClientChat:
    """chat() 方法测试。"""

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_success(self, mock_openai_class):
        """测试 chat 成功调用。"""
        # 配置 mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Hello from AI"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # 测试
        client = DeepSeekClient(api_key="test-key")
        result = client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.5,
        )

        assert result == "Hello from AI"
        mock_client.chat.completions.create.assert_called_once()

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_retry_on_failure(self, mock_openai_class):
        """测试 chat 失败时指数退避重试。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="成功响应"))
        ]

        # 前两次失败，第三次成功
        mock_client.chat.completions.create.side_effect = [
            Exception("网络错误"),
            Exception("超时"),
            mock_response,
        ]

        client = DeepSeekClient(api_key="test-key", max_retries=3)

        with patch("src.analyzer.deepseek_client.time.sleep") as mock_sleep:
            result = client.chat(messages=[{"role": "user", "content": "Hi"}])

        assert result == "成功响应"
        assert mock_client.chat.completions.create.call_count == 3
        # 验证指数退避等待（1s, 2s）
        assert mock_sleep.call_count == 2

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_all_retries_failed(self, mock_openai_class):
        """测试所有重试均失败时抛出异常。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("持续失败")

        client = DeepSeekClient(api_key="test-key", max_retries=3)

        with patch("src.analyzer.deepseek_client.time.sleep"):
            with pytest.raises(RuntimeError) as exc_info:
                client.chat(messages=[{"role": "user", "content": "Hi"}])

        assert "最大重试次数" in str(exc_info.value)
        assert mock_client.chat.completions.create.call_count == 3

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_empty_content(self, mock_openai_class):
        """测试空内容响应。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        client = DeepSeekClient(api_key="test-key")
        result = client.chat(messages=[{"role": "user", "content": "Hi"}])

        assert result == ""


class TestDeepSeekClientChatJson:
    """chat_json() 方法测试。"""

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_json_success(self, mock_openai_class):
        """测试 chat_json 成功解析 JSON。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        json_response = {
            "concepts": ["概念A", "概念B"],
            "keywords": ["关键词1"],
            "theory_pillars": ["刘原理"],
            "summary": "测试摘要",
            "tomas_agi_related": False,
            "taiji_os_related": True,
        }
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(json_response)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        client = DeepSeekClient(api_key="test-key")
        result = client.chat_json(
            messages=[{"role": "user", "content": "分析"}]
        )

        assert result["concepts"] == ["概念A", "概念B"]
        assert result["keywords"] == ["关键词1"]
        assert result["theory_pillars"] == ["刘原理"]
        assert result["tomas_agi_related"] is False
        assert result["taiji_os_related"] is True

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_json_with_code_block(self, mock_openai_class):
        """测试包含 ```json 代码块的响应解析。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        json_data = {"key": "value"}
        content = f"这是分析结果：\n```json\n{json.dumps(json_data)}\n```\n以上。"
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=content))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        client = DeepSeekClient(api_key="test-key")
        result = client.chat_json(
            messages=[{"role": "user", "content": "分析"}]
        )

        assert result == json_data

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_json_with_inline_braces(self, mock_openai_class):
        """测试包含内联花括号的响应解析。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        json_data = {"concepts": ["A", "B"]}
        content = f"分析结果如下：{json.dumps(json_data, ensure_ascii=False)} 完毕"
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=content))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        client = DeepSeekClient(api_key="test-key")
        result = client.chat_json(
            messages=[{"role": "user", "content": "分析"}]
        )

        assert result["concepts"] == ["A", "B"]

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_chat_json_retry_on_parse_failure(self, mock_openai_class):
        """测试 JSON 解析失败时重试。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        good_response = MagicMock()
        good_response.choices = [
            MagicMock(message=MagicMock(content='{"key": "value"}'))
        ]

        # 第一次返回无法解析的内容，第二次返回有效 JSON
        bad_response = MagicMock()
        bad_response.choices = [
            MagicMock(message=MagicMock(content="这不是JSON"))
        ]
        mock_client.chat.completions.create.side_effect = [
            bad_response,
            good_response,
        ]

        client = DeepSeekClient(api_key="test-key", max_retries=3)

        with patch("src.analyzer.deepseek_client.time.sleep"):
            result = client.chat_json(
                messages=[{"role": "user", "content": "分析"}]
            )

        assert result == {"key": "value"}
        assert mock_client.chat.completions.create.call_count == 2


class TestDeepSeekClientInit:
    """客户端初始化测试。"""

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_init_with_defaults(self, mock_openai_class):
        """测试默认参数初始化。"""
        client = DeepSeekClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert client.model == "deepseek-chat"
        assert client.base_url == "https://api.deepseek.com/v1"
        assert client.max_retries == 3

    @patch("src.analyzer.deepseek_client.OpenAI")
    def test_init_with_custom_params(self, mock_openai_class):
        """测试自定义参数初始化。"""
        client = DeepSeekClient(
            api_key="custom-key",
            model="deepseek-reasoner",
            base_url="https://custom.api.com/v1",
            max_retries=5,
        )

        assert client.api_key == "custom-key"
        assert client.model == "deepseek-reasoner"
        assert client.base_url == "https://custom.api.com/v1"
        assert client.max_retries == 5
