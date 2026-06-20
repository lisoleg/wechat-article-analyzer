"""CLI 入口模块 — main.py。

使用 Click 框架定义命令组：
- login [--timeout 300]
- crawl [--resume] [--limit N]
- analyze [--resume] [--article-id N] [--incremental]
- report [--output path]
- graph [--output path]
- status
- config set/show

全局选项：--db-path, --log-level
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from src.config import Config
from src.database import ArticleRepository, Database
from src.utils.logger import LoggerSetup


# ============================================================
# 全局上下文对象
# ============================================================
class CliContext:
    """CLI 全局上下文，在各命令间共享配置和数据库连接。"""

    def __init__(self) -> None:
        self.config: Optional[Config] = None
        self.db: Optional[Database] = None
        self.repo: Optional[ArticleRepository] = None

    def init(self, config: Config) -> None:
        """初始化上下文。"""
        self.config = config
        self.db = Database(config.db_path)
        self.db.init()
        self.repo = ArticleRepository(self.db)
        # 初始化理论体系（如果表为空）
        self._init_theory_systems()

    def _init_theory_systems(self) -> None:
        """如果 theory_systems 表为空，从 theory_systems.json 导入默认体系。"""
        assert self.repo is not None
        existing = self.repo.get_all_theory_systems()
        if not existing:
            import json as _json
            config_path = Path("data/theory_systems.json")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    systems = _json.load(f)
                for name, info in systems.items():
                    self.repo.upsert_theory_system(
                        name=name,
                        description=info.get("description", ""),
                        pillars=info.get("pillars", []),
                        color_code=info.get("color_code", "#000000"),
                    )
                logger.info(f"已初始化 {len(systems)} 个理论体系")

    def close(self) -> None:
        """清理资源。"""
        if self.db is not None:
            self.db.close()


# ============================================================
# Click 命令组定义
# ============================================================
@click.group()
@click.option(
    "--db-path",
    default=None,
    help="SQLite 数据库路径（覆盖配置文件）",
)
@click.option(
    "--log-level",
    default=None,
    help="日志级别 DEBUG/INFO/WARNING/ERROR（覆盖配置文件）",
)
@click.pass_context
def cli(
    ctx: click.Context,
    db_path: Optional[str],
    log_level: Optional[str],
) -> None:
    """微信公众号文章采集与理论收敛分析工具。

    \b
    工作流程：
      1. login   — 扫码登录微信公众号后台
      2. crawl   — 采集文章列表与正文
      3. analyze — 使用 DeepSeek AI 分析文章
      4. report  — 生成理论收敛报告
      5. graph   — 构建概念关系图谱
      6. status  — 查看采集与分析进度
    """
    # 加载配置
    config = Config.load()

    # 命令行参数覆盖配置
    if db_path:
        config.set("db_path", db_path)
    if log_level:
        config.set("log_level", log_level)

    # 初始化日志
    LoggerSetup.setup(level=config.log_level, log_file=config.log_file)

    # 初始化上下文
    context = CliContext()
    context.init(config)
    ctx.obj = context


# ============================================================
# login 命令
# ============================================================
@cli.command()
@click.option(
    "--timeout",
    default=None,
    type=int,
    help="登录超时时间（秒），默认 300",
)
@click.pass_obj
def login(ctx: CliContext, timeout: Optional[int]) -> None:
    """扫码登录微信公众号后台。"""
    from src.crawler.browser import BrowserManager
    from src.crawler.login import LoginHandler, LoginTimeoutError

    assert ctx.config is not None
    actual_timeout = timeout or ctx.config.login_timeout

    browser_mgr = BrowserManager(
        cookies_path=ctx.config.cookies_path,
        browser_data_dir=ctx.config.browser_data_dir,
    )
    login_handler = LoginHandler(
        browser_mgr=browser_mgr,
        login_timeout=actual_timeout,
        cookies_path=ctx.config.cookies_path,
    )

    try:
        click.echo("正在启动浏览器，请准备扫码登录...")
        if login_handler.login(actual_timeout):
            click.echo(click.style("[OK] 登录成功！", fg="green"))
        else:
            click.echo(click.style("[FAIL] 登录失败", fg="red"))
            sys.exit(1)
    except LoginTimeoutError as e:
        click.echo(click.style(f"[FAIL] 登录超时: {e}", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"[FAIL] 登录出错: {e}", fg="red"))
        logger.exception("登录过程出错")
        sys.exit(1)
    finally:
        browser_mgr.close()


# ============================================================
# crawl 命令
# ============================================================
@cli.command()
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="断点续抓模式，跳过已完成的文章",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="限制采集数量（用于测试）",
)
@click.pass_obj
def crawl(ctx: CliContext, resume: bool, limit: Optional[int]) -> None:
    """采集文章列表与正文内容。"""
    from src.crawler.article_content import ArticleContentCrawler
    from src.crawler.article_list import ArticleListCrawler
    from src.crawler.browser import BrowserManager
    from src.crawler.login import LoginHandler, LoginTimeoutError

    assert ctx.config is not None
    assert ctx.repo is not None

    browser_mgr = BrowserManager(
        cookies_path=ctx.config.cookies_path,
        browser_data_dir=ctx.config.browser_data_dir,
    )
    login_handler = LoginHandler(
        browser_mgr=browser_mgr,
        login_timeout=ctx.config.login_timeout,
        cookies_path=ctx.config.cookies_path,
    )

    try:
        # 步骤1: 登录
        click.echo("步骤 1/3: 登录微信公众号后台...")
        login_handler.login(ctx.config.login_timeout)
        click.echo(click.style("[OK] 登录成功", fg="green"))

        # 步骤2: 获取文章列表
        click.echo("步骤 2/3: 获取文章列表...")
        list_crawler = ArticleListCrawler(browser_mgr, ctx.repo)
        articles = list_crawler.fetch_article_list(resume=resume, limit=limit)
        click.echo(
            click.style(
                f"[OK] 文章列表获取完成，共 {len(articles)} 篇",
                fg="green",
            )
        )

        # 强制刷新 DB，确保正文采集能查到新插入的文章
        ctx.repo.db.get_connection().commit()
        click.echo(f"[DEBUG] DB 已刷新，待采集文章数: {len(ctx.repo.get_articles_by_crawl_status('pending'))}")

        # 步骤3: 抓取正文
        click.echo("步骤 3/3: 采集文章正文...")
        content_crawler = ArticleContentCrawler(
            browser_mgr,
            ctx.repo,
            interval_min=ctx.config.crawl_interval_min,
            interval_max=ctx.config.crawl_interval_max,
        )
        content_crawler.fetch_all_content(resume=resume, limit=limit)

        stats = ctx.repo.get_stats()
        click.echo(
            click.style(
                f"\n[OK] 采集完成: 总计 {stats['total']} 篇, "
                f"成功 {stats['crawled']} 篇, "
                f"失败 {stats['crawl_failed']} 篇",
                fg="green",
            )
        )

        # 写结果到文件（utf-8），避免终端编码问题
        import os
        result_file = os.path.join(os.path.dirname(__file__), "..", "data", "last_crawl_result.txt")
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(f"采集完成\n")
            f.write(f"总计: {stats['total']} 篇\n")
            f.write(f"成功: {stats['crawled']} 篇\n")
            f.write(f"失败: {stats['crawl_failed']} 篇\n")
        click.echo(f"[DEBUG] 结果已写入: {result_file}")

    except LoginTimeoutError as e:
        click.echo(click.style(f"[FAIL] 登录超时: {e}", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"[FAIL] 采集出错: {e}", fg="red"))
        logger.exception("采集过程出错")
        sys.exit(1)
    finally:
        browser_mgr.close()


# ============================================================
# analyze 命令
# ============================================================
@cli.command()
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="断点续分析模式，跳过已分析的文章",
)
@click.option(
    "--article-id",
    default=None,
    type=int,
    help="分析指定文章 ID",
)
@click.option(
    "--incremental",
    is_flag=True,
    default=False,
    help="增量分析模式，只分析上次之后新增的文章",
)
@click.option(
    "--multi-model",
    is_flag=True,
    default=False,
    help="启用多模型交叉验证（需配置 MULTI_MODELS 环境变量或 config）",
)
@click.pass_obj
def analyze(
    ctx: CliContext,
    resume: bool,
    article_id: Optional[int],
    incremental: bool,
    multi_model: bool,
) -> None:
    """使用 DeepSeek AI 分析文章。"""
    from src.analyzer.article_analyzer import ArticleAnalyzer
    from src.analyzer.concepts import ConceptProcessor
    from src.analyzer.deepseek_client import DeepSeekClient

    assert ctx.config is not None
    assert ctx.repo is not None

    # 互斥检查
    if incremental and article_id:
        click.echo(
            click.style(
                "[FAIL] --incremental 和 --article-id 不能同时使用",
                fg="red",
            )
        )
        sys.exit(1)

    # 检查 API Key
    if not ctx.config.deepseek_api_key:
        click.echo(
            click.style(
                "[FAIL] 未配置 DeepSeek API Key，请通过环境变量 DEEPSEEK_API_KEY "
                "或 config set deepseek_api_key <key> 设置",
                fg="red",
            )
        )
        sys.exit(1)

    client = DeepSeekClient(
        api_key=ctx.config.deepseek_api_key,
        model=ctx.config.deepseek_model,
        base_url=ctx.config.deepseek_base_url,
    )
    analyzer = ArticleAnalyzer(client, ctx.repo, ctx.config)

    try:
        if multi_model:
            click.echo("开始多模型交叉验证...")
            from src.analyzer.multi_model import MultiModelValidator

            # 获取多模型配置
            models_config = ctx.config.multi_models
            # 处理字符串列表格式（来自逗号分隔环境变量）
            if models_config and isinstance(models_config[0], str):
                parsed = []
                for item in models_config:
                    parts = item.strip().split(":")
                    if len(parts) >= 2:
                        parsed.append({
                            "name": parts[0],
                            "api_key": parts[1],
                            "base_url": ctx.config.deepseek_base_url,
                            "model": parts[0],
                        })
                models_config = parsed

            if not models_config:
                click.echo(
                    click.style(
                        "[FAIL] 未配置多模型参数，请通过 config set multi_models "
                        "或环境变量 MULTI_MODELS 设置",
                        fg="red",
                    )
                )
                sys.exit(1)

            validator = MultiModelValidator(models_config, ctx.repo)

            # 获取待分析文章
            if article_id:
                target_article = ctx.repo.get_article(article_id)
                if not target_article:
                    click.echo(click.style(f"[FAIL] 文章 ID {article_id} 不存在", fg="red"))
                    sys.exit(1)
                articles = [target_article]
            else:
                articles = ctx.repo.get_articles_by_analysis_status("pending")
                articles = [a for a in articles if a.content_text]

            if not articles:
                click.echo("没有待验证的文章")
                return

            batch_result = validator.validate_batch(articles, analyzer)

            click.echo(
                click.style(
                    f"\n[OK] 多模型验证完成: "
                    f"成功 {batch_result['successful_articles']}/{batch_result['total_articles']} 篇, "
                    f"平均一致性 {batch_result['avg_consistency']:.4f}",
                    fg="green",
                )
            )
            click.echo(f"  共识概念: {', '.join(batch_result['all_consensus_concepts'][:20])}")
            click.echo(f"  共识支柱: {', '.join(batch_result['all_consensus_pillars'])}")
        elif incremental:
            click.echo("开始增量分析...")
            summary = analyzer.analyze_incremental()
            click.echo(
                click.style(
                    f"\n[OK] 增量分析完成: 分析了 {summary['articles_analyzed']} 篇新文章, "
                    f"新增概念 {summary['new_concepts']} 个, 跳过 {summary['skipped']} 篇",
                    fg="green",
                )
            )
            if summary["articles_analyzed"] == 0:
                click.echo("没有新文章需要分析")
        else:
            click.echo("开始文章分析...")
            analyzer.analyze_all(resume=resume, article_id=article_id)

        stats = ctx.repo.get_stats()
        click.echo(
            click.style(
                f"\n[OK] 分析完成: 成功 {stats['analyzed']} 篇, "
                f"失败 {stats['analyze_failed']} 篇",
                fg="green",
            )
        )

        # 保存概念关系
        if not article_id:
            click.echo("正在构建概念共现矩阵...")
            concept_proc = ConceptProcessor(ctx.repo)
            concept_proc.build_co_occurrence_matrix()
            click.echo(click.style("[OK] 概念共现矩阵已保存", fg="green"))

    except Exception as e:
        click.echo(click.style(f"[FAIL] 分析出错: {e}", fg="red"))
        logger.exception("分析过程出错")
        sys.exit(1)


# ============================================================
# report 命令
# ============================================================
@cli.command()
@click.option(
    "--output",
    default=None,
    help="报告输出路径（默认 ./output/report.md）",
)
@click.option(
    "--theory-system",
    default=None,
    help="指定理论体系名称（如 'TOMAS-AGI'），不指定则分析全部",
)
@click.option(
    "--cross-theory",
    is_flag=True,
    default=False,
    help="生成跨理论体系对比报告",
)
@click.pass_obj
def report(ctx: CliContext, output: Optional[str], theory_system: Optional[str], cross_theory: bool) -> None:
    """生成理论收敛报告。"""
    from src.analyzer.concepts import ConceptProcessor
    from src.analyzer.deepseek_client import DeepSeekClient
    from src.report.convergence_report import ConvergenceReportGenerator

    assert ctx.config is not None
    assert ctx.repo is not None

    output_path = output or f"{ctx.config.output_dir}/report.md"

    # 检查是否有分析数据
    stats = ctx.repo.get_stats()
    if stats["analyzed"] == 0:
        click.echo(
            click.style(
                "[FAIL] 没有已分析的文章，请先执行 analyze 命令",
                fg="red",
            )
        )
        sys.exit(1)

    # 检查 API Key
    if not ctx.config.deepseek_api_key:
        click.echo(
            click.style(
                "[FAIL] 未配置 DeepSeek API Key，请先设置",
                fg="red",
            )
        )
        sys.exit(1)

    # 处理 --theory-system 选项
    if theory_system:
        ts = ctx.repo.get_theory_system(theory_system)
        if not ts:
            click.echo(
                click.style(
                    f"[FAIL] 理论体系 '{theory_system}' 不存在，"
                    f"请使用 'theory-systems list' 查看可用体系",
                    fg="red",
                )
            )
            sys.exit(1)
        ctx.config.set("active_theory_system", theory_system)
        click.echo(f"使用理论体系: {theory_system} ({len(ts['pillars'])}个支柱)")
        output_path = output or f"{ctx.config.output_dir}/report_{theory_system}.md"

    client = DeepSeekClient(
        api_key=ctx.config.deepseek_api_key,
        model=ctx.config.deepseek_model,
        base_url=ctx.config.deepseek_base_url,
    )
    concept_proc = ConceptProcessor(ctx.repo)
    report_gen = ConvergenceReportGenerator(client, ctx.repo, concept_proc, ctx.config)

    try:
        if cross_theory:
            click.echo("正在生成跨理论体系对比报告...")
            cross_output = output or f"{ctx.config.output_dir}/cross_theory_report.md"
            report_text = report_gen.generate_cross_theory_report(cross_output)
            output_path = cross_output
        else:
            click.echo("正在生成理论收敛报告...")
            report_text = report_gen.generate_report(output_path)
        click.echo(
            click.style(
                f"\n[OK] 报告已生成: {output_path}",
                fg="green",
            )
        )
        click.echo(
            f"  JSON 数据: {output_path.replace('.md', '.json')}"
        )
    except Exception as e:
        click.echo(click.style(f"[FAIL] 报告生成出错: {e}", fg="red"))
        logger.exception("报告生成过程出错")
        sys.exit(1)


# ============================================================
# graph 命令
# ============================================================
@cli.command()
@click.option(
    "--output",
    default=None,
    help="图谱输出路径（默认 ./output/concept_graph.json）",
)
@click.option(
    "--top-n",
    default=50,
    type=int,
    help="取 Top N 关系构建图谱",
)
@click.pass_obj
def graph(
    ctx: CliContext,
    output: Optional[str],
    top_n: int,
) -> None:
    """构建概念关系图谱。"""
    from src.analyzer.concepts import ConceptProcessor
    from src.report.concept_graph import ConceptGraphBuilder

    assert ctx.config is not None
    assert ctx.repo is not None

    output_path = output or f"{ctx.config.output_dir}/concept_graph.json"

    concept_proc = ConceptProcessor(ctx.repo)
    graph_builder = ConceptGraphBuilder(concept_proc)

    try:
        click.echo(f"正在构建概念关系图谱 (Top {top_n})...")
        graph_data = graph_builder.build_graph(top_n=top_n)

        # 导出 JSON
        graph_builder.export_json(graph_data, output_path)

        # 导出 Mermaid
        mermaid_path = output_path.replace(".json", ".mmd")
        graph_builder.export_mermaid(graph_data, mermaid_path)

        click.echo(
            click.style(
                f"\n[OK] 概念图谱已生成:",
                fg="green",
            )
        )
        click.echo(f"  JSON: {output_path}")
        click.echo(f"  Mermaid: {mermaid_path}")
        click.echo(
            f"  节点数: {graph_data['metadata']['total_nodes']}, "
            f"边数: {graph_data['metadata']['total_edges']}"
        )
    except Exception as e:
        click.echo(click.style(f"[FAIL] 图谱构建出错: {e}", fg="red"))
        logger.exception("图谱构建过程出错")
        sys.exit(1)


# ============================================================
# status 命令
# ============================================================
@cli.command()
@click.pass_obj
def status(ctx: CliContext) -> None:
    """查看采集与分析进度。"""
    assert ctx.repo is not None

    stats = ctx.repo.get_stats()

    console = Console()
    table = Table(title="采集与分析进度", show_header=True, header_style="bold cyan")
    table.add_column("指标", style="cyan", no_wrap=True)
    table.add_column("数量", justify="right", style="magenta")

    table.add_row("文章总数", str(stats["total"]))
    table.add_row("采集完成", str(stats["crawled"]))
    table.add_row("待采集", str(stats["crawl_pending"]))
    table.add_row("采集失败", str(stats["crawl_failed"]))
    table.add_row("分析完成", str(stats["analyzed"]))
    table.add_row("分析失败", str(stats["analyze_failed"]))

    console.print(table)

    # 计算进度百分比
    if stats["total"] > 0:
        crawl_pct = (stats["crawled"] / stats["total"]) * 100
        click.echo(f"\n采集进度: {crawl_pct:.1f}%")
    if stats["crawled"] > 0:
        analyze_pct = (stats["analyzed"] / stats["crawled"]) * 100
        click.echo(f"分析进度: {analyze_pct:.1f}%")


# ============================================================
# standardize 命令
# ============================================================
@cli.command()
@click.option(
    "--similarity-threshold",
    default=0.8,
    type=float,
    help="聚类相似度阈值（0.0–1.0），默认 0.8",
)
@click.option(
    "--update-results",
    is_flag=True,
    default=False,
    help="更新 analysis_results 中的概念为标准化后概念",
)
@click.option(
    "--rebuild-graph",
    is_flag=True,
    default=False,
    help="标准化后重建概念共现矩阵",
)
@click.pass_obj
def standardize(
    ctx: CliContext,
    similarity_threshold: float,
    update_results: bool,
    rebuild_graph: bool,
) -> None:
    """概念标准化 — 两阶段（同义词映射 + TF-IDF 聚类）。"""
    from src.standardizer.standardizer_pipeline import StandardizerPipeline

    assert ctx.config is not None
    assert ctx.repo is not None

    pipeline = StandardizerPipeline(
        ctx.repo,
        dict_path="./data/synonym_dict.json",
        similarity_threshold=similarity_threshold,
    )

    try:
        click.echo("开始概念标准化...")
        summary = pipeline.standardize_all(
            save_mappings=True,
            update_results=update_results,
        )

        click.echo(
            click.style(
                f"\n[OK] 标准化完成:",
                fg="green",
            )
        )
        click.echo(f"  原始概念数: {summary['total_concepts']}")
        click.echo(f"  规则映射: {summary['mapped_by_rules']} 个")
        click.echo(f"  聚类映射: {summary['mapped_by_clustering']} 个")
        click.echo(f"  标准化后: {summary['final_concepts']} 个概念")
        click.echo(f"  新保存映射: {summary['new_mappings']} 条")

        if rebuild_graph:
            click.echo("正在重建概念共现矩阵...")
            pipeline.rebuild_co_occurrence_matrix()
            click.echo(click.style("[OK] 共现矩阵已重建", fg="green"))

    except Exception as e:
        click.echo(click.style(f"[FAIL] 标准化出错: {e}", fg="red"))
        logger.exception("标准化过程出错")
        sys.exit(1)


# ============================================================
# theory-systems 命令组
# ============================================================
@cli.group()
def theory_systems() -> None:
    """理论体系管理。"""
    pass


@theory_systems.command(name="list")
@click.pass_obj
def theory_list(ctx: CliContext) -> None:
    """列出所有理论体系。"""
    assert ctx.repo is not None
    systems = ctx.repo.get_all_theory_systems()
    if not systems:
        click.echo("暂无理论体系")
        return
    for s in systems:
        click.echo(f"  [{s['id']}] {s['system_name']} ({len(s['pillars'])}个支柱)")
        click.echo(f"    {s['description']}")


@theory_systems.command(name="add")
@click.argument("name")
@click.argument("description")
@click.argument("pillars")  # 逗号分隔
@click.option("--color", default="#000000", help="颜色代码")
@click.pass_obj
def theory_add(ctx: CliContext, name: str, description: str, pillars: str, color: str) -> None:
    """添加理论体系。"""
    assert ctx.repo is not None
    pillar_list = [p.strip() for p in pillars.split(",")]
    ctx.repo.upsert_theory_system(name, description, pillar_list, color)
    click.echo(click.style(f"[OK] 已添加理论体系: {name}", fg="green"))


@theory_systems.command(name="remove")
@click.argument("id", type=int)
@click.pass_obj
def theory_remove(ctx: CliContext, id: int) -> None:
    """删除理论体系。"""
    assert ctx.repo is not None
    if ctx.repo.delete_theory_system(id):
        click.echo(click.style(f"[OK] 已删除理论体系 ID={id}", fg="green"))
    else:
        click.echo(click.style(f"[FAIL] 理论体系 ID={id} 不存在", fg="red"))


# ============================================================
# config 命令组
# ============================================================
@cli.group()
def config() -> None:
    """配置管理。"""
    pass


@config.command(name="show")
@click.pass_obj
def config_show(ctx: CliContext) -> None:
    """显示当前配置。"""
    assert ctx.config is not None

    config_dict = ctx.config.to_dict()
    # 隐藏 API Key 中间部分
    api_key = config_dict.get("deepseek_api_key", "")
    if api_key and len(api_key) > 8:
        config_dict["deepseek_api_key"] = (
            api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        )

    console = Console()
    table = Table(title="当前配置", show_header=True, header_style="bold cyan")
    table.add_column("配置项", style="cyan", no_wrap=True)
    table.add_column("值", style="white")

    for key, value in config_dict.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        table.add_row(key, value_str)

    console.print(table)


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def config_set(ctx: CliContext, key: str, value: str) -> None:
    """设置配置项。

    KEY 为配置键名，VALUE 为配置值。
    布尔值使用 true/false，列表使用逗号分隔。
    """
    assert ctx.config is not None

    # 类型转换
    current_value = ctx.config.get(key)
    if isinstance(current_value, bool):
        converted = value.lower() in ("true", "1", "yes")
    elif isinstance(current_value, int):
        converted = int(value)
    elif isinstance(current_value, float):
        converted = float(value)
    elif isinstance(current_value, list):
        converted = [v.strip() for v in value.split(",")]
    else:
        converted = value

    ctx.config.set(key, converted)
    click.echo(click.style(f"[OK] 已设置 {key} = {converted}", fg="green"))


# ============================================================
# serve 命令
# ============================================================
@cli.command(name="serve")
@click.option("--host", default="0.0.0.0", help="监听地址")
@click.option("--port", default=8000, help="监听端口")
@click.option("--db", default="data/articles.db", help="数据库路径")
@click.pass_obj
def serve(ctx: CliContext, host: str, port: int, db: str) -> None:
    """启动 REST API 服务器。"""
    import uvicorn

    click.echo(click.style(f"[OK] API 服务器启动: http://{host}:{port}", fg="green"))
    click.echo(click.style(f"    数据库: {db}", fg="green"))
    click.echo(click.style(f"    API 文档: http://{host}:{port}/docs", fg="green"))

    # 关闭 CLI 的数据库连接（API 会自己管理）
    ctx.close()

    uvicorn.run(
        "src.api.app:create_app",
        host=host,
        port=port,
        factory=True,
        reload=False,
    )


# ============================================================
# 程序入口
# ============================================================
if __name__ == "__main__":
    cli()
