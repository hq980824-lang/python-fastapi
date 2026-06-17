from http import HTTPStatus
from typing import Optional, Any
from pydantic import BaseModel

class ResponseModel(BaseModel):
    code: int
    msg: str
    data: Optional[Any] = None

def success(data = None, msg = '操作成功', code = HTTPStatus.OK):
    return ResponseModel(code=code, msg=msg, data=data)

def fail(msg = '操作失败', code = HTTPStatus.BAD_REQUEST, data = None):
    return ResponseModel(code=code, msg=msg, data=data)