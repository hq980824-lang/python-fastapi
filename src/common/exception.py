from http import HTTPStatus
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from src.common.response import fail

async def http_err_handler(req: Request, exc: HTTPException):
    return JSONResponse(content=fail(msg=exc.detail, code=exc.status_code).model_dump())

async def global_err_handler(req: Request, exc: Exception):
    return JSONResponse(content=fail(msg="服务器异常", code=HTTPStatus.INTERNAL_SERVER_ERROR).model_dump())