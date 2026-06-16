from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str

class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None

class UserResp(UserCreate):
    id: int
    create_time: str | None = None
    update_time: str | None = None

