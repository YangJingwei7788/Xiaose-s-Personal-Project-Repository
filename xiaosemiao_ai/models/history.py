"""浏览历史表：用户浏览过的 AI 对话会话"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xiaosemiao_ai.models.base import Base, BigIntPK


class History(Base):
    """浏览历史表：关联用户 ID 与对话会话 ID，记录最后浏览时间"""

    __tablename__ = "history"
    __table_args__ = (UniqueConstraint("user_id", "chat_id", name="uk_history_user_chat"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="ID")
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False, comment="用户ID"
    )
    chat_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("chat.id", ondelete="CASCADE"), index=True, nullable=False, comment="对话ID"
    )
    last_viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="最后浏览时间")

    user: Mapped["User"] = relationship(back_populates="histories")
    chat: Mapped["Chat"] = relationship()