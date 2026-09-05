"""用户表与用户令牌表"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xiaosemiao_ai.models.base import Base, BigIntPK


class User(Base):
    """用户表：存储账号基础信息"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="bcrypt 加密后的密码")
    nickname: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="昵称")
    avatar: Mapped[str] = mapped_column(String(500), default="", nullable=False, comment="头像地址")
    llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None, comment="大模型来源: public/local/deepseek")
    llm_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="本地大模型地址")
    llm_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, comment="DeepSeek API Key（已保存）")
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None, comment="大模型名称")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    chats: Mapped[list["Chat"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    histories: Mapped[list["History"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserToken(Base):
    """用户令牌表：记录登录发放的 JWT 令牌，支持过期失效"""

    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="ID")
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False, comment="关联用户ID"
    )
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False, comment="JWT 令牌")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")