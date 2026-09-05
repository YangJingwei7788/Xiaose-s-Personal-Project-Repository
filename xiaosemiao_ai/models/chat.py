"""AI 对话表与对话消息表"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xiaosemiao_ai.models.base import Base, BigIntPK


class Chat(Base):
    """AI 对话会话表"""

    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="对话ID")
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False, comment="所属用户ID"
    )
    title: Mapped[str] = mapped_column(String(200), default="新对话", nullable=False, comment="会话标题")
    system_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None, comment="角色设定（作为 system 指令随每次提问发送给 AI）"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    user: Mapped["User"] = relationship(back_populates="chats")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """对话消息表：存储单轮问答消息，区分用户提问与 AI 回复"""

    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="消息ID")
    chat_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("chat.id", ondelete="CASCADE"), index=True, nullable=False, comment="所属对话ID"
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="角色: user / assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    chat: Mapped["Chat"] = relationship(back_populates="messages")