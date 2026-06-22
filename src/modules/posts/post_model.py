from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from src.config.db import Base


class PostDB(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    title = Column(String(200), nullable=False, comment="标题")
    content = Column(Text, comment="正文")

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="作者ID")

    create_time = Column(DateTime, server_default= func.now(), comment="创建时间")
    update_time = Column(DateTime, server_default = func.now(), onupdate = func.now(), comment="更新时间")

    author = relationship("UserDB", back_populates="posts")