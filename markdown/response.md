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

## 二、两层协作：`response_model` + `ResponseRoute`

成功响应的组装分两层，各管一件事：

| 层                         | 职责                              | 写在哪              |
| ------------------------- | ------------------------------- | ---------------- |
| `response_model`（FastAPI） | ORM 对象 → DTO，并做类型序列化（datetime → 字符串） | controller 接口声明上 |
| `ResponseRoute`（自定义路由）    | 给序列化后的数据套上 `code/msg/data` 外壳   | `src/common/route.py` |

controller 里**不再手动** `model_validate` / `model_dump` / `success`，只声明 `response_model` 并直接返回 ORM 对象。

### 自定义路由（`src/common/route.py`）

```python
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from src.common.response import success


class ResponseRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request):
            response = await original_handler(request)
            # 只包装 JSON 响应；文件流、重定向等原样放行
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return response
            # original_handler 已把返回值序列化成 JSON，取出再套统一外壳
            data = json.loads(response.body)
            content = success(data=data).model_dump(mode="json")
            return JSONResponse(content=content, status_code=response.status_code)
        return custom_handler


def create_router(prefix: str = "", tags: list = None):
    return APIRouter(prefix=prefix, tags=tags, route_class=ResponseRoute)
```

**两个容易踩的坑：**

> 1. `route_class=ResponseRoute` 必须挂在 **`APIRouter`**（路由分组）上。`APIRoute` 是单条路由、不接受 `prefix`，误用会报 `TypeError: APIRoute.__init__() got an unexpected keyword argument 'prefix'`。
> 2. 判断是否包装要用**响应头 `content-type`**，不能用 `isinstance(response, JSONResponse)`。用了 `response_model` 后 FastAPI 返回的是基类 `Response` 而非 `JSONResponse`，按类型判断会漏掉、导致包装不生效。

### controller 写法

```python
router = create_router(prefix='/users', tags=['用户模块'])

@router.get("/{user_id}", response_model=UserResp)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    user = await svc.get_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return user   # 直接返回 ORM 对象

# 列表用 list[UserResp]
@router.get("", response_model=list[UserResp])
async def get_all_users(db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    return await svc.get_all(db)
```

**数据流转过程：**

```
数据库查询
  → UserDB（SQLAlchemy ORM 对象）
  → response_model=UserResp 自动转换（靠 from_attributes=True，datetime → 字符串）
  → ResponseRoute 自动套上 success(data=...) 外壳
  → {"code":200,"msg":"操作成功","data":{...}}
```

---

## 三、小结

| 关注点         | 现状                              | 状态   |
| ----------- | ------------------------------- | ---- |
| 统一响应结构      | `ResponseModel` + `success/fail` | 已实现 |
| 成功响应自动化     | `ResponseRoute` 自动包装            | 已实现 |
