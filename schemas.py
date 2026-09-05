"""请求数据校验模型。"""
import re

from pydantic import BaseModel, Field, field_validator

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="品类名称")
    type: int = Field(ge=1, le=2, description="1=回收 2=售卖")
    sort: int = Field(default=0, description="排序权重")
    status: int = Field(default=1, ge=0, le=1, description="1=显示 0=隐藏")
    image: str = Field(default="", max_length=300, description="品类背景图地址")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("品类名称不能为空")
        return v


class CategoryUpdate(CategoryCreate):
    pass


class BookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="客户姓名")
    phone: str = Field(min_length=1, max_length=20, description="联系电话")
    book_type: int = Field(ge=1, le=2, description="1=回收预约 2=购买咨询")
    need_content: str = Field(default="", max_length=500, description="需求描述")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("手机号格式不正确")
        return v

    @field_validator("need_content")
    @classmethod
    def strip_need(cls, v: str) -> str:
        return v.strip()


class BookStatusUpdate(BaseModel):
    status: int = Field(ge=0, le=1, description="0=未处理 1=已处理")


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=50)


class PasswordUpdate(BaseModel):
    old_password: str = Field(min_length=1, max_length=50)
    new_password: str = Field(min_length=4, max_length=50)


class SettingsUpdate(BaseModel):
    settings: dict[str, str]