from http import HTTPStatus
from fastapi import APIRouter, Response

from src.modules.health.health_service import check_mysql, check_redis

router = APIRouter(tags = ["健康检查"])

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/ready")
async def ready(response: Response):
    checks = {
        "redis": "ok" if await check_redis() else "down",
        "mysql": "ok" if await check_mysql() else "down"
    }

    all_ok = all(v == "ok" for v in checks.values())

    if not all_ok:
        response.status_code = HTTPStatus.SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ok else "not_ready", 
        "checks": checks
    }