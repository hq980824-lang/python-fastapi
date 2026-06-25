from datetime import datetime, timedelta, timezone
import jwt
from src.config.settings import settings


class JwtUtil:
    @staticmethod
    def create_access_token(
        subject: int | str, expires_delta: timedelta | None = None
    ) -> str:
        # 1. payload：载荷，存在token里的业务数据，sub约定用来存用户唯一ID
        payload = {"sub": str(subject)}

        # 2. 获取当前UTC标准时间，设置令牌过期时间
        now = datetime.now(timezone.utc)
        expire = now + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        payload["exp"] = expire

        # 3. 使用密钥+加密算法，把载荷加密成一段字符串token返回给前端
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token

    @staticmethod
    def decode_access_token(token: str) -> int | None:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            return int(user_id) if user_id else None
        except (jwt.InvalidTokenError, Exception):
            return None
