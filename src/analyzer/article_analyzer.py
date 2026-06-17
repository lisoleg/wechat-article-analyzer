"""单篇文章分析模块 — ArticleAnalyzer。

构建分析 Prompt（包含预定义四大理论支柱 + TOMAS-AGI/太极 OS 标注），
调用 DeepSeek API 获取 JSON 格式分析结果，解析为 AnalysisResult 对象并存储。

System prompt 包含预定义四大理论支柱。
User message 包含文章标题 + 发布时间 + 正文（截断 8000 字符）。
期望 JSON 响应：concepts, keywords, theory_pillars, summary,
tomas_agi_related, taiji_os_related。
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Optional

from loguru import logger

from src.analyzer.deepseek_client import DeepSeekClient
from src.config import Config
from src.database import ArticleRepository
from src.models import AnalysisResult, Article


class ArticleAnalyzer:
    """单篇文章分析器。

    Attributes:
        client: DeepSeek API 客户端。
        repo: 文章仓库。
        config: 配置对象。
    """

    # 正文截断长度（字符数）
    MAX_CONTENT_LENGTH: int = 8000

    # 分析 System Prompt 模板
    ANALYSIS_SYSTEM_PROMPT: str = (
        "你是一个理论分析专家。请分析以下微信公众号文章，提取核心概念、关键词，"
        "并从预定义的理论支柱中标注本文所属的理论支柱。\n"
        "预定义理论支柱：{theory_pillars}\n"
        "同时判断本文是否与TOMAS-AGI项目或太极OS项目相关。\n"
        "TOMAS-AGI相关关键词：{tomas_keywords}\n"
        "太极OS相关关键词：{taiji_keywords}\n\n"
        "请严格以JSON格式返回，格式如下：\n"
        "{{\n"
        '  "concepts": ["概念1", "概念2", "概念3"],\n'
        '  "keywords": ["关键词1", "关键词2"],\n'
        '  "theory_pillars": ["刘原理", "三视界法"],\n'
        '  "summary": "本文探讨了...",\n'
        '  "tomas_agi_related": false,\n'
        '  "taiji_os_related": true\n'
        "}}"
    )

    def __init__(
        self,
        client: DeepSeekClient,
        repo: ArticleRepository,
        config: Config,
    ) -> None:
        """初始化文章分析器。

        Args:
            client: DeepSeek API 客户端。
            repo: 文章仓库。
            config: 配置对象。
        """
        self.client: DeepSeekClient = client
        self.repo: ArticleRepository = repo
        self.config: Config = config

    def analyze_all(
        self,
        resume: bool = False,
        article_id: Optional[int] = None,
    ) -> None:
        """批量分析所有待分析文章。

        Args:
            resume: 断点续分析模式，True 时跳过已分析完成的文章。
            article_id: 指定单篇文章 ID 进行分析。
        """
        if article_id:
            article = self.repo.get_article(article_id)
            if not article:
                logger.error(f"文章 ID {article_id} 不存在")
                return
            if not article.content_text:
                logger.error(f"文章 {article_id} 无正文内容，请先采集")
                return
            articles = [article]
        else:
            if resume:
                # 续分析：获取 pending 和 failed 的文章
                pending = self.repo.get_articles_by_analysis_status("pending")
                # failed 的文章也需要重新分析
                articles = [a for a in pending if a.content_text]
            else:
                pending = self.repo.get_articles_by_analysis_status("pending")
                articles = [a for a in pending if a.content_text]

        if not articles:
            logger.info("没有待分析的文章")
            return

        logger.info(f"开始分析文章，共 {len(articles)} 篇")

        success_count = 0
        fail_count = 0

        for idx, article in enumerate(articles, start=1):
            logger.info(
                f"[{idx}/{len(articles)}] 正在分析: {article.title[:50]}..."
            )

            try:
                result = self.analyze_article(article)
                if result:
                    success_count += 1
                    logger.info(
                        f"[{idx}/{len(articles)}] 分析成功: {article.title[:50]}"
                    )
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(
                    f"[{idx}/{len(articles)}] 分析失败: {article.title[:50]} - {e}"
                )

            # API 调用间隔
            if idx < len(articles):
                time.sleep(0.5)

        logger.info(
            f"文章分析完成: 成功 {success_count} 篇, 失败 {fail_count} 篇"
        )

    def analyze_article(self, article: Article) -> Optional[AnalysisResult]:
        """分析单篇文章。

        Args:
            article: 待分析的文章对象（需含 content_text）。

        Returns:
            分析结果对象，失败返回 None。
        """
        if not article.content_text:
            logger.warning(f"文章 {article.id} 无正文内容，跳过分析")
            return None

        # 创建初始分析结果（状态为进行中）
        result = AnalysisResult(
            article_id=article.id or 0,
            analysis_status="in_progress",
        )
        self.repo.save_analysis_result(result)

        try:
            # 构建分析 Prompt
            messages = self.build_analysis_prompt(article)

            # 调用 DeepSeek API
            response_dict = self.client.chat_json(messages, temperature=0.3)

            # 解析响应
            result = self.parse_analysis_response(response_dict, article.id or 0)
            result.analysis_status = "complete"
            result.analysis_time = datetime.now().isoformat()

            # 保存结果
            self.repo.save_analysis_result(result)

            logger.debug(
                f"分析结果: concepts={result.concepts}, "
                f"pillars={result.theory_pillars}, "
                f"tomas={result.tomas_agi_related}, taiji={result.taiji_os_related}"
            )

            return result

        except Exception as e:
            error_msg = str(e)[:500]
            result.analysis_status = "failed"
            result.analysis_error = error_msg
            result.analysis_time = datetime.now().isoformat()
            self.repo.save_analysis_result(result)
            logger.error(f"文章 {article.id} 分析失败: {e}")
            return None

    def build_analysis_prompt(self, article: Article) -> list[dict[str, str]]:
        """构建发送给 DeepSeek 的 messages。

        Args:
            article: 文章对象。

        Returns:
            messages 列表，包含 system 和 user 消息。
        """
        # 构建 System prompt
        system_prompt = self.ANALYSIS_SYSTEM_PROMPT.format(
            theory_pillars="、".join(self.config.theory_pillars),
            tomas_keywords="、".join(self.config.tomas_agi_keywords),
            taiji_keywords="、".join(self.config.taiji_os_keywords),
        )

        # 截断正文
        content_text = (article.content_text or "")[: self.MAX_CONTENT_LENGTH]

        # 构建 User message
        user_message = (
            f"文章标题：{article.title}\n"
            f"发布时间：{article.publish_time or '未知'}\n"
            f"正文内容：\n{content_text}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

    def parse_analysis_response(
        self,
        response: dict,
        article_id: int = 0,
    ) -> AnalysisResult:
        """解析 API 返回的 JSON 为 AnalysisResult 对象。

        Args:
            response: API 返回的 JSON 字典。
            article_id: 关联的文章 ID。

        Returns:
            AnalysisResult 对象。
        """
        concepts: list[str] = response.get("concepts", [])
        keywords: list[str] = response.get("keywords", [])
        theory_pillars: list[str] = response.get("theory_pillars", [])
        summary: str = response.get("summary", "")
        tomas_related: bool = bool(response.get("tomas_agi_related", False))
        taiji_related: bool = bool(response.get("taiji_os_related", False))

        # 类型安全：确保列表中的元素都是字符串
        concepts = [str(c) for c in concepts if c]
        keywords = [str(k) for k in keywords if k]
        theory_pillars = [str(p) for p in theory_pillars if p]

        return AnalysisResult(
            article_id=article_id,
            concepts=concepts,
            keywords=keywords,
            theory_pillars=theory_pillars,
            summary=summary,
            tomas_agi_related=tomas_related,
            taiji_os_related=taiji_related,
            analysis_status="complete",
        )
