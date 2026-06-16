from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.db import get_db
from src.modules.users.user_dto import UserCreate, UserUpdate
from src.modules.users.user_service import UserService

router = APIRouter(prefix = '/users')

def get_svc():
    return UserService()

@router.post("")
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    return await svc.create(db, payload)

@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    user = await svc.get_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")
    return user

@router.get("")
async def get_all_users(db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    users = await svc.get_all(db)
    return users

@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, svc: UserService = Depends(get_svc)):
    user = svc.update_by_id(user_id, payload)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, svc: UserService = Depends(get_svc)):
    success = svc.delete_by_id(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="用户不存在或删除失败")
    return {"message": "用户删除成功"}

