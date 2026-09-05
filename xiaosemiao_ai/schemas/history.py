"""浏览历史操作参数校验模型"""
from pydantic import BaseModel, Field


class HistoryAddRequest(BaseModel):
    chat_id: int = Field(description="要记录的对话ID")