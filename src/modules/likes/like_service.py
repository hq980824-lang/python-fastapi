from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.likes.like_model import LikeDB
from src.modules.posts.post_model import PostDB


class LikeService:
    async def _get_like(self, db, user_id, post_id):
        stmt = select(LikeDB).where(
            and_(LikeDB.user_id == user_id, LikeDB.post_id == post_id)
        )
        result = await db.execute(stmt)
        exists = result.scalars().first()
        return exists

    async def like(self, db: AsyncSession, post_id: int, user_id: int):
        post = await db.get(PostDB, post_id)

        if post is None:
            raise ValueError("点赞失败：文章不存在")

        exists = await self._get_like(db, user_id, post_id)

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

    async def unlike(self, db: AsyncSession, post_id: int, user_id: int):
        exists = await self._get_like(db, user_id, post_id)

        if exists:
            await db.delete(exists)
            await db.commit()
            return "取消点赞成功"

        return "未点赞过"

    async def count(self, db: AsyncSession, post_id: int):
        count_stmt = select(func.count(LikeDB.id)).where(LikeDB.post_id == post_id)
        total = await db.scalar(count_stmt)

        return total
