from src.common.dependencies import CurrentUser, DbDep, get_current_user
from src.common.route import create_router
from src.modules.likes.like_service import LikeService

router = create_router(prefix="/likes", tags=["点赞模块"])

svc = LikeService()


@router.post("/like")
async def post_like(db: DbDep, current_user: CurrentUser, post_id: int):
    return await svc.post_like(db=db, post_id=post_id, user_id=current_user.id)
