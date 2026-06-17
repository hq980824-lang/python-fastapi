from http import HTTPStatus
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import PageQuery, PageResp
from src.common.route import create_router
from src.config.db import get_db
from src.modules.users.user_dto import UserCreate, UserResp, UserUpdate
from src.modules.users.user_service import UserService

router = create_router(prefix = '/users', tags = ['用户模块'])

def get_svc():
    return UserService()

@router.post("", response_model=UserResp)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    return await svc.create(db, payload)

@router.get("/{user_id}", response_model=UserResp)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    user = await svc.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return user

@router.get("", response_model=PageResp[UserResp])
async def get_all_users(params: PageQuery = Depends(), db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    return await svc.get_all(db, params)

@router.put("/{user_id}", response_model=UserResp)
async def update_user(user_id: int, payload: UserUpdate, svc: UserService = Depends(get_svc), db: AsyncSession = Depends(get_db)):
    user = await svc.update_by_id(db, user_id, payload)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return user

@router.delete("/{user_id}")
async def delete_user(user_id: int, svc: UserService = Depends(get_svc), db: AsyncSession = Depends(get_db)):
    success_flag = await svc.delete_by_id(db, user_id)
    if not success_flag:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在或删除失败")
    return "删除用户成功"

