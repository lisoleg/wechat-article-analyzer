"""理论收敛报告生成模块 — ConvergenceReportGenerator。

收集汇总数据（概念频次 Top50、理论支柱分布、演化时间线、TOMAS/太极 OS 相关文章），
调用 DeepSeek 生成 Markdown 报告，同时输出 JSON 结构化数据。
报告包含：核心理论框架、关键概念集群、概念演化路径、理论支柱总结。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.analyzer.concepts import ConceptProcessor
from src.analyzer.deepseek_client import DeepSeekClient
from src.database import ArticleRepository


class ConvergenceReportGenerator:
    """理论收敛报告生成器。

    Attributes:
        client: DeepSeek API 客户端。
        repo: 文章仓库。
        concept_proc: 概念处理器。
    """

    # 报告生成 System Prompt
    REPORT_SYSTEM_PROMPT: str = (
        "你是理论收敛分析专家。基于以下概念统计数据进行理论收敛分析，"
        "生成结构化理论收敛报告。\n"
        "请以 Markdown 格式输出报告，包含以下部分：\n"
        "1. 核心理论框架\n"
        "2. 关键概念集群\n"
        "3. 概念演化路径\n"
        "4. 理论支柱总结\n\n"
        "报告应基于提供的数据进行分析，不要泛泛而谈。"
    )

    def __init__(
        self,
        client: DeepSeekClient,
        repo: ArticleRepository,
        concept_proc: ConceptProcessor,
    ) -> None:
        """初始化报告生成器。

        Args:
            client: DeepSeek API 客户端。
            repo: 文章仓库。
            concept_proc: 概念处理器。
        """
        self.client: DeepSeekClient = client
        self.repo: ArticleRepository = repo
        self.concept_proc: ConceptProcessor = concept_proc

    def generate_report(self, output_path: str = "./output/report.md") -> str:
        """生成 Markdown 理论收敛报告。

        Args:
            output_path: 报告输出路径。

        Returns:
            生成的 Markdown 报告文本。
        """
        # 1. 收集汇总数据
        summary_data = self._collect_summary_data()

        if not summary_data["total_analyzed"]:
            logger.warning("没有已分析的文章，无法生成报告")
            report_text = "# 理论收敛报告\n\n暂无分析数据，请先执行文章分析。\n"
            self._save_report(output_path, report_text)
            return report_text

        # 2. 构建报告 Prompt
        prompt = self.build_report_prompt(summary_data)

        # 3. 调用 DeepSeek 生成报告
        logger.info("正在调用 DeepSeek 生成理论收敛报告...")
        messages = [
            {"role": "system", "content": self.REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        report_text = self.client.chat(messages, temperature=0.7)

        # 4. 保存 Markdown 报告
        self._save_report(output_path, report_text)

        # 5. 同时生成 JSON 结构化数据
        json_path = output_path.replace(".md", ".json")
        self.generate_json_report(json_path, summary_data, report_text)

        logger.info(f"理论收敛报告已生成: {output_path}")
        logger.info(f"结构化数据已生成: {json_path}")

        return report_text

    def generate_json_report(
        self,
        output_path: str = "./output/report.json",
        summary_data: Optional[dict[str, Any]] = None,
        report_text: str = "",
    ) -> dict[str, Any]:
        """生成 JSON 结构化报告数据。

        Args:
            output_path: JSON 输出路径。
            summary_data: 汇总数据（如未提供则重新收集）。
            report_text: Markdown 报告文本（可选）。

        Returns:
            结构化报告字典。
        """
        if summary_data is None:
            summary_data = self._collect_summary_data()

        json_report: dict[str, Any] = {
            "generated_at": summary_data.get("generated_at", ""),
            "total_articles": summary_data["total_articles"],
            "total_analyzed": summary_data["total_analyzed"],
            "concept_frequency_top50": summary_data["concept_frequency"],
            "pillar_distribution": summary_data["pillar_distribution"],
            "evolution_timeline": summary_data["evolution_timeline"],
            "tomas_agi_articles": summary_data["tomas_articles"],
            "taiji_os_articles": summary_data["taiji_articles"],
            "report_markdown": report_text,
        }

        # 保存 JSON
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)

        return json_report

    def build_report_prompt(self, summary_data: dict[str, Any]) -> str:
        """构建发送给 DeepSeek 的报告生成 Prompt。

        Args:
            summary_data: 汇总数据字典。

        Returns:
            Prompt 字符串。
        """
        # 概念频次 Top50
        concept_freq_lines: list[str] = []
        for concept, count in summary_data["concept_frequency"][:50]:
            concept_freq_lines.append(f"  - {concept}: {count}次")
        concept_freq_str = "\n".join(concept_freq_lines) if concept_freq_lines else "  暂无数据"

        # 理论支柱分布
        pillar_lines: list[str] = []
        for pillar, count in summary_data["pillar_distribution"].items():
            pillar_lines.append(f"  - {pillar}: {count}篇")
        pillar_str = "\n".join(pillar_lines) if pillar_lines else "  暂无数据"

        # 演化时间线（取最近 12 个时间点）
        evolution_lines: list[str] = []
        for item in summary_data["evolution_timeline"][-12:]:
            top_concepts = ", ".join(
                [f"{c}({n})" for c, n in list(item["concepts"].items())[:5]]
            )
            evolution_lines.append(f"  - {item['time']}: {top_concepts}")
        evolution_str = "\n".join(evolution_lines) if evolution_lines else "  暂无数据"

        # TOMAS-AGI 相关文章
        tomas_lines: list[str] = []
        for article in summary_data["tomas_articles"][:20]:
            tomas_lines.append(
                f"  - [{article['article_id']}] {article['title']}: {article['summary'][:80]}"
            )
        tomas_str = "\n".join(tomas_lines) if tomas_lines else "  暂无相关文章"

        # 太极 OS 相关文章
        taiji_lines: list[str] = []
        for article in summary_data["taiji_articles"][:20]:
            taiji_lines.append(
                f"  - [{article['article_id']}] {article['title']}: {article['summary'][:80]}"
            )
        taiji_str = "\n".join(taiji_lines) if taiji_lines else "  暂无相关文章"

        prompt = (
            f"基于以下 {summary_data['total_analyzed']} 篇文章的分析数据进行理论收敛分析：\n\n"
            f"## 概念频次 Top50\n{concept_freq_str}\n\n"
            f"## 理论支柱分布\n{pillar_str}\n\n"
            f"## 概念演化时间线（按月统计）\n{evolution_str}\n\n"
            f"## TOMAS-AGI 相关文章（共 {len(summary_data['tomas_articles'])} 篇）\n{tomas_str}\n\n"
            f"## 太极OS 相关文章（共 {len(summary_data['taiji_articles'])} 篇）\n{taiji_str}\n\n"
            f"请生成 Markdown 格式的理论收敛报告。"
        )

        return prompt

    def _collect_summary_data(self) -> dict[str, Any]:
        """收集报告所需的汇总数据。

        Returns:
            包含所有汇总数据的字典。
        """
        from datetime import datetime

        stats = self.repo.get_stats()
        concept_frequency = self.concept_proc.get_concept_frequency()
        pillar_distribution = self.concept_proc.get_pillar_distribution()
        evolution_timeline = self.concept_proc.get_concept_evolution()
        tomas_articles = self.concept_proc.get_tomas_articles()
        taiji_articles = self.concept_proc.get_taiji_articles()

        return {
            "generated_at": datetime.now().isoformat(),
            "total_articles": stats["total"],
            "total_analyzed": stats["analyzed"],
            "concept_frequency": concept_frequency,
            "pillar_distribution": pillar_distribution,
            "evolution_timeline": evolution_timeline,
            "tomas_articles": tomas_articles,
            "taiji_articles": taiji_articles,
        }

    @staticmethod
    def _save_report(output_path: str, report_text: str) -> None:
        """保存 Markdown 报告到文件。

        Args:
            output_path: 输出路径。
            report_text: 报告文本。
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
