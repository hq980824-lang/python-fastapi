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
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession):
        stmt = select(UserDB)
        result = await db.execute(stmt)
        user_list = result.scalars().all()
        return user_list

    def update_by_id(self, user_id: int, payload: UserUpdate):
        for user in users:
            if user['id'] == user_id:
                user.update(payload.model_dump(exclude_unset=True))
                return user
        return None

    def delete_by_id(self, user_id: int):
        global users
        for index, user in enumerate(users):
            if user['id'] == user_id:
                users.pop(index)
                return True
        return False