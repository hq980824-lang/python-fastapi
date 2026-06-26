from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.config.db import Base

if TYPE_CHECKING:
    from src.modules.posts.post_model import PostDB


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="邮箱"
    )
    create_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    posts: Mapped[list["PostDB"]] = relationship(back_populates="author")
