import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from src.common.response import success


class ResponseRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request):
            response = await original_handler(request)

            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return response

            # 二进制 JSON 字节 → 转换成可操作的 Python dict
            data = json.loads(response.body)
            content = success(data=data).model_dump(mode="json")
            return JSONResponse(content=content, status_code=response.status_code)

        return custom_handler


def create_router(prefix: str = "", tags: list = None):
    return APIRouter(prefix=prefix, tags=tags, route_class=ResponseRoute)
