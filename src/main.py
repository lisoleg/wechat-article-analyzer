"""CLI 入口模块 — main.py。

使用 Click 框架定义命令组：
- login [--timeout 300]
- crawl [--resume] [--limit N]
- analyze [--resume] [--article-id N]
- report [--output path]
- graph [--output path]
- status
- config set/show

全局选项：--db-path, --log-level
"""

from __future__ import annotations

import json
import sys
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
@click.pass_obj
def analyze(
    ctx: CliContext,
    resume: bool,
    article_id: Optional[int],
) -> None:
    """使用 DeepSeek AI 分析文章。"""
    from src.analyzer.article_analyzer import ArticleAnalyzer
    from src.analyzer.concepts import ConceptProcessor
    from src.analyzer.deepseek_client import DeepSeekClient

    assert ctx.config is not None
    assert ctx.repo is not None

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
@click.pass_obj
def report(ctx: CliContext, output: Optional[str]) -> None:
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

    client = DeepSeekClient(
        api_key=ctx.config.deepseek_api_key,
        model=ctx.config.deepseek_model,
        base_url=ctx.config.deepseek_base_url,
    )
    concept_proc = ConceptProcessor(ctx.repo)
    report_gen = ConvergenceReportGenerator(client, ctx.repo, concept_proc)

    try:
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
# 程序入口
# ============================================================
if __name__ == "__main__":
    cli()
