"""萧瑟喵AI工作台 V1.0 应用入口"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from xiaosemiao_ai.config.cache_conf import close_redis
from xiaosemiao_ai.config.db_conf import init_db
from xiaosemiao_ai.config.settings import settings
from xiaosemiao_ai.routers import chat, favorite, history, user
from xiaosemiao_ai.utils.common import error

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("xiaosemiao_ai")

BASE_DIR = Path(__file__).resolve().parent
HTML_DIR = BASE_DIR / "html"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（数据库需提前创建，见 scripts/init_db.sql）
    try:
        await init_db()
    except Exception:
        logger.warning("数据库初始化失败，请确认 MySQL 已启动且数据库已创建", exc_info=True)
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="萧瑟喵AI工作台 V1.0 接口文档",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=error(exc.status_code, str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=error(422, "参数校验失败"))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(status_code=500, content=error(500, "服务器内部错误"))


app.include_router(user.router, prefix="/api/user", tags=["用户管理"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI对话"])
app.include_router(favorite.router, prefix="/api/favorite", tags=["素材收藏"])
app.include_router(history.router, prefix="/api/history", tags=["浏览历史"])

# 静态资源（上传的头像等）
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/user", include_in_schema=False)
async def user_page():
    # ?????????no-store ??????????????
    return FileResponse(HTML_DIR / "user.html", headers={"Cache-Control": "no-store"})


@app.get("/settings", include_in_schema=False)
async def settings_page():
    # ???????no-store ?????
    return FileResponse(HTML_DIR / "settings.html", headers={"Cache-Control": "no-store"})


@app.get("/", include_in_schema=False)
async def index():
    # no-store：禁止浏览器缓存首页，确保每次加载最新页面，无需手动刷新
    return FileResponse(HTML_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/health", tags=["系统"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}