# 统一响应说明

## 目标

让所有接口返回**统一的 JSON 结构**，前端不用为每个接口单独处理格式：

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": { ... }
}
```

无论成功还是失败，返回结构都长这样。失败响应由「异常拦截器」负责包装，见 `exception-handler.md`。

---

## 一、统一响应模型（`src/common/response.py`）

```python
from http import HTTPStatus
from typing import Optional, Any
from pydantic import BaseModel

class ResponseModel(BaseModel):
    code: int
    msg: str
    data: Optional[Any] = None

def success(data=None, msg='操作成功', code=HTTPStatus.OK):
    return ResponseModel(code=code, msg=msg, data=data)

def fail(msg='操作失败', code=HTTPStatus.BAD_REQUEST, data=None):
    return ResponseModel(code=code, msg=msg, data=data)
```

**三个字段的约定：**

| 字段     | 含义                        |
| ------ | ------------------------- |
| `code` | 业务/HTTP 状态码，如 200、400、500 |
| `msg`  | 给前端/用户看的提示文字              |
| `data` | 真正的业务数据，失败时通常为 `null`     |

`success()` 和 `fail()` 是两个工厂函数，controller 里只管调用，不用每次手写 `ResponseModel(...)`。

---

## 二、成功响应自动包装（`src/common/route.py`）

项目通过**自定义路由类 `ResponseRoute`** 自动包装成功响应，controller 里只需返回业务数据，外层的 `code/msg/data` 结构由路由自动套上。

```python
from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
from src.common.response import success


class ResponseRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request):
            response = await original_handler(request)
            # 已经是 Response（如手动返回的 JSONResponse）就原样放行
            if isinstance(response, Response):
                return response
            # 否则把返回值塞进统一结构
            return success(data=response).model_dump()
        return custom_handler


def create_router(prefix: str = "", tags: list = None):
    return APIRouter(prefix=prefix, tags=tags, route_class=ResponseRoute)
```

> 注意：包装能力来自 `route_class=ResponseRoute`，必须挂在 **`APIRouter`**（路由分组）上。`APIRoute` 是单条路由、不接受 `prefix`，误用会报 `TypeError: APIRoute.__init__() got an unexpected keyword argument 'prefix'`。

controller 用 `create_router` 创建路由器后，直接返回数据即可：

```python
router = create_router(prefix='/users', tags=['用户模块'])

@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    user = await svc.get_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return UserResp.model_validate(user).model_dump(mode="json")  # 直接返回数据，无需手动 success()
```

**数据流转过程：**

```
数据库查询
  → UserDB（SQLAlchemy ORM 对象，不能直接返回）
  → UserResp.model_validate(user)（靠 from_attributes=True 转成 Pydantic 对象）
  → .model_dump(mode="json")（转成 dict，datetime 等转字符串）
  → controller 返回
  → ResponseRoute 自动套上 success(data=...) 外壳
```

---

## 三、小结

| 关注点         | 现状                              | 状态   |
| ----------- | ------------------------------- | ---- |
| 统一响应结构      | `ResponseModel` + `success/fail` | 已实现 |
| 成功响应自动化     | `ResponseRoute` 自动包装            | 已实现 |
