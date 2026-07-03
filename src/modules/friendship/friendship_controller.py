from src.common.dependencies import CurrentUser, DbDep
from src.common.route import create_router
from src.modules.friendship.friendship_service import FriendShipService

router = create_router("/friendship", tags=["好友模块"])

svc = FriendShipService()
