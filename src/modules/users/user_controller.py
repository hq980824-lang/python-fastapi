from http import HTTPStatus
from fastapi import Depends, HTTPException

from src.common.dependencies import CurrentUser, DbDep, get_current_user
from src.common.pagination import PageQuery, PageResp
from src.common.route import create_router
from src.modules.users.user_dto import UserCreate, UserResp, UserUpdate
from src.modules.users.user_service import UserService

router = create_router(prefix="/users", tags=["用户模块"])

svc = UserService()


@router.post("", response_model=UserResp)
async def create_user(payload: UserCreate, db: DbDep):
    return await svc.create(db, payload)


@router.get("/profile", response_model=UserResp)
async def get_profile(current_user: CurrentUser):
    return current_user


@router.get(
    "/{user_id}", response_model=UserResp, dependencies=[Depends(get_current_user)]
)
async def get_user(user_id: int, db: DbDep):
    user = await svc.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return user


@router.get(
    "", response_model=PageResp[UserResp], dependencies=[Depends(get_current_user)]
)
async def get_all_users(db: DbDep, params: PageQuery = Depends()):
    return await svc.get_all(db, params)


@router.put("/{user_id}", response_model=UserResp)
async def update_user(
    user_id: int, payload: UserUpdate, current_user: CurrentUser, db: DbDep
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="只能修改自己的信息"
        )
    user = await svc.update_by_id(db, user_id, payload)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return user


@router.delete("/{user_id}")
async def delete_user(user_id: int, current_user: CurrentUser, db: DbDep):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="只能删除自己的账号"
        )
    success_flag = await svc.delete_by_id(db, user_id)
    if not success_flag:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在或删除失败"
        )
    return "删除用户成功"
