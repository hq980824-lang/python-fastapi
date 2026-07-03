from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.friendship.friendship_dto import FriendStatus
from src.modules.friendship.friendship_model import FriendShipDb
from src.modules.users.user_model import UserDB


class FriendShipService:
    async def add():
        print(1)
