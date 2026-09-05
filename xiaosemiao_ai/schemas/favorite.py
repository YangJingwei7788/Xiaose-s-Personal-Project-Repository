"""收藏操作参数校验模型"""
from pydantic import BaseModel, Field


class FavoriteAddRequest(BaseModel):
    chat_id: int = Field(description="要收藏的对话ID")