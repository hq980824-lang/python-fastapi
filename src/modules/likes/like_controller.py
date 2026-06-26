from src.common.dependencies import CurrentUser, DbDep
from src.common.route import create_router
from src.modules.likes.like_service import LikeService

router = create_router(prefix="/likes", tags=["点赞模块"])

svc = LikeService()


@router.post("/like")
async def post_like(db: DbDep, current_user: CurrentUser, post_id: int):
    return await svc.like(db=db, post_id=post_id, user_id=current_user.id)


@router.delete("/unlike")
async def post_unlike(db: DbDep, current_user: CurrentUser, post_id: int):
    return await svc.unlike(db=db, post_id=post_id, user_id=current_user.id)


@router.get("/count")
async def post_count(db: DbDep, post_id: int):
    return await svc.count(db=db, post_id=post_id)
