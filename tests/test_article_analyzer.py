"""ArticleAnalyzer 补充测试。

测试分析器核心逻辑：
- build_analysis_prompt：四大理论支柱注入、TOMAS/太极关键词注入、正文截断 8000 字符
- parse_analysis_response：JSON 响应解析、类型安全、默认值
- analyze_article：完整分析流程（mock DeepSeek 客户端）
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.article_analyzer import ArticleAnalyzer
from src.config import Config
from src.database import ArticleRepository, Database
from src.models import AnalysisResult, Article


@pytest.fixture
def setup():
    """创建临时数据库、仓库、配置和 mock 客户端。"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db = Database(db_path=db_path)
    db.init()
    repo = ArticleRepository(db)

    config = Config()
    # 确保四大理论支柱设置正确
    config.theory_pillars = ["刘原理", "三视界法", "太乙预言机", "全息拓扑动力学"]
    config.tomas_agi_keywords = ["TOMAS-AGI", "TOMAS", "AGI", "通用人工智能"]
    config.taiji_os_keywords = ["太极OS", "太极操作系统", "TaijiOS"]

    mock_client = MagicMock()

    analyzer = ArticleAnalyzer(mock_client, repo, config)

    yield analyzer, repo, mock_client, config

    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestBuildAnalysisPrompt:
    """build_analysis_prompt 测试。"""

    def test_prompt_contains_four_theory_pillars(self, setup):
        """测试 Prompt 包含四大理论支柱。"""
        analyzer, repo, _, config = setup
        article = Article(
            title="测试文章",
            url="https://example.com/1",
            content_text="这是正文内容。",
        )

        messages = analyzer.build_analysis_prompt(article)
        system_prompt = messages[0]["content"]

        assert messages[0]["role"] == "system"
        for pillar in config.theory_pillars:
            assert pillar in system_prompt

    def test_prompt_contains_tomas_keywords(self, setup):
        """测试 Prompt 包含 TOMAS-AGI 关键词。"""
        analyzer, _, _, config = setup
        article = Article(
            title="测试",
            url="https://example.com/2",
            content_text="正文",
        )

        messages = analyzer.build_analysis_prompt(article)
        system_prompt = messages[0]["content"]

        for kw in config.tomas_agi_keywords:
            assert kw in system_prompt

    def test_prompt_contains_taiji_keywords(self, setup):
        """测试 Prompt 包含太极OS 关键词。"""
        analyzer, _, _, config = setup
        article = Article(
            title="测试",
            url="https://example.com/3",
            content_text="正文",
        )

        messages = analyzer.build_analysis_prompt(article)
        system_prompt = messages[0]["content"]

        for kw in config.taiji_os_keywords:
            assert kw in system_prompt

    def test_prompt_contains_article_title(self, setup):
        """测试 User message 包含文章标题。"""
        analyzer, _, _, _ = setup
        article = Article(
            title="深度解析复合体理学",
            url="https://example.com/4",
            content_text="正文内容",
            publish_time="2024-06-01T10:00:00",
        )

        messages = analyzer.build_analysis_prompt(article)
        user_message = messages[1]["content"]

        assert messages[1]["role"] == "user"
        assert "深度解析复合体理学" in user_message
        assert "2024-06-01T10:00:00" in user_message

    def test_content_truncated_to_8000_chars(self, setup):
        """测试正文截断到 8000 字符。"""
        analyzer, _, _, _ = setup
        long_content = "A" * 10000
        article = Article(
            title="长文章",
            url="https://example.com/5",
            content_text=long_content,
        )

        messages = analyzer.build_analysis_prompt(article)
        user_message = messages[1]["content"]

        # 正文部分应该被截断为 8000 字符
        # user_message 还包含标题和发布时间，所以总长度 > 8000 但正文部分 = 8000
        assert "A" * 8000 in user_message
        assert "A" * 8001 not in user_message

    def test_content_under_limit_not_truncated(self, setup):
        """测试正文未超过限制时不截断。"""
        analyzer, _, _, _ = setup
        short_content = "短正文内容"
        article = Article(
            title="短文章",
            url="https://example.com/6",
            content_text=short_content,
        )

        messages = analyzer.build_analysis_prompt(article)
        user_message = messages[1]["content"]

        assert short_content in user_message

    def test_empty_content_handled(self, setup):
        """测试空正文不报错。"""
        analyzer, _, _, _ = setup
        article = Article(
            title="空文章",
            url="https://example.com/7",
            content_text=None,
        )

        messages = analyzer.build_analysis_prompt(article)
        user_message = messages[1]["content"]

        assert "正文内容" in user_message

    def test_max_content_length_is_8000(self, setup):
        """测试 MAX_CONTENT_LENGTH 常量值为 8000。"""
        analyzer, _, _, _ = setup
        assert analyzer.MAX_CONTENT_LENGTH == 8000

    def test_prompt_requests_json_format(self, setup):
        """测试 Prompt 要求 JSON 格式返回。"""
        analyzer, _, _, _ = setup
        article = Article(
            title="测试",
            url="https://example.com/8",
            content_text="正文",
        )

        messages = analyzer.build_analysis_prompt(article)
        system_prompt = messages[0]["content"]

        assert "JSON" in system_prompt
        assert "concepts" in system_prompt
        assert "keywords" in system_prompt
        assert "theory_pillars" in system_prompt
        assert "summary" in system_prompt
        assert "tomas_agi_related" in system_prompt
        assert "taiji_os_related" in system_prompt


class TestParseAnalysisResponse:
    """parse_analysis_response 测试。"""

    def test_parse_complete_response(self, setup):
        """测试解析完整的分析响应。"""
        analyzer, _, _, _ = setup
        response = {
            "concepts": ["概念A", "概念B", "概念C"],
            "keywords": ["关键词1", "关键词2"],
            "theory_pillars": ["刘原理", "三视界法"],
            "summary": "这是一篇关于理论的文章。",
            "tomas_agi_related": False,
            "taiji_os_related": True,
        }

        result = analyzer.parse_analysis_response(response, article_id=1)

        assert result.article_id == 1
        assert result.concepts == ["概念A", "概念B", "概念C"]
        assert result.keywords == ["关键词1", "关键词2"]
        assert result.theory_pillars == ["刘原理", "三视界法"]
        assert result.summary == "这是一篇关于理论的文章。"
        assert result.tomas_agi_related is False
        assert result.taiji_os_related is True
        assert result.analysis_status == "complete"

    def test_parse_with_defaults(self, setup):
        """测试缺失字段时使用默认值。"""
        analyzer, _, _, _ = setup
        response = {}

        result = analyzer.parse_analysis_response(response, article_id=5)

        assert result.article_id == 5
        assert result.concepts == []
        assert result.keywords == []
        assert result.theory_pillars == []
        assert result.summary == ""
        assert result.tomas_agi_related is False
        assert result.taiji_os_related is False

    def test_parse_type_safety_strings(self, setup):
        """测试非字符串元素被转为字符串。"""
        analyzer, _, _, _ = setup
        response = {
            "concepts": ["概念A", 123, None, "概念B"],
            "keywords": [True, "关键词"],
        }

        result = analyzer.parse_analysis_response(response, article_id=1)

        # None 被过滤掉，数字被转为字符串
        assert "123" in result.concepts
        assert "概念A" in result.concepts
        assert "概念B" in result.concepts
        assert None not in result.concepts
        assert "True" in result.keywords

    def test_parse_tomas_related_truthy(self, setup):
        """测试 tomas_agi_related 为 truthy 值时正确转换。"""
        analyzer, _, _, _ = setup
        response = {"tomas_agi_related": 1, "taiji_os_related": 0}

        result = analyzer.parse_analysis_response(response, article_id=1)

        assert result.tomas_agi_related is True
        assert result.taiji_os_related is False


class TestAnalyzeArticle:
    """analyze_article 完整流程测试（mock DeepSeek 客户端）。"""

    def test_analyze_success(self, setup):
        """测试分析成功流程。"""
        analyzer, repo, mock_client, _ = setup

        # 创建文章
        article = Article(
            title="测试文章",
            url="https://example.com/analyze/1",
            content_text="这是一篇测试文章的正文内容。",
        )
        article_id = repo.upsert_article(article)
        article.id = article_id

        # mock chat_json 返回
        mock_client.chat_json.return_value = {
            "concepts": ["概念A", "概念B"],
            "keywords": ["关键词"],
            "theory_pillars": ["刘原理"],
            "summary": "测试摘要",
            "tomas_agi_related": False,
            "taiji_os_related": True,
        }

        result = analyzer.analyze_article(article)

        assert result is not None
        assert result.analysis_status == "complete"
        assert result.concepts == ["概念A", "概念B"]
        assert result.taiji_os_related is True
        assert result.analysis_time is not None

        # 验证结果已保存到数据库
        saved = repo.get_analysis_result(article_id)
        assert saved is not None
        assert saved.analysis_status == "complete"

    def test_analyze_no_content_returns_none(self, setup):
        """测试无正文内容时返回 None。"""
        analyzer, _, _, _ = setup
        article = Article(
            title="无正文",
            url="https://example.com/analyze/2",
            content_text=None,
        )

        result = analyzer.analyze_article(article)
        assert result is None

    def test_analyze_api_failure_marks_failed(self, setup):
        """测试 API 调用失败时标记为 failed。"""
        analyzer, repo, mock_client, _ = setup

        article = Article(
            title="会失败的文章",
            url="https://example.com/analyze/3",
            content_text="正文内容",
        )
        article_id = repo.upsert_article(article)
        article.id = article_id

        mock_client.chat_json.side_effect = RuntimeError("API 调用失败")

        result = analyzer.analyze_article(article)

        assert result is None

        # 验证数据库中状态为 failed
        saved = repo.get_analysis_result(article_id)
        assert saved is not None
        assert saved.analysis_status == "failed"
        assert saved.analysis_error is not None
