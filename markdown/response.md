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

## 二、成功响应的写法（controller 手动包装）

目前项目**没有做自动的成功响应拦截**，而是在每个 controller 里手动调用 `success()`：

```python
@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), svc: UserService = Depends(get_svc)):
    user = await svc.get_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    pydantic_user = UserResp.model_validate(user)   # ORM 对象 → Pydantic 对象
    return success(data=pydantic_user.model_dump())  # 包装成统一结构
```

**数据流转过程：**

```
数据库查询
  → UserDB（SQLAlchemy ORM 对象，不能直接返回）
  → UserResp.model_validate(user)（靠 from_attributes=True 转成 Pydantic 对象）
  → .model_dump()（转成 dict）
  → success(data=...)（套上 code/msg/data 外壳）
```

---

## 三、目前存在的问题与改进建议

### 1. 成功响应仍是手动包装，存在重复

每个 controller 都要写 `UserResp.model_validate(...).model_dump()` + `success(...)`，重复且容易漏。后续可考虑：

- 用 FastAPI 的 `response_model` + 自定义中间件/`APIRoute` 统一包装，或
- 封装一个依赖/装饰器自动套 `success()` 外壳。

当前阶段手动包装可以接受，规模变大后建议收敛。

---

## 四、小结

| 关注点         | 现状                              | 状态   |
| ----------- | ------------------------------- | ---- |
| 统一响应结构      | `ResponseModel` + `success/fail` | 已实现 |
| 成功响应自动化     | 手动包装                            | 可优化 |
