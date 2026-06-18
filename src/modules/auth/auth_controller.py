import asyncio
from http import HTTPStatus
from fastapi import Depends, HTTPException
from redis.asyncio import Redis
from src.auth.dto import EmailLoginDto, SendCodeDto
from src.common.route import create_router
from src.config.settings import settings
from src.config.redis import get_redis
from src.utils.email_util import EmailUtil
from src.utils.jwt_util import JwtUtil
from src.utils.redis_util import RedisUtil

router = create_router(prefix="/auth", tags=["登录鉴权"])

@router.post("/send-code")
async def send_email_code(dto: SendCodeDto, redis: Redis = Depends(get_redis)):
    code = EmailUtil.generate_code()

    if settings.ENV != 'dev':
        try:
            await asyncio.to_thread(EmailUtil.send_verify_code, dto.email, code)
        except Exception:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail='发送失败')

    await RedisUtil.set_value(redis, f"verify_code:{dto.email}", code, expire=5 * 60)

    return code if settings.ENV == 'dev' else "验证码已发送，请查收邮箱"

@router.post("/login")
async def email_login(dto: EmailLoginDto, redis: Redis = Depends(get_redis)):
    code = await RedisUtil.get_value(redis, f"verify_code:{dto.email}")

    if code is None:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="清先获取邮箱验证码")
    if code != dto.code:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="验证码错误")

    token = JwtUtil.create_access_token(subject=dto.email)
    await RedisUtil.delete_value(redis, f"verify_code:{dto.email}")

    return {
        "token": f"Bearer {token}"
    }