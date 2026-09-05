"""AI 对话相关请求 / 返回校验模型"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200, description="可选，创建时指定标题")


class ChatTitleUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200, description="新标题")


class ChatSendRequest(BaseModel):
    chat_id: int | None = Field(default=None, description="为空则自动新建对话")
    message: str = Field(min_length=1, max_length=8000, description="用户提问内容")
    model: str | None = Field(default=None, description="可选，指定模型名")
    provider: str | None = Field(default=None, description="可选，模型来源：public/local/deepseek，缺省用用户保存的配置")
    base_url: str | None = Field(default=None, description="可选，本地大模型地址")
    api_key: str | None = Field(default=None, description="可选，DeepSeek API Key（未保存到账号时临时传入）")


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ChatListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ChatDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    system_prompt: str | None = None
    created_at: datetime
    messages: list[ChatMessageOut]


class ChatRoleUpdate(BaseModel):
    system_prompt: str = Field(default="", max_length=4000, description="角色设定内容，传空字符串表示清除")