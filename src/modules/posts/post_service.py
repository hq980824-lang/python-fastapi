from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.modules.posts.post_dto import PostCreate
from src.modules.posts.post_model import PostDB


class PostService:
    async def create(self, db: AsyncSession, payload: PostCreate, author_id: int):
        new_post = PostDB(**payload.model_dump(), author_id=author_id)
        db.add(new_post)
        await db.commit()
        await db.refresh(new_post)
        return new_post

    async def get_by_id(self, db: AsyncSession, post_id: int):
        stmt = (
            select(PostDB)
            .where(PostDB.id == post_id)
            .options(selectinload(PostDB.author))
        )
        result = await db.execute(stmt)
        return result.scalars().first()