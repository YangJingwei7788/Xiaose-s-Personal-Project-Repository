"""二手家具回收售卖展示系统 - 程序入口。

开发运行：python main.py [--port 8000]
打包命令：pyinstaller -F -n 二手家具业务展示系统 --add-data "static;static" main.py
"""
import argparse
import socket
import sys
import threading
import webbrowser
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from database import ensure_dirs, init_db, static_dir, uploads_dir
from routers import admin, book, category

ensure_dirs()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """服务生命周期：启动时初始化数据库"""
    init_db()
    yield


app = FastAPI(title="二手家具回收售卖展示系统", lifespan=lifespan)

app.include_router(category.router)
app.include_router(book.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
def index():
    """根路径重定向至后台管理页，不暴露在接口文档"""
    return RedirectResponse(url="/admin.html")


app.mount("/uploads", StaticFiles(directory=str(uploads_dir())), name="uploads")
app.mount("/", StaticFiles(directory=str(static_dir()), html=True), name="static")


def get_lan_ip() -> str:
    """获取本机局域网IP，获取失败返回127.0.0.1
    利用UDP套接字获取出网网卡IP，无需真正建立连接
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    """程序入口：解析命令行参数、打印访问地址、启动uvicorn服务"""
    parser = argparse.ArgumentParser(description="二手家具回收售卖展示系统")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0，允许局域网访问）")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    args = parser.parse_args()

    # 额外初始化数据库，规避生命周期钩子未触发的边界情况
    init_db()
    lan_ip = get_lan_ip()

    print("=" * 56)
    print("  二手家具回收售卖展示系统 已启动")
    print(f"  商家后台:    http://127.0.0.1:{args.port}/admin.html")
    print(f"  客户前台:    http://127.0.0.1:{args.port}/index.html")
    if args.host in ("0.0.0.0", "::"):
        print(f"  局域网(后台): http://{lan_ip}:{args.port}/admin.html")
        print(f"  局域网(前台): http://{lan_ip}:{args.port}/index.html")
    print("  按 Ctrl+C 停止服务")
    print("=" * 56)

    # 延迟打开浏览器，等待服务完成启动
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}/admin.html")).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()