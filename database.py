"""数据库连接、建表、迁移与种子数据初始化。"""
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from models import DEFAULT_SETTINGS, SEED_CATEGORIES, Base, GoodsCategory, Setting

DB_FILENAME = "furniture.db"


def app_dir() -> Path:
    """数据文件目录：打包后为 EXE 所在目录，开发时为项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def static_dir() -> Path:
    """静态资源目录：打包后从 _MEIPASS 读取，开发时为 static 目录。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)) / "static"
    return Path(__file__).resolve().parent / "static"


def uploads_dir() -> Path:
    """上传图片目录：打包后为 EXE 同目录 uploads，开发时为项目根目录 uploads。"""
    return app_dir() / "uploads"


def db_path() -> Path:
    return app_dir() / DB_FILENAME


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dirs() -> None:
    uploads_dir().mkdir(parents=True, exist_ok=True)


# SQLAlchemy 引擎：连接 SQLite 数据库，check_same_thread=False 允许多线程复用
engine = create_engine(
    f"sqlite:///{db_path()}",
    connect_args={"check_same_thread": False},
)

# 会话工厂：每次通过 db() 上下文创建一个新的 Session
SessionLocal = sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)


@contextmanager
def db():
    """获取一个 SQLAlchemy 会话，自动提交/回滚并关闭。"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """建表、迁移（兼容旧库）、写入默认种子数据。"""
    ensure_dirs()
    Base.metadata.create_all(engine)
    with db() as session:
        migrate(session)
        seed_if_empty(session)


def migrate(session) -> None:
    """为旧版本数据库补充新增字段与缺失的默认配置键。"""
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("goods_category")}
    if "image" not in cols:
        session.execute(text("ALTER TABLE goods_category ADD COLUMN image TEXT NOT NULL DEFAULT ''"))
    existing = {row[0] for row in session.execute(text("SELECT key FROM settings"))}
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            session.add(Setting(key=key, value=value))


def seed_if_empty(session) -> None:
    count = session.query(GoodsCategory).count()
    if count == 0:
        for i, name in enumerate(SEED_CATEGORIES["recycle"], start=1):
            session.add(GoodsCategory(name=name, type=1, sort=i, status=1, image="", create_time=now()))
        for i, name in enumerate(SEED_CATEGORIES["sell"], start=1):
            session.add(GoodsCategory(name=name, type=2, sort=i, status=1, image="", create_time=now()))
    settings_count = session.query(Setting).count()
    if settings_count == 0:
        for key, value in DEFAULT_SETTINGS.items():
            session.add(Setting(key=key, value=value))