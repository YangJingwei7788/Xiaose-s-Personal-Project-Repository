"""品类展示与管理接口。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from database import db, now
from models import GoodsCategory
from routers.admin import require_admin
from schemas import CategoryCreate, CategoryUpdate

router = APIRouter()


@router.get("/api/categories")
def list_public_categories(type: int = Query(1, ge=1, le=2)):
    """前台公开：按业务类型返回显示中的品类（按 sort 排序）。"""
    with db() as session:
        rows = session.execute(
            select(GoodsCategory)
            .where(GoodsCategory.type == type, GoodsCategory.status == 1)
            .order_by(GoodsCategory.sort.asc(), GoodsCategory.id.asc())
        ).scalars().all()
    return {"code": 0, "data": [r.to_dict() for r in rows]}


@router.get("/api/admin/categories")
def list_admin_categories(_=Depends(require_admin)):
    """后台：返回全部品类（含隐藏）。"""
    with db() as session:
        rows = session.execute(
            select(GoodsCategory).order_by(
                GoodsCategory.type.asc(), GoodsCategory.sort.asc(), GoodsCategory.id.asc()
            )
        ).scalars().all()
    return {"code": 0, "data": [r.to_dict() for r in rows]}


@router.post("/api/admin/categories")
def create_category(payload: CategoryCreate, _=Depends(require_admin)):
    with db() as session:
        cat = GoodsCategory(
            name=payload.name, type=payload.type, sort=payload.sort,
            status=payload.status, image=payload.image, create_time=now(),
        )
        session.add(cat)
        session.flush()
        cat_id = cat.id
    return {"code": 0, "message": "新增成功", "data": {"id": cat_id}}


@router.put("/api/admin/categories/{cat_id}")
def update_category(cat_id: int, payload: CategoryUpdate, _=Depends(require_admin)):
    with db() as session:
        cat = session.get(GoodsCategory, cat_id)
        if cat is None:
            raise HTTPException(status_code=404, detail="品类不存在")
        cat.name = payload.name
        cat.type = payload.type
        cat.sort = payload.sort
        cat.status = payload.status
        cat.image = payload.image
    return {"code": 0, "message": "修改成功"}


@router.delete("/api/admin/categories/{cat_id}")
def delete_category(cat_id: int, _=Depends(require_admin)):
    with db() as session:
        cat = session.get(GoodsCategory, cat_id)
        if cat is None:
            raise HTTPException(status_code=404, detail="品类不存在")
        session.delete(cat)
    return {"code": 0, "message": "删除成功"}