from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from src.config.db import Base
from src.modules.friendship.friendship_dto import FriendStatus


class FriendShipDb(Base):
    __tablename__ = "friendship"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="用户ID"
    )
    friend_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="好友ID"
    )

    status: Mapped[FriendStatus] = mapped_column(
        default=FriendStatus.PENDING, comment="状态"
    )

    create_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="更新时间", onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", "friend_id"),)
