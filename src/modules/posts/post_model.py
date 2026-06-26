from datetime import datetime
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.config.db import Base
from src.modules.posts.post_dto import PostStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.users.user_model import UserDB

class PostDB(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键ID")
    title: Mapped[str] = mapped_column(String(200), comment="标题")
    content: Mapped[str | None] = mapped_column(Text, comment="正文")

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="作者ID"
    )

    create_time: Mapped[datetime] = mapped_column(server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), comment="更新时间")
    status: Mapped[PostStatus] = mapped_column(default=PostStatus.DRAFT, comment="状态")

    author: Mapped["UserDB"] = relationship(back_populates="posts")
