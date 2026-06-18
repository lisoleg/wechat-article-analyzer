"""分步测试：先列表采集，再正文采集，输出到 utf-8 文件。"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from loguru import logger
from src.database import Database, ArticleRepository
from src.crawler.browser import BrowserManager
from src.crawler.article_list import ArticleListCrawler
from src.crawler.article_content import ArticleContentCrawler

# 配置 loguru 输出到 utf-8 文件
logger.remove()
logger.add(
    "data/test_crawl.log",
    level="DEBUG",
    encoding="utf-8",
    rotation="10 MB",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
)

DB_PATH = "./data/articles_test.db"
LIMIT = 5

# 1. 初始化 DB
db = Database(DB_PATH)
db.init()
repo = ArticleRepository(db)
logger.info(f"数据库初始化完成: {DB_PATH}")

# 2. 启动浏览器 + 登录
browser_mgr = BrowserManager()
browser_mgr.launch(headless=False)
logger.info("浏览器已启动，请扫码登录（如需要）...")

# 3. 列表采集
list_crawler = ArticleListCrawler(browser_mgr, repo)
articles = list_crawler.fetch_article_list(resume=False, limit=LIMIT)
logger.info(f"列表采集完成: {len(articles)} 篇")

# 验证 ID 是否都非 None
ok_count = sum(1 for a in articles if a.id is not None)
logger.info(f"有 ID 的文章数: {ok_count}/{len(articles)}")
for a in articles:
    logger.debug(f"  id={a.id}, title={a.title[:30]}, url={a.url[:50]}")

# 强制刷新 DB 连接
db.get_connection().commit()
logger.info("DB 已 commit")

# 4. 查 DB 确认
all_articles = repo.get_all_articles()
logger.info(f"DB 中共有 {len(all_articles)} 篇文章")
pending = repo.get_articles_by_crawl_status("pending")
logger.info(f"DB 中 pending 状态: {len(pending)} 篇")
for a in pending:
    logger.debug(f"  id={a.id}, title={a.title[:30]}")

# 5. 正文采集
content_crawler = ArticleContentCrawler(browser_mgr, repo)
content_crawler.fetch_all_content(resume=False, limit=LIMIT)

# 6. 结果统计
stats = repo.get_stats()
logger.info(f"最终结果: total={stats['total']}, crawled={stats['crawled']}, pending={stats['crawl_pending']}, failed={stats['crawl_failed']}")

# 7. 关闭
browser_mgr.close()
logger.info("测试完成")
