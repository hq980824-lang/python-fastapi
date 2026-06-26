from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.likes.like_model import LikeDB
from src.modules.posts.post_model import PostDB

class LikeService:
    async def post_like(self, db: AsyncSession, post_id: int, user_id: int):
        post = await db.get(PostDB, post_id)

        if post is None:
            raise ValueError("点赞失败：文章不存在")

        stmt = select(LikeDB).where(
            and_(LikeDB.user_id == user_id, LikeDB.post_id == post_id)
        )
        result = await db.execute(stmt)
        exists = result.scalars().first()

        if exists:
            return "已经点赞过了"

        new_like = LikeDB(user_id=user_id, post_id=post_id)

        try:
            db.add(new_like)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("点赞失败：请勿重复点赞")

        return "点赞成功"
