from http import HTTPStatus
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.dependencies import get_current_user
from src.common.route import create_router
from src.config.db import get_db
from src.modules.posts.post_dto import PostCreate, PostResp
from src.modules.posts.post_service import PostService
from src.modules.users.user_model import UserDB


router = create_router(prefix = "/posts", tags = ["文章模块"])

def get_svc():
    return PostService()

@router.post("", response_model=PostResp)
async def create_post(payload: PostCreate, current_user: UserDB = Depends(get_current_user), db: AsyncSession = Depends(get_db), svc: PostService = Depends(get_svc)):
    return await svc.create(db, payload, author_id=current_user.id)

@router.get("/{post_id}", response_model=PostResp)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db), svc: PostService = Depends(get_svc)):
    post = await svc.get_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="文章不存在")
    return post