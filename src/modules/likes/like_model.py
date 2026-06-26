from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from src.config.db import Base


class LikeDB(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="用户ID"
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"), index=True, comment="文章ID"
    )

    create_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uniq_userid_postid"),
    )
