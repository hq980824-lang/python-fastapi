from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.users.user_dto import UserCreate, UserUpdate
from src.modules.users.user_model import UserDB

users = []
next_id = 1

class UserService:
    async def create(self, db: AsyncSession, payload: UserCreate):
        new_user = UserDB(**payload.model_dump())
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    async def get_by_id(self, user_id: int, db: AsyncSession):
        result = await db.get(UserDB, user_id)
        return result

    async def get_all(self, db: AsyncSession):
        stmt = select(UserDB)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_by_id(self, user_id: int, payload: UserUpdate, db: AsyncSession):
        db_user = await self.get_by_id(user_id, db)
        if not db_user:
            return None
        
        update_dict = payload.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            setattr(db_user, key, value)

        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def delete_by_id(self, user_id: int, db: AsyncSession):
        db_user = await self.get_by_id(user_id, db)
        if not db_user:
            return False
        await db.delete(db_user)
        await db.commit()
        return True