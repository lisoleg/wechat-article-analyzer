#!/usr/bin/env python3
"""生成基于全量文章的理论收敛报告。"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import Database, ArticleRepository
from src.analyzer.concepts import ConceptProcessor
from src.analyzer.deepseek_client import DeepSeekClient
from src.report.convergence_report import ConvergenceReportGenerator
from src.report.concept_graph import ConceptGraphBuilder
import json

# Initialize database
db = Database(db_path='./data/articles.db')
db.init()
repo = ArticleRepository(db)
client = DeepSeekClient(api_key='sk-3a8cad32238c4ebbbb50968d5e802758')
concept_proc = ConceptProcessor(repo)
generator = ConvergenceReportGenerator(client, repo, concept_proc)

print('正在生成理论收敛报告（基于全量2001篇文章）...')
print('这可能需要 1-2 分钟...')

# Generate Markdown report
report = generator.generate_report('./output/report_full.md')
print(f'[OK] 报告已生成: output/report_full.md ({len(report)} 字符)')

# Generate JSON report
json_data = generator.generate_json_report(
    './output/report_full.json',
    generator._collect_summary_data(),
    report
)
print(f'[OK] 结构化数据已生成: output/report_full.json')

# Generate concept graph
print('\n正在生成概念关系图谱...')
builder = ConceptGraphBuilder(concept_proc)
graph = builder.build_graph(top_n=100)
builder.export_json(graph, './output/concept_graph_full.json')
builder.export_mermaid(graph, './output/concept_graph_full.md')
print(f'[OK] 概念图谱已生成: output/concept_graph_full.json')
print(f'[OK] Markdown图谱已生成: output/concept_graph_full.md')

# Print summary
stats = repo.get_stats()
print(f'\n=== 全量数据分析总结 ===')
print(f'总文章数: {stats["total"]}')
print(f'已分析: {stats["analyzed"]}')
print(f'概念关系: {stats["relations"]}')

# Show top 20 concepts
concept_freq = concept_proc.get_concept_frequency()
print(f'\n=== Top20 概念 ===')
for i, (concept, count) in enumerate(list(concept_freq.items())[:20], 1):
    print(f'{i:2d}. {concept}: {count}次')

print('\n[完成] 所有报告已生成！')
