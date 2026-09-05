"""统一响应封装与分页通用工具"""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def success(data: Any = None, message: str = "success") -> dict:
    """统一成功响应"""
    return {"code": 0, "message": message, "data": data}


def error(code: int = 500, message: str = "服务器内部错误") -> dict:
    """统一错误响应"""
    return {"code": code, "message": message, "data": None}


def page_data(total: int, page: int, size: int, items: list[Any]) -> dict:
    """分页数据包装"""
    return {"total": total, "page": page, "size": size, "items": items}


async def paginate_query(db: AsyncSession, stmt, page: int, size: int) -> tuple[int, list[Any]]:
    """对查询语句执行分页，返回 (总数, 当前页数据)"""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = await db.scalar(count_stmt) or 0
    rows = (await db.scalars(stmt.offset((page - 1) * size).limit(size))).all()
    return total, list(rows)