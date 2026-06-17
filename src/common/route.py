from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

from src.common.response import success


class ResponseRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request):
            response = await original_handler(request)

            if (isinstance(response, Response)):
                return response

            return success(data=response).model_dump()
        return custom_handler


def create_router(prefix: str = "", tags: list = None):
    return APIRouter(prefix=prefix, tags=tags, route_class=ResponseRoute)