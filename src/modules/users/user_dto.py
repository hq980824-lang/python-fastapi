from datetime import datetime

from pydantic import BaseModel, ConfigDict

class UserCreate(BaseModel):
    name: str
    email: str

class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None

class UserResp(UserCreate):
    id: int
    create_time: datetime | None = None
    update_time: datetime | None = None
    # 支持直接用 ORM 实例解析成 Pydantic 对象。
    # ORM 实例：从数据库查出来的db_user，是 SQLAlchemy 封装的数据库对象，不能直接返回给前端。
    # Pydantic 对象：用来规范返回给前端的数据结构。
    # from_attributes=True：让UserResp能直接读取db_user里的字段，不用手动逐个赋值
    model_config = ConfigDict(from_attributes=True)
