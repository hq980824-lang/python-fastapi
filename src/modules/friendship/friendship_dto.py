from enum import Enum


class FriendStatus(str, Enum):
    # 待同意
    PENDING = "pending"
    # 已同意
    ACCEPTED = "accepted"
    # 已拒绝
    REJECTED = "rejected"
