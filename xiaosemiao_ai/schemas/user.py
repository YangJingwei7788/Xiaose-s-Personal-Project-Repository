"""用户相关请求 / 返回校验模型"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=32, description="用户名")
    password: str = Field(min_length=6, max_length=64, description="密码")


class UserLogin(BaseModel):
    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    avatar: str
    created_at: datetime


class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=64, description="新昵称")
    avatar: str | None = Field(default=None, max_length=500, description="新头像地址")


class PasswordUpdate(BaseModel):
    old_password: str = Field(description="原密码")
    new_password: str = Field(min_length=6, max_length=64, description="新密码")


class LoginResult(BaseModel):
    token: str
    user: UserInfo


class LLMSettingsOut(BaseModel):
    """大模型设置（不返回明文 API Key）"""
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_has_api_key: bool = False
    llm_model: str | None = None
    server_default_model: str | None = None


class LLMSettingsUpdate(BaseModel):
    llm_provider: str = Field(default="public", description="public/local/deepseek")
    llm_base_url: str | None = Field(default=None, max_length=500, description="本地大模型地址")
    llm_api_key: str | None = Field(default=None, max_length=500, description="DeepSeek API Key，传空表示保留原值")
    llm_model: str | None = Field(default=None, max_length=100, description="大模型名称")