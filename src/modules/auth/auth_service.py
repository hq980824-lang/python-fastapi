import asyncio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dto import EmailLoginDto
from src.config.settings import settings
from src.modules.users.user_service import UserService
from src.utils.email_util import EmailUtil
from src.utils.jwt_util import JwtUtil
from src.utils.redis_util import RedisUtil


class AuthService:
    @staticmethod
    def _code_key(email: str) -> str:
        return f"verify_code:{email}"

    async def send_code(self, redis: Redis, email: str) -> str:
        code = EmailUtil.generate_code()

        if settings.ENV != "dev":
            try:
                await asyncio.to_thread(EmailUtil.send_verify_code, email, code)
            except Exception:
                raise ValueError("验证码发送失败，请稍后重试")

        await RedisUtil.set_value(redis, self._code_key(email), code, expire=5 * 60)
        return code

    async def verify_and_login(
        self, redis: Redis, dto: EmailLoginDto, db: AsyncSession
    ) -> str:
        code = await RedisUtil.get_value(redis, self._code_key(dto.email))
        if code is None:
            raise ValueError("请先获取邮箱验证码")
        if code != dto.code:
            raise ValueError("验证码错误")

        user = await UserService().get_by_email(db, email=dto.email)

        if user is None:
            raise ValueError("用户不存在")

        token = JwtUtil.create_access_token(subject=user.id)
        await RedisUtil.delete_value(redis, self._code_key(dto.email))
        return token
