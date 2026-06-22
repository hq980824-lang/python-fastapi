from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class PostStatus(str, Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'

class AuthorBrief(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class PostResp(BaseModel):
    id: int
    title: str
    content: str | None = None
    status: PostStatus
    author_id: int
    author: AuthorBrief | None = None
    create_time: datetime | None = None
    update_time: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str | None = None
    status: PostStatus = PostStatus.DRAFT

class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: PostStatus | None = None