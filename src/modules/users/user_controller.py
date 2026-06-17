from fastapi import APIRouter, Depends, HTTPException
import pydantic
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.response import success
from src.config.db import get_db
from src.modules.users.user_dto import UserCreate, UserResp, UserUpdate
from src.modules.users.user_service import UserService

router = APIRouter(prefix = '/users')

def get_svc():
    return UserService()

@router.post("")
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    new_user = await svc.create(db, payload)
    new_pydantic_user = UserResp.model_validate(new_user)
    return success(data=new_pydantic_user.model_dump()) 

@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    user = await svc.get_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")
    pydantic_user = UserResp.model_validate(user)
    return success(data=pydantic_user.model_dump())

@router.get("")
async def get_all_users(db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    users = await svc.get_all(db)
    # UserResp.model_validate(user).model_dump() for user in users
    data = []
    for user in users:
        pydantic_user = UserResp.model_validate(user)
        data.append(pydantic_user.model_dump())
        
    return success(data=data)

@router.put("/{user_id}")
async def update_user(user_id: int, payload: UserUpdate, svc: UserService = Depends(get_svc), db: AsyncSession = Depends(get_db)):
    user = await svc.update_by_id(user_id, payload, db)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")
    pydantic_user = UserResp.model_validate(user)
    return success(data=pydantic_user.model_dump())

@router.delete("/{user_id}")
def delete_user(user_id: int, svc: UserService = Depends(get_svc), db: AsyncSession = Depends(get_db)):
    success = svc.delete_by_id(user_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="用户不存在或删除失败")
    return success(msg="删除用户成功")

