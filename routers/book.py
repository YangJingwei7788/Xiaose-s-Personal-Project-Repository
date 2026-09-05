"""客户预约与预约管理接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from database import db, now
from models import CustomerBook
from routers.admin import require_admin
from schemas import BookCreate, BookStatusUpdate

router = APIRouter()


@router.post("/api/book")
def create_book(payload: BookCreate):
    with db() as session:
        book = CustomerBook(
            name=payload.name, phone=payload.phone, book_type=payload.book_type,
            need_content=payload.need_content, create_time=now(), status=0,
        )
        session.add(book)
        session.flush()
        book_id = book.id
    return {"code": 0, "message": "预约提交成功，我们会尽快与您联系", "data": {"id": book_id}}


@router.get("/api/admin/books")
def list_books(_=Depends(require_admin)):
    """后台：查看全部预约（未处理在前，新提交在前）。"""
    with db() as session:
        rows = session.execute(
            select(CustomerBook).order_by(CustomerBook.status.asc(), CustomerBook.id.desc())
        ).scalars().all()
    return {"code": 0, "data": [r.to_dict() for r in rows]}


@router.patch("/api/admin/books/{book_id}/status")
def update_book_status(book_id: int, payload: BookStatusUpdate, _=Depends(require_admin)):
    with db() as session:
        book = session.get(CustomerBook, book_id)
        if book is None:
            raise HTTPException(status_code=404, detail="预约记录不存在")
        book.status = payload.status
    return {"code": 0, "message": "状态已更新"}


@router.delete("/api/admin/books/{book_id}")
def delete_book(book_id: int, _=Depends(require_admin)):
    with db() as session:
        book = session.get(CustomerBook, book_id)
        if book is None:
            raise HTTPException(status_code=404, detail="预约记录不存在")
        session.delete(book)
    return {"code": 0, "message": "删除成功"}