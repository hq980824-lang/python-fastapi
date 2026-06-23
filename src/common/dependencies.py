from http import HTTPStatus
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.db import get_db
from src.modules.users.user_model import UserDB
from src.modules.users.user_service import UserService
from src.utils.jwt_util import JwtUtil

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    user_id = JwtUtil.decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="登录已失效，请重新登录")

    user = await UserService().get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="用户不存在")

    return user

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[UserDB, Depends(get_current_user)]