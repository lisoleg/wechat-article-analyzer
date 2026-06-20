"""理论收敛报告生成模块 — ConvergenceReportGenerator。

收集汇总数据（概念频次 Top50、理论支柱分布、演化时间线、TOMAS/太极 OS 相关文章），
调用 DeepSeek 生成 Markdown 报告，同时输出 JSON 结构化数据。
报告包含：核心理论框架、关键概念集群、概念演化路径、理论支柱总结。

v2.0 新增：跨理论体系对比分析，支持多理论体系并行对比。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.analyzer.concepts import ConceptProcessor
from src.analyzer.deepseek_client import DeepSeekClient
from src.config import Config
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

    # 跨理论体系对比 System Prompt
    CROSS_THEORY_SYSTEM_PROMPT: str = (
        "你是跨理论体系对比分析专家。基于以下多个理论体系的数据，"
        "进行跨体系对比分析，生成结构化报告。\n"
        "请以 Markdown 格式输出报告，包含以下部分：\n"
        "1. 各理论体系概览\n"
        "2. 共有概念分析（跨体系共享的核心概念）\n"
        "3. 独有概念分析（各体系特有的概念）\n"
        "4. 理论体系间关联性分析\n"
        "5. 综合结论\n\n"
        "报告应基于提供的数据进行分析，突出体系间的异同。"
    )

    def __init__(
        self,
        client: DeepSeekClient,
        repo: ArticleRepository,
        concept_proc: ConceptProcessor,
        config: Optional[Config] = None,
    ) -> None:
        """初始化报告生成器。

        Args:
            client: DeepSeek API 客户端。
            repo: 文章仓库。
            concept_proc: 概念处理器。
            config: 配置对象（用于读取理论体系定义，可选）。
        """
        self.client: DeepSeekClient = client
        self.repo: ArticleRepository = repo
        self.concept_proc: ConceptProcessor = concept_proc
        self.config: Optional[Config] = config

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
        for concept, count in list(summary_data["concept_frequency"].items())[:50]:
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

    # ----------------------------------------------------------
    # 跨理论体系对比（v2.0）
    # ----------------------------------------------------------
    def get_theory_systems(self) -> list[dict[str, Any]]:
        """获取理论体系列表。

        优先从数据库 theory_systems 表加载，若无则从配置文件加载。

        Returns:
            理论体系字典列表，每项包含 name / description / pillars / color_code。
        """
        # 1. 尝试从数据库加载
        db_systems = self.repo.get_all_theory_systems()
        if db_systems:
            return db_systems

        # 2. 从配置加载
        if self.config and hasattr(self.config, "theory_systems"):
            return self.config.theory_systems

        # 3. 降级：使用单一理论体系（theory_pillars）
        if self.config and hasattr(self.config, "theory_pillars"):
            return [
                {
                    "system_name": "默认理论体系",
                    "description": "基于配置的默认理论支柱",
                    "pillars": self.config.theory_pillars,
                    "color_code": "#000000",
                }
            ]

        return []

    def collect_cross_theory_data(self) -> dict[str, Any]:
        """收集跨理论体系对比数据。

        对每个理论体系，统计其支柱分布、相关概念频次、相关文章数。

        Returns:
            跨理论对比数据字典::

                {
                    "systems": [
                        {
                            "name": str,
                            "description": str,
                            "color_code": str,
                            "pillars": list[str],
                            "pillar_distribution": {pillar: count},
                            "total_articles": int,
                            "top_concepts": [(concept, count), ...],
                            "unique_concepts": list[str],
                        }
                    ],
                    "shared_concepts": list[str],   # 所有体系共有的概念
                    "all_concepts": set[str],       # 所有体系涉及的概念集合
                }
        """
        systems_config = self.get_theory_systems()
        results = self.repo.get_all_analysis_results()

        # 全局概念频次
        global_concept_freq: dict[str, int] = {}
        for result in results:
            for concept in result.concepts:
                global_concept_freq[concept] = global_concept_freq.get(concept, 0) + 1

        systems_data: list[dict[str, Any]] = []
        all_concept_sets: list[set[str]] = []

        for sys_config in systems_config:
            sys_name = sys_config.get("system_name") or sys_config.get("name", "")
            sys_pillars = sys_config.get("pillars", [])
            sys_color = sys_config.get("color_code", "#000000")
            sys_desc = sys_config.get("description", "")

            # 统计该体系支柱分布
            pillar_dist: dict[str, int] = {}
            sys_concept_freq: dict[str, int] = {}
            sys_article_count = 0

            for result in results:
                # 检查文章是否属于此体系（theory_pillars 有交集）
                matched_pillars = set(result.theory_pillars) & set(sys_pillars)
                if matched_pillars:
                    sys_article_count += 1
                    for pillar in matched_pillars:
                        pillar_dist[pillar] = pillar_dist.get(pillar, 0) + 1
                    for concept in result.concepts:
                        sys_concept_freq[concept] = sys_concept_freq.get(concept, 0) + 1

            # Top 20 概念
            top_concepts = sorted(
                sys_concept_freq.items(), key=lambda x: -x[1]
            )[:20]

            sys_concepts_set = set(sys_concept_freq.keys())
            all_concept_sets.append(sys_concepts_set)

            systems_data.append({
                "name": sys_name,
                "description": sys_desc,
                "color_code": sys_color,
                "pillars": sys_pillars,
                "pillar_distribution": pillar_dist,
                "total_articles": sys_article_count,
                "top_concepts": top_concepts,
                "concept_set": sys_concepts_set,
            })

        # 计算共有概念和所有概念
        all_concepts: set[str] = set()
        for s in all_concept_sets:
            all_concepts |= s

        shared_concepts: set[str] = set()
        if all_concept_sets:
            shared_concepts = set(all_concept_sets[0])  # copy to avoid mutating original
            for s in all_concept_sets[1:]:
                shared_concepts &= s

        # 计算各体系独有概念
        for i, sys_data in enumerate(systems_data):
            other_concepts: set[str] = set()
            for j, s in enumerate(all_concept_sets):
                if i != j:
                    other_concepts |= s
            sys_data["unique_concepts"] = sorted(
                sys_data["concept_set"] - other_concepts
            )
            # 清理内部字段
            del sys_data["concept_set"]

        return {
            "systems": systems_data,
            "shared_concepts": sorted(shared_concepts),
            "all_concepts_count": len(all_concepts),
        }

    def build_cross_theory_prompt(self, cross_data: dict[str, Any]) -> str:
        """构建跨理论体系对比报告的 Prompt。

        Args:
            cross_data: collect_cross_theory_data() 返回的数据。

        Returns:
            Prompt 字符串。
        """
        lines: list[str] = []

        for sys_data in cross_data["systems"]:
            lines.append(f"## 理论体系: {sys_data['name']}")
            lines.append(f"  描述: {sys_data['description']}")
            lines.append(f"  颜色: {sys_data['color_code']}")
            lines.append(f"  支柱: {', '.join(sys_data['pillars'])}")
            lines.append(f"  相关文章数: {sys_data['total_articles']}")

            # 支柱分布
            pillar_lines = [
                f"    - {p}: {c}篇"
                for p, c in sys_data["pillar_distribution"].items()
            ]
            lines.append(f"  支柱分布:\n" + "\n".join(pillar_lines))

            # Top 概念
            concept_lines = [
                f"    - {c}: {n}次"
                for c, n in sys_data["top_concepts"][:10]
            ]
            lines.append(f"  核心概念:\n" + "\n".join(concept_lines))

            # 独有概念
            if sys_data["unique_concepts"]:
                lines.append(
                    f"  独有概念: {', '.join(sys_data['unique_concepts'][:20])}"
                )
            lines.append("")

        # 共有概念
        shared = cross_data["shared_concepts"]
        lines.append(f"## 跨体系共有概念 ({len(shared)} 个)")
        if shared:
            lines.append(f"  {', '.join(shared[:30])}")
        else:
            lines.append("  无共有概念")

        lines.append(f"\n所有体系涉及概念总数: {cross_data['all_concepts_count']}")
        lines.append("\n请生成 Markdown 格式的跨理论体系对比分析报告。")

        return "\n".join(lines)

    def generate_cross_theory_report(
        self,
        output_path: str = "./output/cross_theory_report.md",
    ) -> str:
        """生成跨理论体系对比报告。

        Args:
            output_path: 报告输出路径。

        Returns:
            生成的 Markdown 报告文本。
        """
        # 1. 收集跨体系数据
        cross_data = self.collect_cross_theory_data()

        if not cross_data["systems"]:
            logger.warning("未配置理论体系，无法生成跨体系报告")
            report_text = "# 跨理论体系对比报告\n\n未配置理论体系，请先配置理论体系。\n"
            self._save_report(output_path, report_text)
            return report_text

        if len(cross_data["systems"]) == 1:
            logger.info("仅有一个理论体系，生成单体系分析报告")
            report_text = self._generate_single_system_report(cross_data)
            self._save_report(output_path, report_text)

            # 同时保存 JSON
            json_path = output_path.replace(".md", ".json")
            self._save_cross_theory_json(json_path, cross_data, report_text)
            return report_text

        # 2. 构建 Prompt
        prompt = self.build_cross_theory_prompt(cross_data)

        # 3. 调用 DeepSeek 生成报告
        logger.info("正在调用 DeepSeek 生成跨理论体系对比报告...")
        messages = [
            {"role": "system", "content": self.CROSS_THEORY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        report_text = self.client.chat(messages, temperature=0.7)

        # 4. 保存报告
        self._save_report(output_path, report_text)

        # 5. 保存 JSON
        json_path = output_path.replace(".md", ".json")
        self._save_cross_theory_json(json_path, cross_data, report_text)

        logger.info(f"跨理论体系报告已生成: {output_path}")
        logger.info(f"结构化数据已生成: {json_path}")

        return report_text

    def _generate_single_system_report(
        self, cross_data: dict[str, Any]
    ) -> str:
        """生成单体系分析报告（当仅有一个理论体系时）。

        Args:
            cross_data: 跨体系数据。

        Returns:
            Markdown 报告文本。
        """
        sys_data = cross_data["systems"][0]
        lines: list[str] = [
            f"# 跨理论体系对比报告\n",
            f"## 理论体系: {sys_data['name']}\n",
            f"**描述**: {sys_data['description']}\n",
            f"**颜色标识**: `{sys_data['color_code']}`\n",
            f"**理论支柱**: {', '.join(sys_data['pillars'])}\n",
            f"**相关文章数**: {sys_data['total_articles']}\n",
        ]

        # 支柱分布
        lines.append("### 支柱分布\n")
        lines.append("| 支柱 | 文章数 |")
        lines.append("|------|--------|")
        for pillar, count in sys_data["pillar_distribution"].items():
            lines.append(f"| {pillar} | {count} |")
        lines.append("")

        # 核心概念
        lines.append("### 核心概念 (Top 20)\n")
        lines.append("| 概念 | 频次 |")
        lines.append("|------|------|")
        for concept, count in sys_data["top_concepts"]:
            lines.append(f"| {concept} | {count} |")
        lines.append("")

        if sys_data["unique_concepts"]:
            lines.append("### 独有概念\n")
            lines.append(", ".join(sys_data["unique_concepts"][:50]))
            lines.append("")

        lines.append("---")
        lines.append("\n*当前仅配置了一个理论体系，如需跨体系对比，请添加更多理论体系。*")

        return "\n".join(lines)

    def _save_cross_theory_json(
        self,
        json_path: str,
        cross_data: dict[str, Any],
        report_text: str,
    ) -> None:
        """保存跨理论体系对比的 JSON 结构化数据。

        Args:
            json_path: JSON 文件路径。
            cross_data: 跨体系数据。
            report_text: Markdown 报告文本。
        """
        from datetime import datetime

        json_data: dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "total_systems": len(cross_data["systems"]),
            "shared_concepts": cross_data["shared_concepts"],
            "all_concepts_count": cross_data["all_concepts_count"],
            "systems": [],
            "report_markdown": report_text,
        }

        for sys_data in cross_data["systems"]:
            json_data["systems"].append({
                "name": sys_data["name"],
                "description": sys_data["description"],
                "color_code": sys_data["color_code"],
                "pillars": sys_data["pillars"],
                "pillar_distribution": sys_data["pillar_distribution"],
                "total_articles": sys_data["total_articles"],
                "top_concepts": [
                    {"concept": c, "count": n}
                    for c, n in sys_data["top_concepts"]
                ],
                "unique_concepts": sys_data["unique_concepts"],
            })

        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
