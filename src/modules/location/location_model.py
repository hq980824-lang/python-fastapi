from enum import IntEnum
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.config.db import Base


class LocationLevel(IntEnum):
    PROVINCE = 1  # 省
    CITY = 2  # 市
    DISTRICT = 3  # 区/县


class LocationDb(Base):
    __tablename__ = "location"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, comment="地区编码")
    name: Mapped[str] = mapped_column(String(50), comment="地区名称")

    level: Mapped[LocationLevel] = mapped_column(
        comment="层级：1省 2市 3区/县"
    )
    parent_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("location.code"),
        index=True,
        default=None,
        comment="上级地区编码，顶级为空",
    )

    parent: Mapped[Optional["LocationDb"]] = relationship(
        remote_side=[code], back_populates="children"
    )
    children: Mapped[list["LocationDb"]] = relationship(
        back_populates="parent"
    )
