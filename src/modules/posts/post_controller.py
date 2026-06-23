from http import HTTPStatus
from fastapi import HTTPException

from src.common.dependencies import CurrentUser, DbDep
from src.common.route import create_router
from src.modules.posts.post_dto import PostCreate, PostResp
from src.modules.posts.post_service import PostService


router = create_router(prefix="/posts", tags=["文章模块"])

svc = PostService()


@router.post("", response_model=PostResp)
async def create_post(payload: PostCreate, current_user: CurrentUser, db: DbDep):
    return await svc.create(db, payload, author_id=current_user.id)


@router.get("/{post_id}", response_model=PostResp)
async def get_post(post_id: int, db: DbDep):
    post = await svc.get_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="文章不存在")
    return post
