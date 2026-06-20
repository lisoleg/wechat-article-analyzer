"""FastAPI 应用主入口。

创建 FastAPI 实例，注册路由，配置 CORS。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routes import router


def create_app(db_path: str = "data/articles.db") -> FastAPI:
    """创建并配置 FastAPI 应用。

    Args:
        db_path: SQLite 数据库文件路径。

    Returns:
        配置好的 FastAPI 应用实例。
    """
    app = FastAPI(
        title="WeChat Article Analyzer API",
        description="微信公众号文章理论收敛分析 REST API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS — 允许前端开发服务器访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 保存 db_path 到 app.state
    app.state.db_path = db_path

    # 注册路由
    app.include_router(router, prefix="/api")

    @app.on_event("startup")
    async def startup_event() -> None:
        """应用启动时初始化数据库。"""
        from src.api.dependencies import init_db

        init_db(db_path)
        logger.info(f"[API] 数据库已初始化: {db_path}")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """应用关闭时清理资源。"""
        from src.api.dependencies import _db

        if _db is not None:
            _db.close()
            logger.info("[API] 数据库连接已关闭")

    @app.get("/health", tags=["状态"], summary="健康检查")
    def health_check() -> dict:
        """返回服务健康状态。"""
        return {"status": "ok", "version": "2.0.0"}

    return app


# 模块级 app 实例，供 uvicorn 加载
app = create_app()
