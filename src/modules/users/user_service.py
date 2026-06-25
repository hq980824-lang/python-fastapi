from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.pagination import PageQuery
from src.modules.users.user_dto import UserCreate, UserUpdate
from src.modules.users.user_model import UserDB


class UserService:
    async def create(self, db: AsyncSession, payload: UserCreate):
        new_user = UserDB(**payload.model_dump())
        db.add(new_user)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("用户名或邮箱已存在")
        await db.refresh(new_user)
        return new_user

    async def get_by_id(self, db: AsyncSession, user_id: int):
        return await db.get(UserDB, user_id)

    async def get_by_email(self, db: AsyncSession, email: str):
        stmt = select(UserDB).where(UserDB.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()
        return user

    async def get_all(self, db: AsyncSession, params: PageQuery):
        count_stmt = select(func.count(UserDB.id))
        total = await db.scalar(count_stmt)

        offset = (params.page - 1) * params.size
        stmt = select(UserDB).offset(offset).limit(params.size)
        result = await db.execute(stmt)
        records = result.scalars().all()

        return {
            "records": records,
            "total": total,
            "page": params.page,
            "size": params.size,
        }

    async def update_by_id(self, db: AsyncSession, user_id: int, payload: UserUpdate):
        db_user = await self.get_by_id(db, user_id)
        if not db_user:
            return None

        update_dict = payload.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            setattr(db_user, key, value)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("用户名或邮箱已存在")
        await db.refresh(db_user)
        return db_user

    async def delete_by_id(self, db: AsyncSession, user_id: int):
        db_user = await self.get_by_id(db, user_id)
        if not db_user:
            return False
        await db.delete(db_user)
        await db.commit()
        return True
