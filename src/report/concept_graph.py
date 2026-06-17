"""概念关系图谱构建模块 — ConceptGraphBuilder。

基于概念共现矩阵构建图谱，取 Top N 关系，
生成 Mermaid 格式图谱，导出 JSON。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.analyzer.concepts import ConceptProcessor


class ConceptGraphBuilder:
    """概念关系图谱构建器。

    Attributes:
        concept_proc: 概念处理器。
    """

    def __init__(self, concept_proc: ConceptProcessor) -> None:
        """初始化图谱构建器。

        Args:
            concept_proc: 概念处理器实例。
        """
        self.concept_proc: ConceptProcessor = concept_proc

    def build_graph(self, top_n: int = 50) -> dict[str, Any]:
        """构建概念关系图谱。

        基于共现矩阵，取 Top N 关系构建图谱数据结构。

        Args:
            top_n: 取前 N 条关系。

        Returns:
            图谱数据字典，包含 nodes 和 edges。
        """
        # 获取共现矩阵
        co_occurrence = self.concept_proc.build_co_occurrence_matrix()

        # 按共现次数排序，取 Top N
        sorted_relations = sorted(
            co_occurrence.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]

        # 构建节点和边
        node_set: set[str] = set()
        edges: list[dict[str, Any]] = []

        for (concept_a, concept_b), count in sorted_relations:
            node_set.add(concept_a)
            node_set.add(concept_b)
            edges.append({
                "source": concept_a,
                "target": concept_b,
                "weight": count,
            })

        # 获取概念频次用于节点大小
        concept_freq = self.concept_proc.get_concept_frequency()
        nodes: list[dict[str, Any]] = []
        for concept in node_set:
            nodes.append({
                "id": concept,
                "label": concept,
                "frequency": concept_freq.get(concept, 0),
            })

        graph_data: dict[str, Any] = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "top_n": top_n,
            },
        }

        logger.info(
            f"概念图谱构建完成: {len(nodes)} 个节点, {len(edges)} 条边"
        )
        return graph_data

    def generate_mermaid(self, graph_data: dict[str, Any]) -> str:
        """生成 Mermaid 格式概念关系图。

        Args:
            graph_data: 图谱数据字典。

        Returns:
            Mermaid 格式的图谱文本。
        """
        lines: list[str] = ["graph TD"]

        # 添加节点定义（使用引号包裹包含特殊字符的节点名）
        for node in graph_data["nodes"]:
            node_id = self._sanitize_mermaid_id(node["id"])
            label = node["label"]
            freq = node["frequency"]
            lines.append(f'    {node_id}["{label} ({freq})"]')

        lines.append("")

        # 添加边
        for edge in graph_data["edges"]:
            source = self._sanitize_mermaid_id(edge["source"])
            target = self._sanitize_mermaid_id(edge["target"])
            weight = edge["weight"]
            lines.append(f"    {source} ---|{weight}| {target}")

        return "\n".join(lines)

    def export_json(
        self,
        graph_data: dict[str, Any],
        path: str = "./output/concept_graph.json",
    ) -> None:
        """导出图谱数据为 JSON 文件。

        Args:
            graph_data: 图谱数据字典。
            path: 输出路径。
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        logger.info(f"概念图谱 JSON 已导出: {path}")

    def export_mermaid(
        self,
        graph_data: dict[str, Any],
        path: str = "./output/concept_graph.mmd",
    ) -> None:
        """导出 Mermaid 图谱文件。

        Args:
            graph_data: 图谱数据字典。
            path: 输出路径。
        """
        mermaid_text = self.generate_mermaid(graph_data)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(mermaid_text)
        logger.info(f"概念图谱 Mermaid 已导出: {path}")

    @staticmethod
    def _sanitize_mermaid_id(concept: str) -> str:
        """将概念名转换为合法的 Mermaid 节点 ID。

        Mermaid 节点 ID 不能包含空格和特殊字符，
        使用 MD5 哈希的前 8 位作为 ID。

        Args:
            concept: 概念名称。

        Returns:
            合法的 Mermaid 节点 ID。
        """
        import hashlib
        return "n" + hashlib.md5(concept.encode("utf-8")).hexdigest()[:8]
