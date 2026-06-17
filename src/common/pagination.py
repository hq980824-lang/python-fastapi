from typing import List, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')

class PageResp(BaseModel, Generic[T]):
    records: List[T]
    total: int
    page: int
    size: int

class PageQuery(BaseModel):
    page: int = 1
    size: int = 10