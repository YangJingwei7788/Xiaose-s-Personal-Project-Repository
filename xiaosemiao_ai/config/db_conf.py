"""MySQL 异步数据库配置：SQLAlchemy 异步引擎与会话工厂"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from xiaosemiao_ai.config.settings import settings

engine_kwargs: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # 本地测试环境使用 SQLite 内存库（单连接共享）
    engine_kwargs.update(connect_args={"check_same_thread": False}, poolclass=StaticPool)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=not settings.DATABASE_URL.startswith("sqlite"),
    **engine_kwargs,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_session():
    """FastAPI 依赖：请求级数据库会话"""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """启动时自动建表（数据库需先创建，见 scripts/init_db.sql）"""
    from xiaosemiao_ai.models import Base  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 兼容旧库：补充新增字段（幂等，仅 MySQL）
    if engine.dialect.name == "mysql":
        from sqlalchemy import text

        async with engine.begin() as conn:
            rows = await conn.execute(text("SHOW COLUMNS FROM chat"))
            chat_columns = [row[0] for row in rows]
            if "system_prompt" not in chat_columns:
                await conn.execute(text("ALTER TABLE chat ADD COLUMN system_prompt TEXT NULL"))
        async with engine.begin() as conn:
            rows = await conn.execute(text("SHOW COLUMNS FROM user"))
            user_columns = [row[0] for row in rows]
            user_additions = [
                ("llm_provider", "VARCHAR(20) NULL"),
                ("llm_base_url", "VARCHAR(500) NULL"),
                ("llm_api_key", "VARCHAR(500) NULL"),
                ("llm_model", "VARCHAR(100) NULL"),
            ]
            for col_name, col_ddl in user_additions:
                if col_name not in user_columns:
                    await conn.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_ddl}"))