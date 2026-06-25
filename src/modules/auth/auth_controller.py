from fastapi import Depends
from redis.asyncio import Redis

from src.auth.dto import EmailLoginDto, SendCodeDto
from src.common.route import create_router
from src.config.db import get_db
from src.config.redis import get_redis
from src.config.settings import settings
from src.modules.auth.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

router = create_router(prefix="/auth", tags=["登录鉴权"])


def get_svc():
    return AuthService()


@router.post("/send-code")
async def send_email_code(
    dto: SendCodeDto,
    redis: Redis = Depends(get_redis),
    svc: AuthService = Depends(get_svc),
):
    code = await svc.send_code(redis, dto.email)
    return code if settings.ENV == "dev" else "验证码已发送，请查收邮箱"


@router.post("/login")
async def email_login(
    dto: EmailLoginDto,
    redis: Redis = Depends(get_redis),
    svc: AuthService = Depends(get_svc),
    db: AsyncSession = Depends(get_db),
):
    token = await svc.verify_and_login(redis, dto, db)
    return {"token": f"Bearer {token}"}
