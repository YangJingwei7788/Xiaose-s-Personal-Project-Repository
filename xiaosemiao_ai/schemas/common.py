"""统一响应与通用模型"""
from typing import Any

from pydantic import BaseModel


class ResponseModel(BaseModel):
    """统一响应格式：{ code, message, data }"""

    code: int = 0
    message: str = "success"
    data: Any = None