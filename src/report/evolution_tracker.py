"""理论演化脉络追踪模块 — EvolutionTracker。

按时间线追踪核心概念出现频率变化，生成时间线数据。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.analyzer.concepts import ConceptProcessor
from src.database import ArticleRepository


class EvolutionTracker:
    """理论演化脉络追踪器。

    按时间线追踪核心概念的出现频率变化，生成结构化时间线数据。

    Attributes:
        repo: 文章仓库。
        concept_proc: 概念处理器。
    """

    def __init__(
        self,
        repo: ArticleRepository,
        concept_proc: ConceptProcessor,
    ) -> None:
        """初始化演化追踪器。

        Args:
            repo: 文章仓库实例。
            concept_proc: 概念处理器实例。
        """
        self.repo: ArticleRepository = repo
        self.concept_proc: ConceptProcessor = concept_proc

    def track_evolution(
        self,
        top_concepts: Optional[list[tuple[str, int]]] = None,
    ) -> dict[str, Any]:
        """追踪核心概念的演化脉络。

        Args:
            top_concepts: 要追踪的概念列表（概念, 频次），
                          None 时自动取 Top 10。

        Returns:
            演化数据字典，包含 concepts / timeline / summary。
        """
        # 获取要追踪的概念
        if top_concepts is None:
            top_concepts = self.concept_proc.get_top_concepts(10)

        tracked_concepts = [concept for concept, _ in top_concepts]

        # 生成时间线
        timeline = self.generate_timeline(tracked_concepts)

        # 汇总分析
        summary = self._generate_evolution_summary(timeline, tracked_concepts)

        evolution_data: dict[str, Any] = {
            "tracked_concepts": tracked_concepts,
            "timeline": timeline,
            "summary": summary,
        }

        logger.info(
            f"理论演化追踪完成: {len(tracked_concepts)} 个概念, "
            f"{len(timeline)} 个时间点"
        )
        return evolution_data

    def generate_timeline(
        self,
        concepts: list[str],
    ) -> list[dict[str, Any]]:
        """生成指定概念的时间线数据。

        Args:
            concepts: 要追踪的概念列表。

        Returns:
            时间线列表，每项包含 time 和各概念的出现频次。
        """
        results = self.repo.get_all_analysis_results()
        articles = self.repo.get_all_articles()

        # 建立文章 ID → 发布时间 的映射
        # 优先使用 publish_time，缺失时降级使用 crawl_time（精确到月份）
        article_time_map: dict[int, str] = {}
        for a in articles:
            if not a.id:
                continue
            if a.publish_time and str(a.publish_time).strip():
                article_time_map[a.id] = str(a.publish_time)
            elif a.crawl_time and str(a.crawl_time).strip():
                # crawl_time 格式如 "2026-06-19T08:22:47.426366"，取前 7 位作为月份
                article_time_map[a.id] = str(a.crawl_time)[:7]
            else:
                article_time_map[a.id] = ""

        # 按月聚合概念频次
        from collections import defaultdict
        monthly_data: dict[str, dict[str, int]] = defaultdict(
            lambda: {c: 0 for c in concepts}
        )
        monthly_article_count: dict[str, int] = defaultdict(int)

        for result in results:
            publish_time = article_time_map.get(result.article_id, "")
            if not publish_time:
                continue

            month_key = publish_time[:7]  # YYYY-MM
            if len(month_key) < 7:
                continue

            monthly_article_count[month_key] += 1

            for concept in result.concepts:
                if concept in concepts:
                    monthly_data[month_key][concept] += 1

        # 按时间排序输出
        timeline: list[dict[str, Any]] = []
        for month_key in sorted(monthly_data.keys()):
            timeline.append({
                "time": month_key,
                "article_count": monthly_article_count[month_key],
                "concept_counts": monthly_data[month_key],
            })

        return timeline

    def export_json(
        self,
        evolution_data: dict[str, Any],
        path: str = "./output/evolution_timeline.json",
    ) -> None:
        """导出演化数据为 JSON 文件。

        Args:
            evolution_data: 演化数据字典。
            path: 输出路径。
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(evolution_data, f, ensure_ascii=False, indent=2)
        logger.info(f"理论演化数据已导出: {path}")

    def _generate_evolution_summary(
        self,
        timeline: list[dict[str, Any]],
        concepts: list[str],
    ) -> dict[str, Any]:
        """生成演化分析摘要。

        分析每个概念的首次出现时间、峰值时间和趋势。

        Args:
            timeline: 时间线数据。
            concepts: 追踪的概念列表。

        Returns:
            摘要字典。
        """
        summary: dict[str, Any] = {}

        for concept in concepts:
            first_seen: Optional[str] = None
            peak_time: Optional[str] = None
            peak_count: int = 0
            total_count: int = 0
            recent_trend: str = "stable"

            for item in timeline:
                count = item["concept_counts"].get(concept, 0)
                if count > 0:
                    if first_seen is None:
                        first_seen = item["time"]
                    if count > peak_count:
                        peak_count = count
                        peak_time = item["time"]
                    total_count += count

            # 判断近期趋势（比较最后两个时间点）
            if len(timeline) >= 2:
                last = timeline[-1]["concept_counts"].get(concept, 0)
                prev = timeline[-2]["concept_counts"].get(concept, 0)
                if last > prev:
                    recent_trend = "rising"
                elif last < prev:
                    recent_trend = "declining"

            summary[concept] = {
                "first_seen": first_seen,
                "peak_time": peak_time,
                "peak_count": peak_count,
                "total_count": total_count,
                "recent_trend": recent_trend,
            }

        return summary
